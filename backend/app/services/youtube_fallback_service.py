"""Explicit, user-selected yt-dlp fallback for failed requests."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, status

from app.config import settings
from app.models.track import Track
from app.services import manual_import_service

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class YouTubeCandidate:
    video_id: str
    title: str
    channel: str
    duration: int | None


def _run(command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, capture_output=True, timeout=timeout)


def _youtube_options() -> list[str]:
    """Use the browser-oriented client; append local session cookies if set."""
    options = [
        "--js-runtimes", "node", "--remote-components", "ejs:github",
        "--extractor-args", "youtube:player_client=default,web_safari",
    ]
    cookie_path = Path(settings.ytdlp_cookies_path) if settings.ytdlp_cookies_path else None
    if cookie_path and cookie_path.is_file():
        options.extend(["--cookies", str(cookie_path)])
    elif cookie_path:
        logger.warning("Configured yt-dlp cookies file does not exist: %s", cookie_path)
    return options


async def candidates(track: Track) -> list[YouTubeCandidate]:
    query = f"{track.artist} - {track.title}"
    command = ["yt-dlp", *_youtube_options(), "--flat-playlist", "--dump-single-json", "--no-warnings", f"ytsearch8:{query}"]
    try:
        result = await asyncio.to_thread(_run, command, timeout=90)
        payload = json.loads(result.stdout or "{}")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="YouTube search is unavailable") from exc
    if result.returncode:
        logger.warning("yt-dlp YouTube search failed: %s", (result.stderr or result.stdout)[-2000:])
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="YouTube search failed")
    found: list[YouTubeCandidate] = []
    for item in payload.get("entries", []):
        if not isinstance(item, dict):
            continue
        video_id = str(item.get("id") or "")
        title = str(item.get("title") or "").strip()
        if not _VIDEO_ID.fullmatch(video_id) or not title:
            continue
        duration = item.get("duration")
        found.append(YouTubeCandidate(
            video_id=video_id,
            title=title[:300],
            channel=str(item.get("channel") or item.get("uploader") or "Canal desconocido")[:200],
            duration=int(duration) if isinstance(duration, (int, float)) else None,
        ))
    return found


async def download_selected(*, video_id: str, track: Track) -> Path:
    if not _VIDEO_ID.fullmatch(video_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid YouTube video")
    workdir = Path(tempfile.mkdtemp(prefix="resonar-ytdlp-"))
    try:
        template = str(workdir / "audio.%(ext)s")
        command = [
            "yt-dlp", *_youtube_options(), "--no-playlist", "--no-warnings", "-f", "bestaudio/best", "-x",
            "--audio-format", "mp3", "--audio-quality", "0", "-o", template,
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        try:
            result = await asyncio.to_thread(_run, command, timeout=900)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="YouTube download is unavailable") from exc
        if result.returncode:
            logger.warning(
                "yt-dlp YouTube download failed for video=%s: %s",
                video_id,
                (result.stderr or result.stdout)[-3000:],
            )
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="YouTube could not download the selected audio")
        source = next(iter(workdir.glob("audio.mp3")), None)
        if source is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="YouTube did not produce an MP3")
        return await manual_import_service.import_path(source=source, track=track)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
