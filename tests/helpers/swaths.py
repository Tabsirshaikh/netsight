import numpy as np


def smooth_swath(n_pings: int = 10, n_bins: int = 200, seed: int = 0) -> np.ndarray:
    """Along-track-correlated seabed: one texture row repeated with small noise."""
    rng = np.random.default_rng(seed)
    texture = 100.0 + 30.0 * np.sin(np.arange(n_bins) * 0.2)
    return texture + rng.normal(0.0, 1.0, (n_pings, n_bins))
