"""Music bingo: private host controls plus a token-based public play room."""
from __future__ import annotations

import json
import random
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.features import require_feature
from app.database import get_db
from app.dependencies import get_current_user
from app.models.bingo import BingoClaim, BingoGame, BingoPlayer
from app.models.playlist import Playlist
from app.models.track import Track
from app.models.user import User
from app.services import event_service, playlist_service
from app.services.serializers import track_out

router = APIRouter(prefix="/api/bingo", tags=["bingo"])


def _game(db: DbSession, game_id: str) -> BingoGame:
    game = db.get(BingoGame, game_id)
    if not game:
        raise HTTPException(404, "Partida no encontrada")
    return game


def _host(game: BingoGame, user: User) -> None:
    if game.host_user_id != user.id:
        raise HTTPException(403, "Solo el anfitrión puede hacer esto")


def _tracks(db: DbSession, game: BingoGame) -> list[Track]:
    ids = json.loads(game.sequence_json)
    rows = {track.id: track for track in db.scalars(select(Track).where(Track.id.in_(ids))).all()}
    return [rows[item] for item in ids if item in rows]


def _state(db: DbSession, game: BingoGame, player: BingoPlayer | None = None, host=False) -> dict:
    tracks = _tracks(db, game)
    current = tracks[game.current_index] if 0 <= game.current_index < len(tracks) else None
    data = {"id": game.id, "code": game.join_code, "title": game.title, "status": game.status, "gridSize": game.grid_size, "playSeconds": game.play_seconds, "markSeconds": game.mark_seconds, "currentIndex": game.current_index, "currentTrack": track_out(current) if current else None, "totalTracks": len(tracks)}
    if player:
        card = json.loads(player.card_json)
        rows = {track.id: track for track in tracks}
        data["player"] = {"token": player.guest_token, "name": player.display_name, "card": card, "cardTracks": [track_out(rows[item]) for item in card if item in rows], "marked": json.loads(player.marked_json)}
    if host:
        data["players"] = [{"id": item.id, "name": item.display_name} for item in db.scalars(select(BingoPlayer).where(BingoPlayer.game_id == game.id)).all()]
        data["claims"] = [{"id": item.id, "playerId": item.player_id, "kind": item.kind, "status": item.status} for item in db.scalars(select(BingoClaim).where(BingoClaim.game_id == game.id, BingoClaim.status == "PENDING")).all()]
    return data


@router.get("/games")
def games(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    require_feature(user, "bingo.access")
    return [_state(db, game, host=True) for game in db.scalars(select(BingoGame).where(BingoGame.host_user_id == user.id).order_by(BingoGame.created_at.desc())).all()]


@router.post("/games")
def create_game(payload: dict, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    require_feature(user, "bingo.access")
    playlist_id = payload.get("playlistId")
    playlist = db.get(Playlist, playlist_id) if isinstance(playlist_id, str) else None
    if not playlist or not playlist_service.can_edit(playlist, user):
        raise HTTPException(404, "Playlist no encontrada")
    size = int(payload.get("gridSize", 4))
    if size not in {3, 4, 5} or len(playlist.items) < size * size:
        raise HTTPException(422, f"La playlist necesita al menos {size * size} canciones")
    sequence = [item.track_id for item in playlist.items]
    random.shuffle(sequence)
    game = BingoGame(host_user_id=user.id, playlist_id=playlist.id, join_code=secrets.token_urlsafe(6).upper(), title=str(payload.get("title") or playlist.name)[:160], grid_size=size, play_seconds=max(5, min(int(payload.get("playSeconds", 15)), 60)), mark_seconds=max(3, min(int(payload.get("markSeconds", 8)), 45)), sequence_json=json.dumps(sequence))
    db.add(game); db.commit(); db.refresh(game)
    return _state(db, game, host=True)


@router.get("/games/{game_id}")
def host_game(game_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    require_feature(user, "bingo.access"); game = _game(db, game_id); _host(game, user)
    return _state(db, game, host=True)


@router.post("/games/{game_id}/start")
async def start(game_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    require_feature(user, "bingo.access"); game = _game(db, game_id); _host(game, user)
    game.status = "RUNNING"; game.current_index = 0; db.commit()
    await event_service.emit_system_updated("bingo.game", {"gameId": game.id})
    return _state(db, game, host=True)


@router.post("/games/{game_id}/next")
async def next_round(game_id: str, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    require_feature(user, "bingo.access"); game = _game(db, game_id); _host(game, user)
    if game.status != "RUNNING": raise HTTPException(409, "La partida no está en curso")
    if game.current_index + 1 >= len(json.loads(game.sequence_json)):
        game.status = "FINISHED"
    else: game.current_index += 1
    db.commit(); await event_service.emit_system_updated("bingo.game", {"gameId": game.id})
    return _state(db, game, host=True)


@router.post("/games/{game_id}/claims/{claim_id}")
async def resolve_claim(game_id: str, claim_id: str, payload: dict, user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    require_feature(user, "bingo.access"); game = _game(db, game_id); _host(game, user)
    claim = db.get(BingoClaim, claim_id)
    if not claim or claim.game_id != game.id: raise HTTPException(404, "Reclamación no encontrada")
    approved = bool(payload.get("approved")); claim.status = "APPROVED" if approved else "REJECTED"
    if approved and claim.kind == "BINGO": game.status = "FINISHED"
    db.commit(); await event_service.emit_system_updated("bingo.game", {"gameId": game.id})
    return _state(db, game, host=True)


@router.get("/public/{code}")
def public_game(code: str, token: str | None = None, db: DbSession = Depends(get_db)):
    game = db.scalar(select(BingoGame).where(BingoGame.join_code == code.upper()))
    if not game: raise HTTPException(404, "Partida no encontrada")
    player = db.scalar(select(BingoPlayer).where(BingoPlayer.game_id == game.id, BingoPlayer.guest_token == token)) if token else None
    return _state(db, game, player=player)


@router.get("/public/{code}/qr")
def public_qr(code: str, request: Request, db: DbSession = Depends(get_db)):
    game = db.scalar(select(BingoGame).where(BingoGame.join_code == code.upper()))
    if not game: raise HTTPException(404, "Partida no encontrada")
    import qrcode
    import qrcode.image.svg
    image = qrcode.make(str(request.base_url).rstrip("/") + f"/bingo/{game.join_code}", image_factory=qrcode.image.svg.SvgPathImage)
    from io import BytesIO
    output = BytesIO(); image.save(output)
    return Response(output.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


@router.post("/public/{code}/join")
def join(code: str, payload: dict, db: DbSession = Depends(get_db)):
    game = db.scalar(select(BingoGame).where(BingoGame.join_code == code.upper()))
    name = str(payload.get("name") or "").strip()[:80]
    if not game or not name: raise HTTPException(422, "Nombre o partida no válidos")
    if game.status != "LOBBY": raise HTTPException(409, "La partida ya ha empezado")
    sequence = json.loads(game.sequence_json); card = random.sample(sequence, game.grid_size * game.grid_size)
    player = BingoPlayer(game_id=game.id, display_name=name, card_json=json.dumps(card)); db.add(player); db.commit(); db.refresh(player)
    return _state(db, game, player=player)


@router.post("/public/{code}/mark")
async def mark(code: str, payload: dict, db: DbSession = Depends(get_db)):
    game = db.scalar(select(BingoGame).where(BingoGame.join_code == code.upper()))
    token, track_id = payload.get("token"), payload.get("trackId")
    player = db.scalar(select(BingoPlayer).where(BingoPlayer.game_id == game.id, BingoPlayer.guest_token == token)) if game and isinstance(token, str) else None
    if not game or not player or track_id not in json.loads(player.card_json): raise HTTPException(403, "Cartón no válido")
    called = set(json.loads(game.sequence_json)[: game.current_index + 1])
    if track_id not in called: raise HTTPException(409, "Esa canción todavía no ha sonado")
    marked = set(json.loads(player.marked_json)); marked.add(track_id); player.marked_json = json.dumps(sorted(marked)); db.commit()
    await event_service.emit_system_updated("bingo.game", {"gameId": game.id})
    return _state(db, game, player=player)


@router.post("/public/{code}/claim")
async def claim(code: str, payload: dict, db: DbSession = Depends(get_db)):
    game = db.scalar(select(BingoGame).where(BingoGame.join_code == code.upper()))
    token, kind = payload.get("token"), payload.get("kind")
    player = db.scalar(select(BingoPlayer).where(BingoPlayer.game_id == game.id, BingoPlayer.guest_token == token)) if game and isinstance(token, str) else None
    if not game or not player or kind not in {"LINE", "BINGO"}: raise HTTPException(422, "Reclamación no válida")
    card, marked, n = json.loads(player.card_json), set(json.loads(player.marked_json)), game.grid_size
    lines = [card[i*n:(i+1)*n] for i in range(n)] + [[card[i*n+j] for i in range(n)] for j in range(n)] + [[card[i*n+i] for i in range(n)], [card[i*n+n-1-i] for i in range(n)]]
    valid = all(item in marked for item in card) if kind == "BINGO" else any(all(item in marked for item in line) for line in lines)
    if not valid: raise HTTPException(409, "Aún no tienes una jugada válida")
    db.add(BingoClaim(game_id=game.id, player_id=player.id, kind=kind)); db.commit(); await event_service.emit_system_updated("bingo.game", {"gameId": game.id})
    return _state(db, game, player=player)
