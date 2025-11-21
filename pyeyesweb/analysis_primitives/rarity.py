import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow


class Rarity:

    def __call__(self, sliding_window: SlidingWindow, alpha: float = 0.5) -> dict:
        if not sliding_window.is_full():
            return np.nan

        samples, _ = sliding_window.to_array()
        n_samples = len(samples)

        # Number of bins
        n_bins = int(np.sqrt(n_samples))
        n_bins = max(n_bins, 1)
        print(f"Using {n_bins} for {n_samples} samples.")

        # Histogram
        counts, bin_edges = np.histogram(samples, bins=n_bins)

        # Convert to probability distribution
        probabilities = counts / n_samples

        # Most probable bin
        most_probable_bin_index = np.argmax(probabilities)
        most_probable_p = probabilities[most_probable_bin_index]

        # Current sample bin
        last_sample = samples[-1]
        last_sample_bin_index = np.searchsorted(bin_edges, last_sample, side='right') - 1
        last_sample_bin_index = np.clip(last_sample_bin_index, 0, n_bins - 1)
        last_sample_p = probabilities[last_sample_bin_index]

        # Compute rarity using probabilities
        d1 = abs(most_probable_bin_index - last_sample_bin_index)  # distance in bin space
        d2 = most_probable_p - last_sample_p  # probability difference

        rarity = d1 * d2 * alpha
        return {"rarity": float(rarity)}
