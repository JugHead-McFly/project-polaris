from pathlib import Path
from typing import Dict

import numpy as np
from astropy.io import fits
from astropy.stats import mad_std
from photutils.detection import DAOStarFinder

from app.models import Capture


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

    stars_detected = 0

    if background_noise > 0:
        star_finder = DAOStarFinder(
            fwhm=3.0,
            threshold=5.0 * background_noise,
        )

        sources = star_finder(background_subtracted)

        if sources is not None:
            stars_detected = len(sources)

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
        "stars_detected": int(stars_detected),
    }