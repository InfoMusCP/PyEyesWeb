# Load the example data

The tutorials and the examples of this documentation use motion-capture recordings of expressive movement: one performer,
Qualisys system, 41 markers, 100 Hz, one session of 2024. {py:mod}`pyeyesweb.datasets` finds a recording, reads it, and returns
the positions as a NumPy array with the names of the joints, the sampling rate and the unit. It computes nothing else: derived
signals belong to the code that uses them. The module is a convenience for the examples, not part of the feature API, and it
needs no dependency beyond NumPy to read a local file.

```{admonition} The recordings are not available online yet
:class: warning

Where the recordings will be hosted has not been decided, so `pyeyesweb.datasets.BASE_URL` is `None` and nothing is
downloaded. The recordings are in the `examples/data` folder of the repository: they are found when you work from a checkout, or
when `PYEYESWEB_DATA` points to a folder that holds them. With a package installed from PyPI and neither of these, loading a
trial raises `FileNotFoundError` with a message that says so (shown at the end of this page). The download itself (with checksums,
using the optional dependency `pooch`) is written and will be switched on once there is an address.
```

The code on this page needs the recordings. The documentation checks skip these blocks (`:skipif:` on the `doctest` directive, which tests
whether trial 7 can be loaded) where the recordings are missing, and run the last block, which does not need them, everywhere.

## Which trials are there

{py:func}`~pyeyesweb.datasets.available_trials` lists the trial numbers that can be loaded now, and
{py:data}`~pyeyesweb.datasets.QUALISYS_TRIALS` says what each trial is: the task and the condition (trials 1, 2 and 9 are tests
and are not listed). The complete description of the session is in `examples/data/README.md`.

```{doctest}
:skipif: 7 not in __import__("pyeyesweb.datasets", fromlist=["x"]).available_trials()

>>> from pyeyesweb.datasets import QUALISYS_TRIALS, available_trials
>>> 7 in available_trials()
True
>>> QUALISYS_TRIALS[7]
('Clapping hands', 'synchronized')
>>> QUALISYS_TRIALS[8]
('Clapping hands', 'unsynchronized')
```

## Load a trial

{py:func}`~pyeyesweb.datasets.load_qualisys_trial` takes the trial number and returns a
{py:class}`~pyeyesweb.datasets.QualisysTrial`. The recordings hold 41 raw markers; by default they are averaged into the 20 joints
of a standard skeleton (`Head`, `Neck`, `Spine`, `Pelvis`, then left and right shoulder, elbow, wrist, hand, hip, knee, ankle
and foot, as defined in `markers_mappings.json`), and a marker that the system lost for a few frames (exported as 0, 0, 0)
is interpolated linearly. `positions` has the shape `(frames, joints, 3)`; `labels` gives the joint of each column;
`joint(name)` returns one joint.

```{doctest}
:skipif: 7 not in __import__("pyeyesweb.datasets", fromlist=["x"]).available_trials()

>>> from pyeyesweb.datasets import load_qualisys_trial
>>> trial = load_qualisys_trial(7, start=5, stop=15)
>>> trial.positions.shape
(1000, 20, 3)
>>> trial.labels[:4]
('Head', 'Neck', 'Spine', 'Pelvis')
>>> trial.sampling_rate, trial.units
(100.0, 'mm')
>>> trial.task, trial.condition
('Clapping hands', 'synchronized')
>>> trial.joint("Right_Hand").shape
(1000, 3)
```

## Choose a stretch of time: `start` and `stop`

`start` and `stop` are in **seconds** of the original recording; the frames from `start` up to, but not including, `stop` are
kept. Without them the whole trial is read. The `timestamps` of the result always start at 0 for the first frame returned and are
in seconds, as the features expect; `offset` keeps the time of that frame in the original recording. `window(start, stop)` cuts a
trial that is already loaded, with times counted from its first frame.

```{doctest}
:skipif: 7 not in __import__("pyeyesweb.datasets", fromlist=["x"]).available_trials()

>>> trial.timestamps[[0, -1]], trial.offset, trial.duration
(array([0.  , 9.99]), 5.0, 10.0)
>>> middle = trial.window(2.0, 4.0)
>>> middle.positions.shape, middle.offset
((200, 20, 3), 7.0)
```

Some of the recordings are long (the original files are several minutes), so a script that needs a few seconds should say
which. The copies of the recordings that the documentation builds use are trimmed to the stretches that the tutorials read
(`tools/trim_example_data.py`); asking one of them for a time it does not hold raises a `ValueError` that names the stretch it has.

## Units

Qualisys exports **millimetres** and the loader keeps them; the unit is in `trial.units`. The features take metres by default,
so convert the data once with {py:meth}`~pyeyesweb.datasets.QualisysTrial.to_units` (which returns a copy), or leave the data
in millimetres and give the feature `units="mm"` for the ten classes that take it (see {doc}`../concepts/time_units_parameters`).

```{doctest}
:skipif: 7 not in __import__("pyeyesweb.datasets", fromlist=["x"]).available_trials()

>>> metres = trial.to_units("m")
>>> metres.units
'm'
>>> bool(np.allclose(metres.positions, trial.positions / 1000))
True
>>> from pyeyesweb.low_level import Kinematics
>>> speed = Kinematics(sampling_rate=100.0).run(metres.joint("Right_Hand"), timestamps=metres.timestamps)
>>> speed.schema
Schema(Output('velocity', unit='m/s'))
```

## Give the skeleton to a feature

For the standard 20 joints, `trial.skeleton` is a {py:class}`~pyeyesweb.data_models.Skeleton` with uniform weights, the pelvis as
the reference joint, and the left and right joints as couples. Pass it as `skeleton=` to the features that work on a body;
each one then reads the joints it needs from the frames of `positions`.

```{doctest}
:skipif: 7 not in __import__("pyeyesweb.datasets", fromlist=["x"]).available_trials()

>>> from pyeyesweb.low_level import KineticEnergy
>>> skeleton = metres.skeleton
>>> skeleton.reference, len(skeleton.joints), len(skeleton.pairs)
('Pelvis', 20, 8)
>>> energy = KineticEnergy(skeleton=skeleton, sampling_rate=100.0).run(metres.positions, timestamps=metres.timestamps)
>>> energy.schema
Schema(Output('kinetic_energy', unit='<length>^2/s^2'))
```

Only a trial with the standard joints has a skeleton. With `standardize=False` the 41 raw markers are returned
(`labels` are the marker names); use it for features that take raw markers, and map them to a skeleton as described in
{doc}`map_skeleton`. A trimmed copy of a recording keeps the 41 markers only for the trials that a tutorial reads raw.

## Where the files are looked for

A recording is looked for in this order, and the first folder that holds the file is used:

1. the folder named by the environment variable `PYEYESWEB_DATA`, if it is set (it is also where a download is stored);
2. the `examples/data` folder of a repository checkout, so that the documentation builds offline from the repository;
3. the download cache: `PYEYESWEB_DATA`, otherwise the cache folder of the operating system. A file would be downloaded here from
   `BASE_URL` and checked against its SHA-256 sum; as `BASE_URL` is not set, this step finds nothing yet.

A folder given by `PYEYESWEB_DATA` has the layout of `examples/data`: `qualisys/trial7.tsv` (or the compressed
`trial7.tsv.gz`) and `markers_mappings.json`. Set it before the first call, in the shell, or from Python:

```python
import os
os.environ["PYEYESWEB_DATA"] = "/path/to/my/data"       # a folder with qualisys/trial7.tsv and markers_mappings.json
```

{py:func}`~pyeyesweb.datasets.cache_dir` gives the folder of the cache, and
{py:func}`~pyeyesweb.datasets.fetch_data_file` the path of any file of the data folder (a file from the first two places is
returned as it is, without a check).

## When the data are missing

Without a local copy the call fails with an error that names the folders it searched and says why nothing was downloaded. A file that
does not exist anywhere shows the same message:

```{doctest}
>>> from pyeyesweb.datasets import fetch_data_file
>>> fetch_data_file("qualisys/trial99.tsv")
Traceback (most recent call last):
  ...
FileNotFoundError: Example data file 'qualisys/trial99.tsv' was not found locally (...) and the example data are not available online yet (pyeyesweb.datasets.BASE_URL is None). Run from a checkout of the repository, or set the environment variable PYEYESWEB_DATA to a folder holding the files.
```

To use the features with your own recordings, nothing here is needed: any array of shape `(frames, joints, 3)` and a list of
labels work (see {doc}`../concepts/inputs` and {doc}`map_skeleton`).
