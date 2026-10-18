"""Isolated exact batching experiment; never imported by production."""
from datetime import timedelta,timezone
import math
from astropy.coordinates import SkyCoord,AltAz
from astropy.time import Time
from app.services import astronomy_service as a,planner_service as p
from app.core.calculation_cache import calculation_scope_active

def install():
    if getattr(p.prepare_fixed_target_altitudes, '_geometry_probe', False): return
    original=p.prepare_fixed_target_altitudes
    def prepare(names,times,context):
        original(names,times,context)
        if not calculation_scope_active() or not times: return
        coarse=times[:-1]; midpoint=times[-1]
        fixed=[]; coords=[]; paired=[]; pairs=[]
        for name in names:
            normalized=name.strip().upper()
            if normalized in a.SOLAR_SYSTEM_TARGETS or a.is_ephemeris_target(normalized): continue
            try:
                coordinate=a.get_target_coordinate(normalized)
            except ValueError:
                continue
            if coordinate is None: continue
            fixed.append(name); coords.append(coordinate)
            values=a.get_altitudes_at(name,coarse,context)
            if any(v is None or not math.isfinite(v) for v in values): continue
            if not any(v is not None and v>=p.MINIMUM_ALTITUDE_DEGREES for v in values): continue
            for left,right,low,high in zip(coarse,coarse[1:],values,values[1:]):
                if (low>=p.MINIMUM_ALTITUDE_DEGREES)==(high>=p.MINIMUM_ALTITUDE_DEGREES): continue
                at=left.astimezone(timezone.utc)+timedelta(minutes=1)
                while at<right.astimezone(timezone.utc):
                    paired.append(len(coords)-1); pairs.append((name,at.astimezone(left.tzinfo)))
                    at+=timedelta(minutes=1)
        for offset in range(0,len(paired),512):
            chunk=pairs[offset:offset+512]
            frame=AltAz(obstime=Time([at.astimezone(timezone.utc) for _,at in chunk]),location=a._get_location(context))
            results=SkyCoord(coords)[paired[offset:offset+512]].transform_to(frame).alt.deg
            for (name,at),value in zip(chunk,results):
                a.get_altitudes_at.seed_exact_samples(name,[at],[round(float(value),1)],context)
        if coords:
            moon=a._moon_coordinate_at(midpoint,context)
            values=SkyCoord(coords).separation(moon).deg
            for name,value in zip(fixed,values):
                a.get_moon_separation_at.seed_exact_result(round(float(value),1),name,midpoint,context)
    prepare._geometry_probe=True
    p.prepare_fixed_target_altitudes=prepare

