from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class RigTargetFit:
    fits: Optional[bool]
    label: str
    margin_degrees: Optional[float]
    reason: str


@dataclass(frozen=True)
class RigRunPlan:
    total_frames: int
    run_count: Optional[int]
    frames_per_run: Optional[int]
    label: str
    reason: str


@dataclass(frozen=True)
class RigProfile:
    key: str
    manufacturer: str
    model: str
    aperture_mm: Optional[float]
    focal_length_mm: Optional[float]
    focal_ratio: Optional[float]
    sensor_name: Optional[str]
    resolution: Optional[Tuple[int, int]]
    pixel_size_um: Optional[float]
    sensor_size_mm: Optional[Tuple[float, float]]
    native_fov_degrees: Optional[Tuple[float, float]]
    supported_exposures_seconds: Tuple[int, ...]
    default_gain: Optional[float]
    read_noise_electrons: Optional[float]
    full_well_electrons: Optional[float]
    filters: Tuple[str, ...]
    mount_type: Optional[str]
    tracking_modes: Tuple[str, ...]
    frame_limit: Optional[int]
    storage_gb: Optional[float]
    battery_life_hours: Optional[float]
    dew_heater_battery_life_hours: Optional[float]
    operating_temperature_c: Optional[Tuple[float, float]]
    source_urls: Tuple[str, ...]
    confidence: str
    notes: str = ""

    @property
    def field_width_degrees(self) -> Optional[float]:
        if self.native_fov_degrees is None:
            return None
        return max(self.native_fov_degrees)

    @property
    def field_height_degrees(self) -> Optional[float]:
        if self.native_fov_degrees is None:
            return None
        return min(self.native_fov_degrees)

    def assess_target_fit(
        self,
        target_width_degrees: Optional[float],
        target_height_degrees: Optional[float],
    ) -> RigTargetFit:
        if (
            target_width_degrees is None
            or target_height_degrees is None
            or self.field_width_degrees is None
            or self.field_height_degrees is None
        ):
            return RigTargetFit(
                fits=None,
                label="Unknown fit",
                margin_degrees=None,
                reason="Target size or rig field of view is incomplete.",
            )

        target_width = max(target_width_degrees, target_height_degrees)
        target_height = min(target_width_degrees, target_height_degrees)
        width_margin = self.field_width_degrees - target_width
        height_margin = self.field_height_degrees - target_height
        margin = round(min(width_margin, height_margin), 2)

        if margin < 0:
            return RigTargetFit(
                fits=False,
                label="Too large",
                margin_degrees=margin,
                reason="The target is larger than the rig's native field of view.",
            )

        largest_field = max(self.field_width_degrees, self.field_height_degrees)
        largest_target = max(target_width, target_height)
        fill_ratio = largest_target / largest_field if largest_field else 0
        if fill_ratio < 0.18:
            return RigTargetFit(
                fits=True,
                label="Very small",
                margin_degrees=margin,
                reason="The target fits, but it will appear small in this rig.",
            )
        if margin <= 0.2:
            return RigTargetFit(
                fits=True,
                label="Tight fit",
                margin_degrees=margin,
                reason="The target fits, but framing tolerance is narrow.",
            )
        return RigTargetFit(
            fits=True,
            label="Comfortable fit",
            margin_degrees=margin,
            reason="The target fits comfortably in this rig's field of view.",
        )

    def estimate_run_plan(
        self,
        *,
        imaging_minutes: int,
        sub_exposure_seconds: int,
    ) -> RigRunPlan:
        if imaging_minutes <= 0 or sub_exposure_seconds <= 0:
            return RigRunPlan(
                total_frames=0,
                run_count=0,
                frames_per_run=None,
                label="No frames",
                reason="The plan has no positive imaging time or sub-exposure length.",
            )

        total_seconds = imaging_minutes * 60
        total_frames = total_seconds // sub_exposure_seconds
        if total_seconds % sub_exposure_seconds:
            total_frames += 1

        if self.frame_limit is None:
            return RigRunPlan(
                total_frames=total_frames,
                run_count=None,
                frames_per_run=None,
                label="Frame limit unknown",
                reason="This rig profile does not record a single-run frame limit.",
            )

        if total_frames <= self.frame_limit:
            return RigRunPlan(
                total_frames=total_frames,
                run_count=1,
                frames_per_run=total_frames,
                label="Single run",
                reason="The plan fits inside this rig's recorded frame limit.",
            )

        run_count = total_frames // self.frame_limit
        if total_frames % self.frame_limit:
            run_count += 1
        return RigRunPlan(
            total_frames=total_frames,
            run_count=run_count,
            frames_per_run=self.frame_limit,
            label="Split run",
            reason="The plan exceeds this rig's recorded single-run frame limit.",
        )


RIG_PROFILES: Dict[str, RigProfile] = {
    "dwarf-2": RigProfile(
        key="dwarf-2",
        manufacturer="DWARFLAB",
        model="DWARF II",
        aperture_mm=24,
        focal_length_mm=100,
        focal_ratio=4.2,
        sensor_name="Sony IMX415 STARVIS",
        resolution=None,
        pixel_size_um=None,
        sensor_size_mm=None,
        native_fov_degrees=None,
        supported_exposures_seconds=(15,),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Alt-azimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=64,
        battery_life_hours=None,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=(-10, 45),
        source_urls=(
            "https://checkout.dwarflab.com/en-de/products/dwarf-2-smart-telescope",
            "https://dwarflab.com/en-ca/pages/faqs",
        ),
        confidence="manufacturer",
        notes=(
            "Official specs list a 3 degree telephoto field of view but do not "
            "state width/height, so Polaris leaves native_fov_degrees unknown "
            "for rectangular framing. Includes 64GB microSD; maximum supported "
            "microSD is 512GB."
        ),
    ),
    "dwarf-3": RigProfile(
        key="dwarf-3",
        manufacturer="DWARFLAB",
        model="DWARF 3",
        aperture_mm=35,
        focal_length_mm=150,
        focal_ratio=4.3,
        sensor_name="Sony IMX678 STARVIS 2",
        resolution=(3840, 2160),
        pixel_size_um=2.0,
        sensor_size_mm=None,
        native_fov_degrees=(3.38, 1.9),
        supported_exposures_seconds=(15, 30, 60),
        default_gain=60,
        read_noise_electrons=0.6,
        full_well_electrons=11270,
        filters=("VIS", "Astro", "Dual-Band"),
        mount_type="Alt-azimuth; EQ mode supported",
        tracking_modes=("alt_az", "equatorial"),
        frame_limit=999,
        storage_gb=128,
        battery_life_hours=5.5,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=(-20, 45),
        source_urls=(
            "https://www.dwarflab.com/us/products/dwarf-3-smart-telescope",
            "https://help.dwarflab.com/en/docs/DWARF-3-Unboxing-and-Quick-Setup",
            "https://help.dwarflab.com/en/docs/DWARF-3-Smart-Telescope-User-Manual-Part1-App-Interface-Introduction?product=dwarf-3",
        ),
        confidence="manufacturer_and_help_center",
        notes=(
            "Official specs list 60s tele exposure in EQ mode; the help manual "
            "recommends 15-60s and gain 60-80 for advanced deep-sky sessions. "
            "The 999-frame limit is from DWARF's documented default/max frame "
            "count behavior, not an equipment-control promise."
        ),
    ),
    "dwarf-mini": RigProfile(
        key="dwarf-mini",
        manufacturer="DWARFLAB",
        model="DWARF mini",
        aperture_mm=30,
        focal_length_mm=150,
        focal_ratio=None,
        sensor_name="Sony IMX662",
        resolution=(1920, 1080),
        pixel_size_um=2.9,
        sensor_size_mm=None,
        native_fov_degrees=None,
        supported_exposures_seconds=(15, 30, 60, 90),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Alt-azimuth; EQ mode supported",
        tracking_modes=("alt_az", "equatorial"),
        frame_limit=None,
        storage_gb=64,
        battery_life_hours=4,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=(-10, 60),
        source_urls=(
            "https://checkout.dwarflab.com/pages/dwarf-mini-smart-telescope",
            "https://help.dwarflab.com/en/docs/DWARF-mini-Smart-Telescope-User-Manual",
            "https://www.kenko-tokina.co.jp/optics/tele_scope/dwarf/dwarfmini.html",
        ),
        confidence="manufacturer_and_help_center",
        notes=(
            "Official DWARFLAB product copy highlights sharp stars on 90s "
            "exposures in EQ mode. Kenko-Tokina's official regional spec page "
            "lists 64GB storage and 4h battery life."
        ),
    ),
    "seestar-s50": RigProfile(
        key="seestar-s50",
        manufacturer="ZWO",
        model="Seestar S50",
        aperture_mm=50,
        focal_length_mm=250,
        focal_ratio=5.0,
        sensor_name="Sony IMX462",
        resolution=(1920, 1080),
        pixel_size_um=2.9,
        sensor_size_mm=None,
        native_fov_degrees=(1.29, 0.73),
        supported_exposures_seconds=(10,),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=("UV/IR Cut", "Dual narrowband"),
        mount_type="Alt-azimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=64,
        battery_life_hours=6,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=(-10, 40),
        source_urls=(
            "https://www.seestar.com/products/seestar-s50",
            "https://us.seestar.com/blogs/faq/s50",
        ),
        confidence="manufacturer_and_official_faq",
        notes=(
            "Official FAQ records a 10s single-frame limit caused by the "
            "Alt/Az field-rotation strategy, no EQ conversion, and no guiding. "
            "Sensor noise curve and single-run frame limit are not included."
        ),
    ),
    "seestar-s30": RigProfile(
        key="seestar-s30",
        manufacturer="ZWO",
        model="Seestar S30",
        aperture_mm=30,
        focal_length_mm=150,
        focal_ratio=5.0,
        sensor_name="Sony IMX662",
        resolution=(1920, 1080),
        pixel_size_um=None,
        sensor_size_mm=None,
        native_fov_degrees=(2.46, 1.38),
        supported_exposures_seconds=(10,),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=("UV/IR Cut", "Dark", "Astronomical light pollution"),
        mount_type="Alt-azimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=64,
        battery_life_hours=None,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=(-10, 40),
        source_urls=("https://www.seestar.com/blogs/faq/s30",),
        confidence="official_faq_partial",
        notes=(
            "Official FAQ gives sensor, aperture, focal ratio, focal length, "
            "tele FOV, filters, storage, and temperature range. Battery life "
            "and single-run frame limit are not included."
        ),
    ),
    "stellina": RigProfile(
        key="stellina",
        manufacturer="Vaonis",
        model="Stellina",
        aperture_mm=80,
        focal_length_mm=400,
        focal_ratio=5.0,
        sensor_name="Sony back-illuminated CMOS",
        resolution=(3096, 2080),
        pixel_size_um=2.4,
        sensor_size_mm=None,
        native_fov_degrees=(1.0, 0.7),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=("Light pollution",),
        mount_type="Automated alt-azimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=None,
        battery_life_hours=5,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=(
            "https://vaonis.com/pages/stellina-observation-station",
            "https://support.vaonis.com/portal/en/kb/articles/que-peut-on-photographier-avec-stellina",
            "https://support.vaonis.com/portal/en/kb/articles/quelle-type-de-batterie-est-utilis%C3%A9-par-stellina",
        ),
        confidence="manufacturer_and_help_center",
        notes=(
            "Vaonis support describes Stellina's field as approximately 1 x "
            "0.7 degrees. Battery life comes from the included 10,000 mAh "
            "power bank guidance."
        ),
    ),
    "vespera-ii": RigProfile(
        key="vespera-ii",
        manufacturer="Vaonis",
        model="Vespera II",
        aperture_mm=50,
        focal_length_mm=250,
        focal_ratio=5.0,
        sensor_name="Sony IMX585",
        resolution=(3840, 2160),
        pixel_size_um=2.9,
        sensor_size_mm=(11.2, 6.3),
        native_fov_degrees=(2.5, 1.4),
        supported_exposures_seconds=(10,),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Alt-azimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=25,
        battery_life_hours=4,
        dew_heater_battery_life_hours=2.5,
        operating_temperature_c=None,
        source_urls=("https://vaonis.com/pages/product/vespera-ii",),
        confidence="manufacturer",
        notes=(
            "Vaonis specs list FITS 16-bit unit images, native field of view, "
            "and 4h battery life. Vaonis support lists 2.5h battery life with "
            "dew heating active."
        ),
    ),
    "vespera-pro": RigProfile(
        key="vespera-pro",
        manufacturer="Vaonis",
        model="Vespera Pro",
        aperture_mm=50,
        focal_length_mm=250,
        focal_ratio=5.0,
        sensor_name="Sony IMX676",
        resolution=(3536, 3536),
        pixel_size_um=2.0,
        sensor_size_mm=(7.0, 7.0),
        native_fov_degrees=(1.6, 1.6),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Alt-azimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=225,
        battery_life_hours=11,
        dew_heater_battery_life_hours=8,
        operating_temperature_c=None,
        source_urls=(
            "https://vaonis.com/products/vespera-pro",
            "https://support.vaonis.com/portal/en/kb/articles/what-is-vespera-s-autonomy-time",
        ),
        confidence="manufacturer_and_help_center",
        notes="Vaonis support lists Vespera Pro autonomy as 11h normal and 8h with dew heating.",
    ),
    "vespera-3": RigProfile(
        key="vespera-3",
        manufacturer="Vaonis",
        model="Vespera 3",
        aperture_mm=50,
        focal_length_mm=245,
        focal_ratio=4.9,
        sensor_name="Sony IMX585",
        resolution=(3840, 2160),
        pixel_size_um=2.9,
        sensor_size_mm=(11.2, 6.3),
        native_fov_degrees=(2.6, 1.4),
        supported_exposures_seconds=(10,),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Alt-azimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=115,
        battery_life_hours=11,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=("https://vaonis.com/pages/vespera-new-generation",),
        confidence="manufacturer",
        notes="New-generation Vaonis specs list Vespera 3 and Vespera Pro 2 together.",
    ),
    "vespera-pro-2": RigProfile(
        key="vespera-pro-2",
        manufacturer="Vaonis",
        model="Vespera Pro 2",
        aperture_mm=50,
        focal_length_mm=245,
        focal_ratio=4.9,
        sensor_name="Sony IMX676",
        resolution=(3536, 3536),
        pixel_size_um=2.0,
        sensor_size_mm=(7.0, 7.0),
        native_fov_degrees=(1.6, 1.6),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Alt-azimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=225,
        battery_life_hours=11,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=("https://vaonis.com/pages/vespera-new-generation",),
        confidence="manufacturer",
        notes="New-generation Vaonis specs list native and mosaic field of view; dew-heater autonomy is not separately published on that page.",
    ),
    "hestia": RigProfile(
        key="hestia",
        manufacturer="Vaonis",
        model="Hestia",
        aperture_mm=30,
        focal_length_mm=None,
        focal_ratio=None,
        sensor_name="User smartphone camera",
        resolution=None,
        pixel_size_um=None,
        sensor_size_mm=None,
        native_fov_degrees=None,
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Manual smartphone optical system",
        tracking_modes=(),
        frame_limit=None,
        storage_gb=None,
        battery_life_hours=None,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=("https://vaonis.com/pages/product/hestia",),
        confidence="manufacturer",
        notes=(
            "Hestia has no onboard electronics or battery and depends on the "
            "user's smartphone. Official specs give a 1.8 degree field of view "
            "but not rectangular sensor framing."
        ),
    ),
    "celestron-origin": RigProfile(
        key="celestron-origin",
        manufacturer="Celestron",
        model="Origin Intelligent Home Observatory",
        aperture_mm=152,
        focal_length_mm=335,
        focal_ratio=2.2,
        sensor_name="Sony IMX178LQJ",
        resolution=(3096, 2080),
        pixel_size_um=2.4,
        sensor_size_mm=None,
        native_fov_degrees=(1.27, 0.85),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=("Integrated filter drawer",),
        mount_type="Computerized GoTo altazimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=None,
        battery_life_hours=6,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=("https://www.celestron.com/products/celestron-origin-intelligent-home-observatory-12099-old-version",),
        confidence="manufacturer",
        notes="First-generation Origin is discontinued; specs retained for existing owners.",
    ),
    "celestron-origin-mark-ii": RigProfile(
        key="celestron-origin-mark-ii",
        manufacturer="Celestron",
        model="Origin Mark II Intelligent Home Observatory",
        aperture_mm=152,
        focal_length_mm=335,
        focal_ratio=2.2,
        sensor_name="Sony IMX678-AAQR1",
        resolution=(3856, 2180),
        pixel_size_um=2.0,
        sensor_size_mm=None,
        native_fov_degrees=(1.32, 0.75),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=("Integrated filter drawer",),
        mount_type="Computerized GoTo altazimuth",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=None,
        battery_life_hours=6,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=("https://www.celestron.com/products/celestron-origin-intelligent-home-observatory",),
        confidence="manufacturer",
        notes="Battery is listed as capable of 6+ hours; Polaris stores 6 as the conservative baseline.",
    ),
    "unistellar-odyssey": RigProfile(
        key="unistellar-odyssey",
        manufacturer="Unistellar",
        model="Odyssey",
        aperture_mm=85,
        focal_length_mm=320,
        focal_ratio=3.9,
        sensor_name=None,
        resolution=None,
        pixel_size_um=1.45,
        sensor_size_mm=None,
        native_fov_degrees=(0.75, 0.56),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Motorized Alt-Az",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=64,
        battery_life_hours=5,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=(
            "https://www.unistellar.com/odyssey/",
            "https://help.unistellar.com/hc/en-us/articles/4406616411922-Compare-Our-Smart-Telescopes",
        ),
        confidence="manufacturer_and_help_center",
        notes="Odyssey and Odyssey Pro share optical/electronic specs; Pro adds Nikon eyepiece technology.",
    ),
    "unistellar-odyssey-pro": RigProfile(
        key="unistellar-odyssey-pro",
        manufacturer="Unistellar",
        model="Odyssey Pro",
        aperture_mm=85,
        focal_length_mm=320,
        focal_ratio=3.9,
        sensor_name=None,
        resolution=None,
        pixel_size_um=1.45,
        sensor_size_mm=None,
        native_fov_degrees=(0.75, 0.56),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Motorized Alt-Az",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=64,
        battery_life_hours=5,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=(
            "https://www.unistellar.com/odyssey/",
            "https://help.unistellar.com/hc/en-us/articles/4406616411922-Compare-Our-Smart-Telescopes",
        ),
        confidence="manufacturer_and_help_center",
        notes="Odyssey Pro shares Odyssey specs and adds Nikon eyepiece technology.",
    ),
    "unistellar-equinox-2": RigProfile(
        key="unistellar-equinox-2",
        manufacturer="Unistellar",
        model="eQuinox 2",
        aperture_mm=114,
        focal_length_mm=450,
        focal_ratio=4.0,
        sensor_name=None,
        resolution=None,
        pixel_size_um=2.9,
        sensor_size_mm=None,
        native_fov_degrees=(0.76, 0.57),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Motorized Alt-Az",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=64,
        battery_life_hours=11,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=(
            "https://www.unistellar.com/expert/",
            "https://help.unistellar.com/hc/en-us/articles/4406616411922-Compare-Our-Smart-Telescopes",
        ),
        confidence="manufacturer_and_help_center",
        notes="Unistellar comparison docs list optics, FOV, storage, and battery for eQuinox 2.",
    ),
    "unistellar-evscope-2": RigProfile(
        key="unistellar-evscope-2",
        manufacturer="Unistellar",
        model="eVscope 2",
        aperture_mm=114,
        focal_length_mm=450,
        focal_ratio=4.0,
        sensor_name="Sony IMX347",
        resolution=(3200, 2400),
        pixel_size_um=2.9,
        sensor_size_mm=None,
        native_fov_degrees=(0.76, 0.57),
        supported_exposures_seconds=(),
        default_gain=None,
        read_noise_electrons=None,
        full_well_electrons=None,
        filters=(),
        mount_type="Motorized Alt-Az",
        tracking_modes=("alt_az",),
        frame_limit=None,
        storage_gb=64,
        battery_life_hours=9,
        dew_heater_battery_life_hours=None,
        operating_temperature_c=None,
        source_urls=(
            "https://www.unistellar.com/expert/",
            "https://shop.unistellar.com/products/evscope-2?variant=40131698163735",
        ),
        confidence="manufacturer",
        notes="Unistellar pages vary between older 10h and current 9h battery references; Polaris stores the current product/spec comparison value.",
    ),
}


def get_rig_profile(key_or_model: str) -> Optional[RigProfile]:
    normalized = (
        key_or_model.strip()
        .lower()
        .replace("_", "-")
        .replace(" ii", " 2")
        .replace(" iii", " 3")
    )
    if normalized in RIG_PROFILES:
        return RIG_PROFILES[normalized]

    compact = normalized.replace(" ", "-")
    if compact in RIG_PROFILES:
        return RIG_PROFILES[compact]

    for profile in RIG_PROFILES.values():
        model_normalized = (
            profile.model.lower()
            .replace("_", "-")
            .replace(" ii", " 2")
            .replace(" iii", " 3")
        )
        if normalized == model_normalized or compact == model_normalized.replace(" ", "-"):
            return profile
    return None
