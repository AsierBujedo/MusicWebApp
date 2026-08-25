"""ORM models. Importing this package registers every table on ``Base.metadata``
which Alembic autogeneration and ``create_all`` rely on."""
from app.models.favorite import Favorite
from app.models.feature_rollout import FeatureRollout
from app.models.history import History
from app.models.music_request import MusicRequest
from app.models.playlist import Playlist, PlaylistCollaborator, PlaylistTrack
from app.models.session import Session
from app.models.spotify_connection import SpotifyConnection
from app.models.system_setting import SystemSetting
from app.models.track import Track
from app.models.user import User, UserFeatureFlag

__all__ = [
    "Favorite",
    "FeatureRollout",
    "History",
    "MusicRequest",
    "Playlist",
    "PlaylistTrack",
    "Session",
    "SpotifyConnection",
    "SystemSetting",
    "Track",
    "User",
]
