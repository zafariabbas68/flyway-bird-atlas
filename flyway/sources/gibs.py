"""NASA GIBS (Global Imagery Browse Services) helpers: public WMS, no API key.

Request format verified against the GIBS documentation:
  * endpoint  https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi
  * WMS 1.3.0 with CRS=EPSG:4326 uses LATITUDE-FIRST bounding boxes (minLat,minLon,maxLat,maxLon)
  * TIME is YYYY-MM-DD, or YYYY-MM-DDTHH:MM:SSZ for sub-daily layers
Layer names are NOT hard-coded: they are looked up in the service's own capabilities
document, so a renamed layer produces a clear message instead of a broken download.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
ACK = ("We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse "
       "Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS).")


def capabilities_url() -> str:
    return WMS + "?" + urlencode({"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"})


# ------------------------------------------------------------ capabilities
def _dt(text: str) -> datetime:
    text = text.strip().replace("Z", "+00:00")
    d = datetime.fromisoformat(text)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def parse_extent(text: str):
    """'2004-01-01/2004-12-01/P1M,2005-...' -> [(start, end, period)]"""
    out = []
    for part in text.replace("\n", "").split(","):
        bits = part.strip().split("/")
        if len(bits) == 3:
            try:
                out.append((_dt(bits[0]), _dt(bits[1]), bits[2]))
            except ValueError:
                continue
        elif len(bits) == 1 and bits[0]:
            try:
                d = _dt(bits[0])
                out.append((d, d, "P1D"))
            except ValueError:
                continue
    return out


def parse_layers(xml_bytes: bytes) -> dict:
    """Return {layer_name: {'title': str, 'time': [(start, end, period)]}}."""
    root = ET.fromstring(xml_bytes)
    layers = {}
    for el in root.iter():
        if not el.tag.endswith("Layer"):
            continue
        name = title = None
        extent = []
        for child in el:
            tag = child.tag.split("}")[-1]
            if tag == "Name" and child.text:
                name = child.text.strip()
            elif tag == "Title" and child.text:
                title = child.text.strip()
            elif tag in ("Dimension", "Extent") and (child.get("name") or "").lower() == "time" and child.text:
                extent = parse_extent(child.text)
        if name:
            layers[name] = {"title": title or name, "time": extent}
    return layers


def find_layer(layers: dict, must: list[str], avoid: list[str] | None = None, prefer: list[str] | None = None):
    """Pick the best layer whose name contains every token in `must` (case-insensitive)."""
    avoid = [a.lower() for a in (avoid or [])]
    cands = [n for n in layers if all(m.lower() in n.lower() for m in must) and not any(a in n.lower() for a in avoid)]
    if not cands:
        return None
    for pref in prefer or []:
        for n in cands:
            if n.lower() == pref.lower():
                return n
    return sorted(cands, key=lambda n: (len(n), n))[0]


# ------------------------------------------------------------------- times
def _add_months(d: datetime, n: int) -> datetime:
    y, m = divmod(d.month - 1 + n, 12)
    return d.replace(year=d.year + y, month=m + 1, day=min(d.day, 28))


def _step(d: datetime, period: str) -> datetime:
    m = re.fullmatch(r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", period)
    if not m:
        return d + timedelta(days=1)
    y, mo, dd, hh, mi, ss = (int(x) if x else 0 for x in m.groups())
    d = _add_months(d, 12 * y + mo)
    return d + timedelta(days=dd, hours=hh, minutes=mi, seconds=ss)


def monthly_times(extents) -> list[datetime]:
    """One timestamp per calendar month (up to 12), preferring a native monthly series."""
    monthly = [e for e in extents if re.match(r"P(1M|1Y)$", e[2])]
    seen: dict[int, datetime] = {}
    if monthly:
        for s, e, p in monthly:
            d = s
            for _ in range(2000):
                if d > e or len(seen) == 12:
                    break
                seen.setdefault(d.month, d)
                d = _step(d, p)
    elif extents:
        end = max(e for _, e, _ in extents)
        start = min(s for s, _, _ in extents)
        for month in range(1, 13):
            for year in range(end.year, start.year - 1, -1):   # latest year that has this month
                d = datetime(year, month, 15, tzinfo=timezone.utc)
                if start <= d <= end:
                    seen[month] = d
                    break
    return [seen[m] for m in sorted(seen)]


def pick_window(extents, days: int = 4, month_day=(10, 8)) -> datetime | None:
    """A start time for a short animation, aiming at autumn migration if the layer allows."""
    if not extents:
        return None
    lo = min(s for s, _, _ in extents)
    hi = max(e for _, e, _ in extents)
    for year in range(hi.year, lo.year - 1, -1):
        start = datetime(year, month_day[0], month_day[1], tzinfo=timezone.utc)
        if start >= lo and start + timedelta(days=days) <= hi:
            return start
    return max(lo, hi - timedelta(days=days + 1))


# ------------------------------------------------------------------ requests
def fmt_time(d: datetime, subdaily: bool) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ") if subdaily else d.strftime("%Y-%m-%d")


def getmap_url(layer: str, bbox: tuple[float, float, float, float], size: tuple[int, int],
               when: str | None, fmt: str = "image/jpeg", transparent: bool = False) -> str:
    """bbox = (lon_min, lat_min, lon_max, lat_max). WMS 1.3.0 wants lat first."""
    lon0, lat0, lon1, lat1 = bbox
    params = {
        "SERVICE": "WMS", "REQUEST": "GetMap", "VERSION": "1.3.0", "LAYERS": layer, "STYLES": "",
        "FORMAT": fmt, "CRS": "EPSG:4326", "BBOX": f"{lat0},{lon0},{lat1},{lon1}",
        "WIDTH": size[0], "HEIGHT": size[1],
    }
    if when:
        params["TIME"] = when
    if transparent:
        params["TRANSPARENT"] = "TRUE"
    return WMS + "?" + urlencode(params)


def looks_like_image(data: bytes) -> bool:
    return data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"
