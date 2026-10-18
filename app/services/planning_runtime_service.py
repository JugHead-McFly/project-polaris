"""Prepare shared reference data, never user plans, before production readiness."""
from datetime import datetime, timezone
import logging
from time import perf_counter, process_time, thread_time

from app.core.planning_context import ObservatoryContext
from app.services.astronomy_service import get_moon_info_at
from app.services.deep_sky_catalog import catalog
from app.services.target_art_library_service import prepare_target_art_library

logger = logging.getLogger(__name__)


def prepare_planning_runtime():
    """Use normal astronomy policy and existing process caches.

    Startup pays reference-data initialization explicitly. No download settings,
    precision, freshness bounds, or astronomy failure behavior are overridden.
    A failed preparation is deferred to the ordinary request path, which can
    retry normally; a transient provider failure must not block app startup.
    """
    context = ObservatoryContext("Reference-data preparation", 0.0, 0.0, "UTC")
    results = {}
    operations = {
        "astronomy_reference": lambda: get_moon_info_at(datetime.now(timezone.utc), context),
        "catalog_reference": catalog,
        "art_catalog_reference": prepare_target_art_library,
    }
    for name, operation in operations.items():
        wall, thread, process = perf_counter(), thread_time(), process_time()
        status, error_type = "ready", None
        try:
            operation()
        except Exception as error:
            status, error_type = "deferred", type(error).__name__
        result = {"status": status, "duration_ms": round((perf_counter()-wall)*1000, 1),
                  "thread_cpu_ms": round((thread_time()-thread)*1000, 1),
                  "process_cpu_ms": round((process_time()-process)*1000, 1)}
        results[name] = result
        # Only fixed stage names, numeric timing, and exception class; no user data.
        logger.log(logging.INFO if status == "ready" else logging.WARNING,
                   "planning_runtime stage=%s status=%s duration_ms=%.1f thread_cpu_ms=%.1f process_cpu_ms=%.1f error_type=%s",
                   name, status, result["duration_ms"], result["thread_cpu_ms"], result["process_cpu_ms"], error_type)
    return results
