"""GOES-18 regional cloud references for saved forecast times.

Public NOAA ACMC files, not a weather-model hindcast. Work runs in the cron
collector, never in a user's plan request. Each download is bounded and each
reference retains the source hash, time offset and pixel quality evidence.
"""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import logging
import re
import xml.etree.ElementTree as ET

import httpx
import numpy as np

from app.models import ForecastAccuracySnapshot


LOGGER = logging.getLogger(__name__)
BASE_URL = "https://noaa-goes18.s3.amazonaws.com/"
MAX_BYTES = 32 * 1024 * 1024


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _stamp(value):
    return datetime.strptime(value[:13], "%Y%j%H%M%S").replace(tzinfo=timezone.utc) + timedelta(seconds=int(value[13:] or "0") / 10)


def _midpoint(key):
    match = re.search(r"_s(\d{14})_e(\d{14})_", key)
    if not match:
        raise ValueError("Unrecognized GOES scan key")
    start, end = (_stamp(value) for value in match.groups())
    return start + (end - start) / 2


def _download(url):
    with httpx.stream("GET", url, timeout=30, follow_redirects=False) as response:
        response.raise_for_status()
        result = bytearray()
        for chunk in response.iter_bytes():
            result.extend(chunk)
            if len(result) > MAX_BYTES:
                raise ValueError("GOES response exceeded download limit")
        return bytes(result)


@lru_cache(maxsize=8)
def _region(x_bytes, y_bytes, height, equatorial, polar, origin, latitude, longitude):
    """NOAA fixed-grid projection in row strips to bound worker memory."""
    x_axis = np.frombuffer(x_bytes, dtype=np.float64)
    y_axis = np.frombuffer(y_bytes, dtype=np.float64)
    hits_y, hits_x = [], []
    h = height + equatorial
    ratio = (equatorial / polar) ** 2
    for offset in range(0, len(y_axis), 64):
        x, y = np.meshgrid(x_axis, y_axis[offset:offset + 64])
        a = np.sin(x)**2 + np.cos(x)**2 * (np.cos(y)**2 + ratio * np.sin(y)**2)
        b = -2 * h * np.cos(x) * np.cos(y)
        with np.errstate(invalid="ignore"):
            r = (-b - np.sqrt(b*b - 4*a*(h*h-equatorial*equatorial))) / (2*a)
            sx, sy, sz = r*np.cos(x)*np.cos(y), -r*np.sin(x), r*np.cos(x)*np.sin(y)
            lat = np.degrees(np.arctan(ratio*sz / np.sqrt((h-sx)**2 + sy*sy)))
            lon = origin - np.degrees(np.arctan2(sy, h-sx))
        distance = 111.2*np.sqrt((lat-latitude)**2 + ((lon-longitude)*np.cos(np.radians(latitude)))**2)
        ys, xs = np.where(distance <= 10)
        hits_y.extend((ys + offset).tolist())
        hits_x.extend(xs.tolist())
    if not hits_y:
        raise ValueError("Observatory is outside GOES-18 CONUS coverage")
    y0, y1, x0, x1 = min(hits_y), max(hits_y)+1, min(hits_x), max(hits_x)+1
    mask = np.zeros((y1-y0, x1-x0), dtype=bool)
    mask[np.array(hits_y)-y0, np.array(hits_x)-x0] = True
    return slice(y0, y1), slice(x0, x1), mask


def extract_reference(content, key, target, latitude, longitude):
    from netCDF4 import Dataset

    target = utc(target)
    with Dataset("cloud.nc", memory=content) as dataset:
        projection = dataset["goes_imager_projection"]
        ys, xs, mask = _region(
            np.asarray(dataset["x"][:], dtype=np.float64).tobytes(),
            np.asarray(dataset["y"][:], dtype=np.float64).tobytes(),
            float(projection.perspective_point_height), float(projection.semi_major_axis),
            float(projection.semi_minor_axis), float(projection.longitude_of_projection_origin),
            float(latitude), float(longitude),
        )
        start = datetime.fromisoformat(dataset.time_coverage_start.replace("Z", "+00:00"))
        end = datetime.fromisoformat(dataset.time_coverage_end.replace("Z", "+00:00"))
        midpoint = start + (end-start)/2
        quality, classes, binary = (dataset[name][ys, xs] for name in ("DQF", "ACM", "BCM"))
        good = (mask & (np.asarray(quality) == 0)
                & ~np.ma.getmaskarray(quality) & ~np.ma.getmaskarray(classes)
                & ~np.ma.getmaskarray(binary) & np.isin(np.asarray(classes), [0, 1, 2, 3])
                & np.isin(np.asarray(binary), [0, 1]))
        coverage = float(good.sum() / mask.sum())
        offset = (midpoint-target).total_seconds()
        usable = coverage >= .9 and abs(offset) <= 180
        return {
            "schema_version": 1, "source": "noaa-goes18-abi-l2-acmc",
            "method": "equal-pixel-fraction-within-10km-nearest-scan-v1",
            "status": "usable" if usable else "insufficient_quality",
            "forecast_for": target.isoformat(), "scan_start": start.isoformat(),
            "scan_end": end.isoformat(), "scan_midpoint": midpoint.isoformat(),
            "time_offset_seconds": offset, "good_pixel_fraction": coverage,
            "cloud_cover_percent": float(np.mean(np.asarray(binary)[good])*100) if usable else None,
            "region_pixel_count": int(mask.sum()), "good_pixel_count": int(good.sum()),
            "uncertain_pixel_fraction": float(np.mean(np.isin(np.asarray(classes)[good], [1, 2]))) if good.any() else None,
            "latitude": latitude, "longitude": longitude, "radius_km": 10,
            "source_url": BASE_URL + key, "sha256": hashlib.sha256(content).hexdigest(),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "location_provenance": "Account observing home coordinates at collection",
            "measurement_kind": "satellite_estimated_regional_cloud_fraction",
            "comparison_kind": "single_target_time_not_nightly_average",
        }


def fetch_reference(target, latitude, longitude):
    target = utc(target)
    keys = set()
    for hour in {target.replace(minute=0, second=0, microsecond=0),
                 (target-timedelta(minutes=5)).replace(minute=0, second=0, microsecond=0),
                 (target+timedelta(minutes=5)).replace(minute=0, second=0, microsecond=0)}:
        prefix = f"ABI-L2-ACMC/{hour.year}/{hour.timetuple().tm_yday:03d}/{hour.hour:02d}/"
        tree = ET.fromstring(_download(BASE_URL + f"?list-type=2&prefix={prefix}&max-keys=1000"))
        keys.update(node.text for node in tree.findall("{*}Contents/{*}Key") if node.text and node.text.startswith(prefix))
    if not keys:
        raise ValueError("Satellite scan not yet available")
    key = min(keys, key=lambda candidate: abs((_midpoint(candidate)-target).total_seconds()))
    if abs((_midpoint(key)-target).total_seconds()) > 180:
        raise ValueError("No satellite scan within three minutes")
    return extract_reference(_download(BASE_URL+key), key, target, latitude, longitude)


def collect_satellite_references(db, *, user_id, observatory, fetch=fetch_reference, now=None, limit=48):
    """Backfill existing saved forecasts; preserve all original forecast fields.

    Commit each target independently so a network failure cannot discard earlier
    successful work. Missing scans retry next run; bad-quality scans are retained
    as evidence but never scored. Tenant identity must already be set by caller.
    """
    if observatory.user_id != user_id:
        raise ValueError("Observatory owner mismatch")
    now = utc(now or datetime.now(timezone.utc))
    rows = db.query(ForecastAccuracySnapshot).filter(
        ForecastAccuracySnapshot.user_id == user_id,
        ForecastAccuracySnapshot.observatory_id == observatory.id,
        ForecastAccuracySnapshot.forecast_for < now-timedelta(minutes=15),
        ForecastAccuracySnapshot.forecast_for >= now-timedelta(days=90),
        ForecastAccuracySnapshot.forecast_created_at < ForecastAccuracySnapshot.forecast_for,
    ).order_by(ForecastAccuracySnapshot.forecast_for).all()
    groups = {}
    for row in rows:
        if row.satellite_cloud_observation is None:
            groups.setdefault(utc(row.forecast_for), []).append(row)
    report = {"completed_targets": 0, "unusable_targets": 0, "retry_targets": 0}
    for target, revisions in list(groups.items())[:limit]:
        try:
            reference = fetch(target, observatory.latitude, observatory.longitude)
            for row in revisions:
                row.satellite_cloud_observation = reference
            db.commit()
            report["completed_targets" if reference["status"] == "usable" else "unusable_targets"] += 1
        except Exception:
            db.rollback()
            report["retry_targets"] += 1
            LOGGER.exception("Satellite reference collection failed for one saved target")
    return report
