"""ORM models. Importing this package registers every table on ``Base.metadata``
which Alembic autogeneration and ``create_all`` rely on."""
from app.models.favorite import Favorite
from app.models.history import History
from app.models.music_request import MusicRequest
from app.models.playlist import Playlist, PlaylistTrack
from app.models.session import Session
from app.models.track import Track
from app.models.user import User

__all__ = [
    "Favorite",
    "History",
    "MusicRequest",
    "Playlist",
    "PlaylistTrack",
    "Session",
    "Track",
    "User",
]
