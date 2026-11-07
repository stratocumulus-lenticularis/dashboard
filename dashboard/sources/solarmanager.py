"""Solar Manager live values.

ASSUMPTION (docs not verifiable offline): SOLARMANAGER_URL is the complete
endpoint returning current values as JSON (e.g. the gateway stream/point
endpoint of your installation) and SOLARMANAGER_TOKEN is a bearer token.
Field names are matched against several known variants; adjust KEYS if your
response differs (run `python -m dashboard --dump solar`).
"""

from __future__ import annotations

from .. import net
from ..config import Config
from ..models import Energy

KEYS = {
    "pv_w": ("currentPvGeneration", "pv", "production", "pvPower"),
    "consumption_w": ("currentOverallConsumption", "consumption", "consumptionPower"),
    "grid_w": ("currentGridPower", "currentGridPowerExchange", "grid", "gridPower"),
    "battery_w": ("currentBatteryChargeDischarge", "battery", "batteryPower"),
    "battery_soc": ("soc", "batterySoc", "currentBatterySoc", "stateOfCharge"),
}


def _num(data: dict, names: tuple[str, ...]) -> float | None:
    for n in names:
        v = data.get(n)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def parse(data: dict) -> Energy:
    if isinstance(data, list) and data:
        data = data[0]
    # some responses nest values, e.g. {"data": {...}}
    if isinstance(data.get("data"), dict):
        data = data["data"]
    return Energy(**{field: _num(data, names) for field, names in KEYS.items()})


def fetch(cfg: Config) -> Energy:
    if not cfg.solar_url:
        raise ValueError("Solar Manager not configured")
    headers = {"Authorization": f"Bearer {cfg.solar_token}"} if cfg.solar_token else {}
    return parse(net.get_json(cfg.solar_url, headers))
