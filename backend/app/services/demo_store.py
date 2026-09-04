"""Load and serve pre-cached demo playbooks for hackathon demos."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.models.playbook import Playbook
from app.models.trace import TraceLog

logger = logging.getLogger(__name__)


class DemoCacheEntry(BaseModel):
    """A cached demo playbook with optional trace log."""

    ticker: str
    job_id: str
    playbook: Playbook
    trace_log: TraceLog | None = None
    seeded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = "live"


class DemoStore:
    """Read demo playbooks from the local demo cache directory."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._demo_dir = Path(self._settings.demo_cache_dir)

    @property
    def demo_dir(self) -> Path:
        return self._demo_dir

    def list_tickers(self) -> list[str]:
        if not self._demo_dir.exists():
            return []
        tickers: list[str] = []
        for path in sorted(self._demo_dir.glob("*.json")):
            if path.name.startswith("."):
                continue
            tickers.append(path.stem.upper())
        return tickers

    def load(self, ticker: str) -> DemoCacheEntry | None:
        path = self._demo_dir / f"{ticker.lower()}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return DemoCacheEntry.model_validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to load demo cache %s: %s", path, exc)
            return None

    def save(self, entry: DemoCacheEntry) -> Path:
        self._demo_dir.mkdir(parents=True, exist_ok=True)
        path = self._demo_dir / f"{entry.ticker.lower()}.json"
        payload = entry.model_dump(mode="json")
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        logger.info("Saved demo cache to %s", path)
        return path

    def save_from_dict(self, ticker: str, data: dict[str, Any]) -> Path:
        entry = DemoCacheEntry.model_validate(data)
        return self.save(entry)


demo_store = DemoStore()
