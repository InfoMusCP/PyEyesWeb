"""Run by sphinx-gallery before each tutorial (``reset_modules`` in ``docs/conf.py``): the same state whatever ran before.

It lives in a module, not in ``conf.py``, so that ``sphinx_gallery_conf`` can be pickled by Sphinx's config cache.
"""


def reset_tutorial_state(gallery_conf, fname):
    """Close figures, restore the matplotlib defaults at dpi 90, seed NumPy, fix the print options."""
    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np

    plt.close("all")
    matplotlib.rcdefaults()
    plt.rcParams["figure.dpi"] = 90  # figures of the tutorials: dpi 80-100
    np.random.seed(0)
    np.set_printoptions(precision=4, suppress=True, linewidth=100)
