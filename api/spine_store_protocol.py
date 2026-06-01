from __future__ import annotations

from typing import Any, Protocol


class SpineStoreProtocol(Protocol):
    def get_tip_hash(self) -> str | None:
        ...

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        ...

    def list_events(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        ...

    def total_events(self) -> int:
        ...

    def verify(self, from_height: int = 0) -> dict[str, Any]:
        ...
