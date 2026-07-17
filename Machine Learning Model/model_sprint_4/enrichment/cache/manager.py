from __future__ import annotations

import threading
import time
from typing import Any


class Cache:

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.RLock()

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        with self._lock:

            item = self._data.get(key)

            if item is None:
                return default

            value, expiry = item

            if expiry is not None and expiry <= time.time():
                del self._data[key]
                return default

            return value

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:

        expiry = None

        if ttl is not None:
            expiry = time.time() + ttl

        with self._lock:
            self._data[key] = (value, expiry)

    def exists(
        self,
        key: str,
    ) -> bool:

        return self.get(key) is not None

    def delete(
        self,
        key: str,
    ) -> None:

        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:

        with self._lock:
            self._data.clear()

    def cleanup(self) -> None:

        now = time.time()

        with self._lock:

            expired = []

            for key, (_, expiry) in self._data.items():

                if expiry is not None and expiry <= now:
                    expired.append(key)

            for key in expired:
                del self._data[key]

    def size(self) -> int:

        self.cleanup()

        with self._lock:
            return len(self._data)

    def stats(self) -> dict[str, int]:

        self.cleanup()

        with self._lock:

            return {
                "entries": len(self._data)
            }


class CacheManager:

    def __init__(self) -> None:

        self.playwright = Cache()

        self.infrastructure = Cache()

        self.ocr = Cache()

        self.siglip = Cache()

        self.qr = Cache()

        self.pdf = Cache()

    def clear(self) -> None:

        self.playwright.clear()

        self.infrastructure.clear()

        self.ocr.clear()

        self.siglip.clear()

        self.qr.clear()

        self.pdf.clear()

    def cleanup(self) -> None:

        self.playwright.cleanup()

        self.infrastructure.cleanup()

        self.ocr.cleanup()

        self.siglip.cleanup()

        self.qr.cleanup()

        self.pdf.cleanup()

    def stats(self) -> dict[str, dict[str, int]]:

        return {
            "playwright": self.playwright.stats(),
            "infrastructure": self.infrastructure.stats(),
            "ocr": self.ocr.stats(),
            "siglip": self.siglip.stats(),
            "qr": self.qr.stats(),
            "pdf": self.pdf.stats(),
        }


cache = CacheManager()