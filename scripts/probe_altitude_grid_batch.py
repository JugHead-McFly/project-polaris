"""Read-only experiment: exact fixed-target common-grid batching, not app code.

Network downloads are disabled only in this reproducible diagnostic fixture.
Per-target current instants and boundary refinements are not changed or modeled.
"""
import json, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from astropy.coordinates import SkyCoord, AltAz
from astropy.time import Time
from astropy.utils import iers
from app.core.planning_context import ObservatoryContext
from app.services.astronomy_service import get_target_coordinate, get_altitudes_at, _get_location
from app.services.deep_sky_catalog import catalog

iers.conf.auto_download=False
names=list(catalog()[0])[:55]
coordinates=SkyCoord([get_target_coordinate(name) for name in names]).reshape(-1,1)
for latitude,longitude,date in [(33.4,-112,'2026-10-19T02:00:00+00:00'),
                                (-33.9,151.2,'2026-12-21T10:00:00+00:00'),
                                (89,0,'2026-12-21T00:00:00+00:00')]:
    context=ObservatoryContext('Synthetic',latitude,longitude,'UTC')
    start=datetime.fromisoformat(date)
    times=[start+timedelta(minutes=15*i) for i in range(41)]
    astropy_times=Time(times)
    frame=AltAz(obstime=astropy_times,location=_get_location(context))
    coordinates.transform_to(frame)  # Warm identical reference data.
    for iteration in range(3):
        began=perf_counter()
        baseline=[get_altitudes_at(name,times,context) for name in names]
        scalar_seconds=perf_counter()-began
        began=perf_counter()
        # Include fresh coordinate/time/frame preparation, as integration must.
        batch_coordinates=SkyCoord([get_target_coordinate(name) for name in names]).reshape(-1,1)
        batch_frame=AltAz(obstime=Time(times),location=_get_location(context))
        raw=batch_coordinates.transform_to(batch_frame).alt.deg
        batched=[[round(float(value),1) for value in row] for row in raw]
        batch_seconds=perf_counter()-began
        assert baseline==batched
        print(json.dumps({'site':[latitude,longitude],'date':date,'iteration':iteration,
            'targets':len(names),'samples_per_target':len(times),'exact_public_values':True,
            'separate_seconds':round(scalar_seconds,5),'batch_seconds':round(batch_seconds,5)}),flush=True)
