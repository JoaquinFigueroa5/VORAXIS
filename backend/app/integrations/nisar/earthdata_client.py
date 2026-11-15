"""Earthdata Login session. Optional: ASF search works anonymously."""

from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EarthdataClient:
    @property
    def configured(self) -> bool:
        return bool(settings.earthdata_username and settings.earthdata_password)

    @lru_cache(maxsize=1)
    def session(self) -> Any | None:
        """Return an authenticated requests session, or None when no credentials exist."""
        import earthaccess

        try:
            auth = earthaccess.login(strategy="environment", persist=False)
        except Exception as exc:
            logger.warning("Earthdata login failed: %s", exc)
            return None
        if not getattr(auth, "authenticated", False):
            logger.warning("Earthdata login was rejected; check EARTHDATA_USERNAME/PASSWORD")
            return None
        # `login` returns an Auth object; the HTTP session comes from it.
        return auth.get_session()

    def download(self, url: str, destination, progress=None) -> bool:
        """`progress(bytes_done, total_or_None)` is called about every 50 MB."""
        if not self.configured:
            logger.info("no Earthdata credentials; skipping authenticated download")
            return False
        session = self.session()
        if session is None:
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Granules are several GB: write to a .part file so an interrupted
        # download is never mistaken for a complete one.
        partial = destination.with_name(destination.name + ".part")
        try:
            with session.get(url, stream=True, timeout=120) as response:
                response.raise_for_status()
                length = response.headers.get("Content-Length")
                total = int(length) if length and length.isdigit() else None
                done = reported = 0
                with partial.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        handle.write(chunk)
                        done += len(chunk)
                        if progress and done - reported >= 50 * 1024 * 1024:
                            reported = done
                            progress(done, total)
                if progress:
                    progress(done, total)
            partial.replace(destination)
        finally:
            partial.unlink(missing_ok=True)
        return True
