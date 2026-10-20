# Porting status

PyEyesWeb is a Python layer over a compiled port of the EyesWeb Expressive Gesture Analysis library: the algorithms are ports of
EyesWeb blocks, plus features of the laboratory that have no EyesWeb original. This page states the policy of the port, how a
correction of the original is recorded, and which blocks of earlier versions are no longer in the library.

## What the catalog holds

```{doctest}
>>> import pyeyesweb
>>> entries = pyeyesweb.catalog()
>>> len(entries), sum(info.eyesweb_block is not None for info in entries), sum(info.eyesweb_block is None for info in entries)
(60, 47, 13)
```

The first number is the number of features, the second the number that come from an EyesWeb block (the block is the
`EYESWEB_BLOCK` of the class and the "EyesWeb" badge of its page), and the third the number of features of the laboratory, which have
no original and are tested by their behaviour, by the catalog-wide suites and by frozen data.

## Fidelity policy

- **A port reproduces the original block**: the same formulas, the same order of floating-point operations where it matters, the same
  defaults and the same edge cases. The EyesWeb source is the only authority; mathematics that is not in the original is not invented.
- **Hangs, crashes and undefined behaviour are not reproduced.** The evident intent is implemented and the difference is described.
- **A deviation that changes numbers needs a decision of the maintainers.** Until it is decided it is asked about and not guessed.
- **Once decided, the corrected behaviour is the behaviour of the core. There is no flag.** No parameter that switches a correction on or off, such as a flag named `legacy` or
  `compat`, exists, and none is added; the numbers of an earlier behaviour are not available. A page and a docstring that
  describe a corrected behaviour mark it with the words **Corrected in the core**, followed by a one-line description.
- **A block that the maintainers retire is removed** from the core, the bindings and the Python package together.

```{doctest}
>>> import inspect
>>> flags = [(info.name, name) for info in entries for name in inspect.signature(info.cls).parameters
...          if name.startswith(("legacy", "compat")) or name.endswith("_fix")]
>>> flags
[]
```

### A correction you can observe

The default tolerance of `SampleEntropy` is relative to the scale of the signal. The absolute tolerance of the original matched
nothing on a signal of another scale and gave infinite entropies; the corrected default gives a finite value whatever the scale.

```{doctest}
>>> from pyeyesweb.analysis_primitives import SampleEntropy
>>> signal = np.random.default_rng(0).normal(size=1000) * 500.0
>>> entropy = SampleEntropy(window=200, hop=100, embedding_dimension=3).run(signal).sample_entropy
>>> bool(np.isfinite(entropy[~np.isnan(entropy)]).all())
True
>>> inspect.signature(SampleEntropy).parameters["tolerance"], inspect.signature(SampleEntropy).parameters["relative_tolerance"]
(<Parameter "tolerance: float | None = None">, <Parameter "relative_tolerance: float = 0.2">)
```

### Where corrections are described

Each correction is described where the feature is: in the **Notes** of its docstring, which the generated API page shows, and in
the theory page of its family ({doc}`../theory/kinematics_energy`, {doc}`../theory/smoothness`,
{doc}`../theory/shape_symmetry_balance`, {doc}`../theory/impulsivity_suddenness`, {doc}`../theory/gesture_segmentation`,
{doc}`../theory/entropy_rarity_periodicity`, {doc}`../theory/synchronization`, {doc}`../theory/dominance`,
{doc}`../theory/humanoid_models`, {doc}`../theory/imaging`). The corrections of the 2.0 release are also in the changelog
({doc}`../changelog`).

A change of the Python layer that alters numbers follows the same rule: it is a decision, it is documented in the docstring and in
the changelog, and no test of numbers is edited to make it pass.

## Removed blocks and features

The names below no longer exist in any public module of the 2.0 release. The reasons are those given by the maintainers when the
block was retired.

| Removed | Use instead | Reason |
|---|---|---|
| `Lightness` | none | its formula (the rarity of the horizontal share of the energy) is not a valid measure of lightness; a redesign is deferred |
| `Clusterability` (Hopkins statistic) | none | removed to reduce the size of the library |
| `StatisticalMoment` | `numpy` and `scipy.stats` (`mean`, `std`, `skew`, `kurtosis`) | simple measures that are available elsewhere |
| `ZeroCross` | `numpy`: count the sign changes with `np.diff(np.sign(x))` | replaceable by one line |
| `CannyEdgeDetector` | OpenCV `cv2.Canny` | replaceable; no feature used it |
| `SkeletonManipulator`, the OpenNI and other legacy device presets (`input_type`, `skeleton_mode`), the Bones `algorithm` of `KineticEnergy` | `skeleton=` with a preset or your own `Skeleton` | not used |
| `NoPreparationDetector`, `NoPreparationDetector2` | none | removed to reduce the size of the library |
| the first algorithm of the event synchronization of `EventSynchronizationMECS`, `EventSynchronizationRealTime`, `TauEstimator`, `ScalarBinarySyncDetector` | `EventSynchronizationMECS` is the later algorithm only, with no `version` | not part of the current EyesWeb project, or only of an old one |
| the trajectory data type and its blocks (`Trajectory`, `TrajectoryBuilder`, `GetKinematicalFeatures`, `KinematicalFeatures`, `NumericDerivative`, the trajectory input mode of `Kinematics`) | `Kinematics` on plain arrays (`from_point`, `from_series`); `Directness` and `TrajectoryNonPlanarity` take `(n, D)` arrays of points, row 0 the newest | the data type was not needed on plain arrays |
| the geometric transforms of the trajectory (`rotation_matrix`, `rotate_x`, `rotate_y`, `rotate_z`, `rotate`, `scale`, `translate`, `rescale_in_range`, `remap_axis`, `convert_on_2d`) | `numpy` | same decision |
| `EllipsoidFitSphericity` | `EllipsoidSphericity().process(points)`; `axis_ratio` is the former value | merged |

The 1.x classes and the renamed features have their own table in the migration guide ({doc}`../changelog`). That the names are gone
can be checked:

```{doctest}
>>> import importlib
>>> removed = "Lightness Clusterability StatisticalMoment ZeroCross CannyEdgeDetector SkeletonManipulator NoPreparationDetector TauEstimator ScalarBinarySyncDetector EventSynchronizationRealTime GetKinematicalFeatures TrajectoryBuilder NumericDerivative EllipsoidFitSphericity".split()
>>> packages = [importlib.import_module(name) for name in ("pyeyesweb", "pyeyesweb.data_models", "pyeyesweb.physical_signals", "pyeyesweb.low_level", "pyeyesweb.mid_level", "pyeyesweb.high_level", "pyeyesweb.analysis_primitives", "pyeyesweb.analysis_primitives.synchronization", "pyeyesweb.skeletons")]
>>> [name for name in removed if any(hasattr(package, name) for package in packages)]
[]
```

## What is still open

The skeleton presets `qualisys_sport`, `mediapipe` and `openpose` are incomplete: their empty fields are documented as such and are
to be filled by the maintainers ({doc}`../howto/map_skeleton`). The compiled core is released as its own package; the packaging
has not been done yet ({doc}`architecture`).
