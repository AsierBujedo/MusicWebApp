"""Safe manual import for failed acquisition requests."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import NamedTuple

import httpx
from fastapi import HTTPException, UploadFile, status
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, TALB, TDRC, TIT2, TPE1, TPE2, TRCK
from mutagen.mp3 import MP3

from app.config import settings
from app.models.track import Track

_ALLOWED_EXTENSIONS = {".mp3", ".flac"}
_MAX_COVER_BYTES = 8 * 1024 * 1024
logger = logging.getLogger(__name__)


class Cover(NamedTuple):
    data: bytes
    mime: str


async def _cover_art_archive(client: httpx.AsyncClient, mbid: str, *, release_group: bool) -> Cover | None:
    try:
        response = await client.get(
            f"https://coverartarchive.org/{'release-group' if release_group else 'release'}/{mbid}/front-250",
            headers={"User-Agent": "Resonar/1.0"},
        )
        response.raise_for_status()
        if len(response.content) > _MAX_COVER_BYTES:
            return None
        mime = response.headers.get("content-type", "image/jpeg").split(";", 1)[0]
        return Cover(response.content, mime) if mime.startswith("image/") else None
    except httpx.HTTPError:
        return None


def _safe_component(value: str, fallback: str) -> str:
    clean = re.sub(r"[^\w .()\-]", "_", (value or "").strip(), flags=re.UNICODE)
    clean = re.sub(r"\s+", " ", clean).strip(" .")
    return (clean or fallback)[:160]


async def _resonar_cover(track: Track) -> Cover | None:
    """Fetch only Resonar's known Cover Art Archive source, never file tags."""
    candidates: list[tuple[str, bool]] = []
    if track.cover and track.cover.startswith("/api/covers/release-group/"):
        candidates.append((track.cover.rsplit("/", 1)[-1], True))
    elif track.provider == "droppedneedle" and track.metadata_json:
        try:
            mbid = json.loads(track.metadata_json).get("release_mbid")
            if mbid:
                candidates.append((str(mbid), False))
        except (TypeError, ValueError):
            pass
    if track.album_id and track.provider == "droppedneedle":
        candidates.append((track.album_id, True))
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # Prefer the exact release/group already selected by Resonar.
            for mbid, is_group in candidates:
                cover = await _cover_art_archive(client, mbid, release_group=is_group)
                if cover:
                    return cover

            # Native DroppedNeedle search results can contain only a recording
            # MBID. Resolve one release here so manual imports still receive a
            # Resonar-sourced cover rather than retaining uploaded artwork.
            if track.provider == "droppedneedle" and track.provider_id:
                response = await client.get(
                    f"https://musicbrainz.org/ws/2/recording/{track.provider_id}",
                    params={"inc": "releases+release-groups", "fmt": "json"},
                    headers={"User-Agent": "Resonar/1.0"},
                )
                response.raise_for_status()
                releases = response.json().get("releases", [])
                if isinstance(releases, list):
                    for release in releases:
                        if not isinstance(release, dict):
                            continue
                        release_id = release.get("id")
                        if release_id:
                            cover = await _cover_art_archive(client, str(release_id), release_group=False)
                            if cover:
                                return cover
    except httpx.HTTPError:
        pass
    logger.info("No Resonar cover available for manual import track=%s", track.id)
    return None


def embedded_cover(path: Path) -> Cover | None:
    """Return the artwork written by Resonar, if any, for the cover proxy."""
    try:
        if path.suffix.lower() == ".flac":
            pictures = FLAC(path).pictures
            if pictures:
                picture = pictures[0]
                return Cover(picture.data, picture.mime or "image/jpeg")
        else:
            tags = MP3(path).tags
            pictures = tags.getall("APIC") if tags else []
            if pictures:
                picture = pictures[0]
                return Cover(picture.data, picture.mime or "image/jpeg")
    except Exception:
        logger.warning("Could not read embedded manual cover: %s", path, exc_info=True)
    return None


def _write_tags(path: Path, track: Track, cover: Cover | None, *, audio_extension: str) -> None:
    title = track.title
    artist = track.artist
    album = track.album or "Singles"
    if audio_extension == ".flac":
        audio = FLAC(path)
        audio.clear()
        audio["title"] = title
        audio["artist"] = artist
        audio["albumartist"] = artist
        audio["album"] = album
        if track.year:
            audio["date"] = str(track.year)
        audio.clear_pictures()
        if cover:
            picture = Picture()
            picture.type = 3
            picture.mime = cover.mime
            picture.data = cover.data
            audio.add_picture(picture)
        audio.save()
        return

    audio = MP3(path)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.clear()
    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artist))
    audio.tags.add(TPE2(encoding=3, text=artist))
    audio.tags.add(TALB(encoding=3, text=album))
    if track.year:
        audio.tags.add(TDRC(encoding=3, text=str(track.year)))
    audio.tags.add(TRCK(encoding=3, text="1"))
    if cover:
        audio.tags.add(APIC(encoding=3, mime=cover.mime, type=3, desc="Cover", data=cover.data))
    audio.save(v2_version=3)


async def import_audio(*, upload: UploadFile, track: Track) -> Path:
    """Copy and retag an MP3/FLAC. Original foreign tags/artwork are discarded."""
    extension = Path(upload.filename or "").suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only MP3 or FLAC files are supported")

    library_root = Path(settings.music_library_path).resolve()
    if not library_root.is_dir():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Music library mount is unavailable")
    target_dir = library_root / _safe_component(track.artist, "Unknown Artist") / _safe_component(track.album or "Singles", "Singles")
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / f"{_safe_component(track.title, 'Track')}{extension}"
    if destination.exists():
        destination = target_dir / f"{_safe_component(track.title, 'Track')} (manual){extension}"
    temporary = destination.with_suffix(destination.suffix + ".uploading")
    total = 0
    try:
        with temporary.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > settings.manual_upload_max_bytes:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file is too large")
                output.write(chunk)
        # The temporary filename ends in `.uploading`; pass the original
        # extension explicitly so a FLAC is never parsed as an MP3.
        _write_tags(temporary, track, await _resonar_cover(track), audio_extension=extension)
        temporary.replace(destination)
        return destination
    except HTTPException:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        logger.warning("Manual audio import could not be retagged: %s", upload.filename, exc_info=True)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The audio file could not be read or retagged") from exc
    finally:
        await upload.close()


async def import_path(*, source: Path, track: Track) -> Path:
    """Retag an internally downloaded MP3/FLAC using the normal manual path."""
    extension = source.suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS or not source.is_file():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Downloaded audio is invalid")
    library_root = Path(settings.music_library_path).resolve()
    if not library_root.is_dir():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Music library mount is unavailable")
    target_dir = library_root / _safe_component(track.artist, "Unknown Artist") / _safe_component(track.album or "Singles", "Singles")
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / f"{_safe_component(track.title, 'Track')}{extension}"
    if destination.exists():
        destination = target_dir / f"{_safe_component(track.title, 'Track')} (manual){extension}"
    temporary = destination.with_suffix(destination.suffix + ".uploading")
    try:
        with source.open("rb") as input_file, temporary.open("wb") as output_file:
            while chunk := input_file.read(1024 * 1024):
                output_file.write(chunk)
        _write_tags(temporary, track, await _resonar_cover(track), audio_extension=extension)
        temporary.replace(destination)
        return destination
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        logger.warning("Downloaded audio could not be retagged: %s", source, exc_info=True)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Downloaded audio could not be retagged") from exc
