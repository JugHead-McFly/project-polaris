"""Focused autumn/winter catalog addition; provenance in docs/seasonal-catalog.md.

No capture settings are inferred from catalog geometry. The existing four-hour
fallback goal is retained so importing catalog data cannot reopen completed goals.
"""

SEASONAL_TARGETS = {
    "M33": dict(name="Triangulum Galaxy", ra="01h33m50.897s", dec="+30d39m36.63s",
                size=(60.26/60, 35.48/60), object_type="Spiral galaxy", constellation="Triangulum"),
    "M45": dict(name="Pleiades", ra="03h46m24.2s", dec="+24d06m50s",
                size=(76.86/60, 76.86/60), object_type="Open cluster", constellation="Taurus"),
    "M42": dict(name="Orion Nebula", ra="05h35m16.8s", dec="-05d23m15s",
                size=(66/60, 66/60), object_type="Emission nebula", constellation="Orion"),
    "M1": dict(name="Crab Nebula", ra="05h34m31.97s", dec="+22d00m52.1s",
               size=(8/60, 4/60), object_type="Supernova remnant", constellation="Taurus"),
    "M78": dict(name="Messier 78", ra="05h46m45.82s", dec="+00d04m45.5s",
                size=(4.5/60, 4.5/60), object_type="Reflection nebula", constellation="Orion"),
    "NGC281": dict(name="Pacman Nebula", ra="00h52m59.35s", dec="+56d37m18.8s",
                   size=(35/60, 30/60), object_type="Emission nebula", constellation="Cassiopeia"),
}
