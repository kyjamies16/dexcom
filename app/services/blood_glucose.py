# glucose.py
import logging
from typing import Optional

from pydexcom import Dexcom, Region

from ..utils.cache import DataCache

logger = logging.getLogger(__name__)


def _coerce_region(region_value: Optional[str]) -> Region:
    if not region_value:
        return Region.US
    try:
        return Region(region_value.strip().lower())
    except ValueError:
        logger.warning(
            "Unknown Dexcom region '%s'; defaulting to US", region_value
        )
        return Region.US


class Glucose:
    def __init__(
        self,
        username: Optional[str],
        password: Optional[str],
        account_id: Optional[str] = None,
        region: Optional[str] = None,
        cache_ttl_seconds: int = 60,
        data_cache: Optional[DataCache] = None,
    ):
        self.high_value = 200
        self.low_value = 70
        self.dexcom: Optional[Dexcom] = None
        self.cache = data_cache or DataCache(logger=logger)
        self.cache_ttl_seconds = max(cache_ttl_seconds, 5)

        if not username or not password:
            logger.warning("Dexcom credentials missing; disabling glucose readings")
            return

        region_enum = _coerce_region(region)
        try:
            self.dexcom = Dexcom(
                username=username,
                password=password,
                account_id=account_id or None,
                region=region_enum,
            )
        except Exception as exc:
            logger.warning("Unable to initialize Dexcom client: %s", exc)

    def get_glucose_reading(self):
        if not self.dexcom:
            return None
        return self.cache.get(
            "glucose:reading",
            self._fetch_reading,
            ttl_seconds=self.cache_ttl_seconds,
            allow_stale=True,
        )

    def _fetch_reading(self):
        try:
            return self.dexcom.get_current_glucose_reading()
        except Exception as exc:
            logger.warning("Dexcom reading failed: %s", exc)
            return None

    def get_glucose_trend(self):
        reading = self.get_glucose_reading()
        return reading.trend_arrow if reading else None

    def get_glucose_value(self):
        reading = self.get_glucose_reading()
        return reading.mg_dl if reading else None
