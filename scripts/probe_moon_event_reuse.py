"""Isolated read-only experiment; does not change application code or IERS policy.

This probe alone disables network downloads for reproducible comparisons.
It compares Astroplan's existing next-rise/set algorithms with exact reuse of
their identical Moon altitude grid. It is not a production implementation.
"""
import json
import sys
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from astropy.time import Time
from astropy.utils import iers
from astroplan.target import MoonFlag
from app.core.planning_context import ObservatoryContext
from app.services.astronomy_service import _get_observer

iers.conf.auto_download = False
cases = [(33.4,-112,'America/Phoenix','2026-10-18T03:24:00'),
         (33.4,-112,'America/Phoenix','2026-10-18T14:32:00'),
         (40.7,-74,'America/New_York','2026-11-01T06:30:00'),
         (-33.9,151.2,'Australia/Sydney','2026-12-21T12:00:00'),
         (0,0,'UTC','2027-03-21T00:00:00'),
         (89,0,'UTC','2026-06-21T00:00:00'),
         (-89,0,'UTC','2026-12-21T00:00:00')]
for latitude,longitude,zone,instant in cases:
    observer = _get_observer(ObservatoryContext('Synthetic',latitude,longitude,zone))
    at = Time(instant, scale='utc')
    def pair():
        return (observer.moon_rise_time(at,which='next'), observer.moon_set_time(at,which='next'))
    pair()  # Warm reference tables for equal CPU-work comparison.
    started=perf_counter(); baseline=pair(); baseline_s=perf_counter()-started
    real=observer.altaz
    cache=[]
    counts={'calls':0,'computes':0}
    def exact_grid(time,target=None,**kwargs):
        counts['calls']+=1
        for prior,prior_kwargs,result in cache:
            if (target is MoonFlag and prior_kwargs == kwargs and time.scale == prior.scale
                    and np.array_equal(time.jd1,prior.jd1) and np.array_equal(time.jd2,prior.jd2)):
                return result.copy()
        counts['computes']+=1
        result=real(time,target,**kwargs)
        if target is MoonFlag: cache.append((time.copy(),dict(kwargs),result.copy()))
        return result
    with patch.object(observer,'altaz',side_effect=exact_grid):
        started=perf_counter(); reused=pair(); reused_s=perf_counter()-started
    for left,right in zip(baseline,reused):
        assert np.array_equal(left.mask,right.mask)
        for part in ('jd1','jd2'):
            assert np.array_equal(np.ma.getdata(getattr(left,part)),np.ma.getdata(getattr(right,part)),equal_nan=True)
    print(json.dumps({'case':[latitude,longitude,zone,instant],'exact_results':True,
        'baseline_seconds':round(baseline_s,5),'reused_seconds':round(reused_s,5),**counts}),flush=True)
