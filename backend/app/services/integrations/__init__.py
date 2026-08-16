"""External service adapters (DroppedNeedle, Navidrome, slskd).

Import the factory functions to obtain the mock or real client depending on
``MOCK_EXTERNAL_SERVICES``.
"""
from app.services.integrations.droppedneedle import get_droppedneedle_client
from app.services.integrations.navidrome import get_navidrome_client
from app.services.integrations.slskd import get_slskd_client

__all__ = [
    "get_droppedneedle_client",
    "get_navidrome_client",
    "get_slskd_client",
]
