from pathlib import Path
from typing import Dict

import numpy as np
from astropy.io import fits
from astropy.stats import mad_std
from astropy.stats import sigma_clipped_stats
from photutils.detection import IRAFStarFinder

from app.models import Capture


def _as_luminance(image_data: np.ndarray) -> np.ndarray:
    image_data = np.asarray(
        image_data,
        dtype=np.float64,
    )
    image_data = np.squeeze(image_data)

    if image_data.ndim == 3:
        if image_data.shape[0] in (3, 4):
            image_data = np.mean(
                image_data[:3],
                axis=0,
            )
        elif image_data.shape[-1] in (3, 4):
            image_data = np.mean(
                image_data[..., :3],
                axis=-1,
            )
        else:
            image_data = np.mean(
                image_data,
                axis=0,
            )
    elif image_data.ndim > 3:
        raise ValueError(
            f"Unsupported FITS image shape: {image_data.shape}"
        )

    if image_data.ndim != 2:
        raise ValueError(
            f"Expected a 2D image but received shape {image_data.shape}"
        )

    return image_data


def _background_gradient(
    image_data: np.ndarray,
    signal_span: float,
) -> float:
    tile_medians = []
    for row in np.array_split(image_data, 4, axis=0):
        for tile in np.array_split(row, 4, axis=1):
            finite_tile = tile[np.isfinite(tile)]
            if finite_tile.size == 0:
                continue
            _, tile_median, _ = sigma_clipped_stats(
                finite_tile,
                sigma=3.0,
                maxiters=5,
            )
            tile_medians.append(float(tile_median))

    if len(tile_medians) < 2 or signal_span <= 0:
        return 0.0

    return float(
        (max(tile_medians) - min(tile_medians))
        / signal_span
    )


def _stellar_metrics(
    background_subtracted: np.ndarray,
    background_noise: float,
) -> Dict[str, float]:
    empty = {
        "stars_detected": 0,
        "star_sample_count": 0,
        "median_fwhm": None,
        "median_roundness": None,
        "median_sharpness": None,
        "median_star_snr": None,
    }
    if background_noise <= 0:
        return empty

    star_finder = IRAFStarFinder(
        threshold=5.0 * background_noise,
        fwhm=3.0,
        sharplo=0.2,
        sharphi=2.0,
        roundlo=0.0,
        roundhi=1.0,
        exclude_border=True,
    )
    sources = star_finder(background_subtracted)
    if sources is None or len(sources) == 0:
        return empty

    sample_size = min(250, len(sources))
    flux_order = np.argsort(
        np.asarray(sources["flux"])
    )
    sample = sources[flux_order[-sample_size:]]
    median_peak = float(
        np.nanmedian(sample["peak"])
    )

    return {
        "stars_detected": int(len(sources)),
        "star_sample_count": int(sample_size),
        "median_fwhm": float(
            np.nanmedian(sample["fwhm"])
        ),
        "median_roundness": float(
            np.nanmedian(sample["roundness"])
        ),
        "median_sharpness": float(
            np.nanmedian(sample["sharpness"])
        ),
        "median_star_snr": float(
            median_peak / background_noise
        ),
    }


def analyze_fits_file(capture: Capture) -> Dict[str, float]:
    if not capture.asset_path:
        raise FileNotFoundError(
            f"Capture '{capture.polaris_id}' has no asset path."
        )

    asset_path = Path(capture.asset_path)

    if not asset_path.exists():
        raise FileNotFoundError(
            f"FITS file was not found at '{asset_path}'."
        )

    with fits.open(asset_path) as hdul:
        image_data = hdul[0].data

    if image_data is None:
        raise ValueError(
            f"Capture '{capture.polaris_id}' contains no image data."
        )

    image_data = _as_luminance(image_data)

    finite_mask = np.isfinite(image_data)

    if not np.any(finite_mask):
        raise ValueError(
            "The FITS image contains no finite pixel values."
        )

    finite_data = image_data[finite_mask]

    median_value = float(np.median(finite_data))
    standard_deviation = float(np.std(finite_data))

    background_subtracted = image_data - median_value
    background_subtracted[~finite_mask] = 0

    background_noise = float(
        mad_std(
            background_subtracted,
            ignore_nan=True,
        )
    )

    signal_span = float(
        np.percentile(finite_data, 99.5)
        - median_value
    )
    background_gradient = _background_gradient(
        image_data=image_data,
        signal_span=signal_span,
    )
    maximum_value = float(np.max(finite_data))
    clipped_pixel_fraction = float(
        np.mean(finite_data >= maximum_value)
    )
    stellar_metrics = _stellar_metrics(
        background_subtracted=background_subtracted,
        background_noise=background_noise,
    )

    height, width = image_data.shape

    return {
        "width": int(width),
        "height": int(height),
        "mean_value": float(np.mean(finite_data)),
        "median_value": median_value,
        "standard_deviation": standard_deviation,
        "minimum_value": float(np.min(finite_data)),
        "maximum_value": float(np.max(finite_data)),
        "background_noise": background_noise,
        "relative_background_noise": (
            float(background_noise / abs(median_value))
            if median_value != 0
            else None
        ),
        "background_gradient": background_gradient,
        "clipped_pixel_fraction": clipped_pixel_fraction,
        **stellar_metrics,
    }
