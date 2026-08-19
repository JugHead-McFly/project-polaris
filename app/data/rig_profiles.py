from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class RigTargetFit:
    fits: Optional[bool]
    label: str
    margin_degrees: Optional[float]
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


RIG_PROFILES: Dict[str, RigProfile] = {
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
        source_urls=(
            "https://www.dwarflab.com/us/products/dwarf-3-smart-telescope",
            "https://help.dwarflab.com/en/docs/DWARF-3-Unboxing-and-Quick-Setup",
        ),
        confidence="manufacturer_and_help_center",
        notes=(
            "DWARF 3 exposure behavior has changed through firmware; Polaris "
            "keeps 15 seconds conservative unless EQ mode or capture history "
            "supports longer sub-exposures."
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
        source_urls=(
            "https://www.seestar.com/products/seestar-s50",
            "https://us.seestar.com/blogs/faq/s50",
        ),
        confidence="manufacturer_and_official_faq",
        notes=(
            "Pixel size is from an official Seestar review/FAQ source rather "
            "than the main product table; sensor noise curve is not included."
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
        source_urls=("https://www.seestar.com/blogs/faq/s30",),
        confidence="official_faq_partial",
        notes="Official FAQ gives sensor, aperture, focal ratio, focal length, and tele FOV.",
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
        source_urls=("https://vaonis.com/pages/product/vespera-ii",),
        confidence="manufacturer",
        notes="Vaonis specs list FITS 16-bit unit images and native field of view.",
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
        source_urls=("https://vaonis.com/pages/vespera-new-generation",),
        confidence="manufacturer",
        notes="New-generation Vaonis specs list Vespera 3 and Vespera Pro 2 together.",
    ),
}


def get_rig_profile(key_or_model: str) -> Optional[RigProfile]:
    normalized = key_or_model.strip().lower().replace("_", "-")
    if normalized in RIG_PROFILES:
        return RIG_PROFILES[normalized]

    compact = normalized.replace(" ", "-")
    if compact in RIG_PROFILES:
        return RIG_PROFILES[compact]

    for profile in RIG_PROFILES.values():
        if normalized == profile.model.lower().replace(" ", "-"):
            return profile
    return None
