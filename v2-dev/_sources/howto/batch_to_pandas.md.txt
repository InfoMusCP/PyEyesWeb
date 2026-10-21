# Batch a recording to pandas

This page runs a recording through several features, collects the results in one table, and saves it. The recording here is
synthetic, so that the code runs anywhere; the same steps apply to a recording read with {doc}`load_data`. The tutorial
{ref}`sphx_glr_tutorials_06_capstone_plot_10_capstone.py` does the same on the example session and compares conditions.

pandas is an optional dependency of PyEyesWeb: everything except `Recorder.to_frame()` works with NumPy alone, and `to_frame()`
raises `ImportError` when pandas is not installed. The columns of a recorder can always be read as arrays
(`rec["name"]`, `rec.to_numpy()`).

## A recording and three features

A hand moves on an ellipse for ten seconds at 100 Hz. Positions are in metres and the timestamps are in seconds.

```{doctest}
>>> import pandas as pd
>>> from pyeyesweb.low_level import Kinematics, SpectralArcLength, LogDimensionlessJerk
>>> rate = 100.0
>>> stamps = np.arange(1000) / rate
>>> position = np.stack([0.3 * np.sin(np.pi * stamps), 0.2 * np.cos(np.pi * stamps), 0.0 * stamps], axis=1)
>>> speed = Kinematics(sampling_rate=rate).run(position, timestamps=stamps)
>>> speed
Recorder(Kinematics, rows=1000, columns=['velocity'], status={'OK': 1000})
>>> arc = SpectralArcLength(window=200, hop=50, sampling_rate=rate).run(speed.velocity, timestamps=stamps)
>>> jerk = LogDimensionlessJerk.from_velocity(window=200, hop=50, sampling_rate=rate).run(speed.velocity, timestamps=stamps)
>>> arc
Recorder(SpectralArcLength, rows=1000, columns=['spectral_arc_length'], status={'OK': 17, 'WARMING_UP': 199, 'NO_OUTPUT': 784})
```

`run` returns one row per sample, whatever the feature: the rows of a windowed feature before its first window are
`WARMING_UP`, and those between two windows are `NO_OUTPUT`. All three recorders therefore have 1000 rows and the same
timestamps, which is what makes them easy to put side by side.

## One table with `to_frame()`

{py:meth}`~pyeyesweb.data_models.Recorder.to_frame` gives a DataFrame with one column per output (a vector output gets one column
per component, such as `velocity_x`), preceded by `status` (the name of the status), `reason` (the text, empty when there is none) and `timestamp` (seconds).

```{doctest}
>>> speed.to_frame(meta=False).head(3)
       velocity
0  3.469447e-16
1  3.644258e-02
2  6.123992e-02
>>> list(arc.to_frame().columns)
['status', 'reason', 'timestamp', 'spectral_arc_length']
```

To merge several recorders, give each frame the name of its feature as a prefix and join them on the row, since the rows
correspond. The `timestamp` columns are equal and one of them is enough; the `reason` columns are left out here.

```{doctest}
>>> frames = {"speed": speed, "arc": arc, "jerk": jerk}
>>> table = pd.concat([recorder.to_frame().drop(columns="reason").add_prefix(name + "_") for name, recorder in frames.items()], axis=1)
>>> table = table.drop(columns=["arc_timestamp", "jerk_timestamp"]).rename(columns={"speed_timestamp": "timestamp"})
>>> table.shape
(1000, 7)
>>> list(table.columns)
['speed_status', 'timestamp', 'speed_velocity', 'arc_status', 'arc_spectral_arc_length', 'jerk_status', 'jerk_log_dimensionless_jerk']
>>> table.loc[198:200, ["timestamp", "jerk_status", "jerk_log_dimensionless_jerk"]]
     timestamp jerk_status  jerk_log_dimensionless_jerk
198       1.98  WARMING_UP                          NaN
199       1.99          OK                   -12.541043
200       2.00   NO_OUTPUT                          NaN
```

## Status: keep the rows that hold a value

A row that is not `OK` holds NaN in every output. Do not drop NaN to find the useful rows: filter on the status, which says why a
value is missing, and filter each feature on its own status.

```{doctest}
>>> table["arc_status"].value_counts().to_dict()
{'NO_OUTPUT': 784, 'WARMING_UP': 199, 'OK': 17}
>>> measured = table[table["arc_status"] == "OK"]
>>> len(measured), measured["timestamp"].iloc[[0, -1]].tolist()
(17, [1.99, 9.99])
>>> measured[["arc_spectral_arc_length", "jerk_log_dimensionless_jerk"]].describe().loc[["count", "mean"]]
       arc_spectral_arc_length  jerk_log_dimensionless_jerk
count                17.000000                    17.000000
mean                 -2.272982                    -6.264024
```

The first value is stamped 1.99 s, the time of the last sample of the first window, and the next ones every 0.5 s (50 samples). A
status of `INVALID_INPUT` also appears here when the recording had NaN or a time that went back; its `reason` is the `reason` column of
`to_frame()` (and `rec.reasons`, `rec[row].reason`) when you need to know why.

## Features on different time grids

Features that run on streams with different rates give recorders of different lengths. Join them on the timestamp, not on the row,
with `pandas.merge_asof`, which takes for each row of the left table the latest row of the right table that is not later.

```{doctest}
>>> slow = Kinematics(sampling_rate=25.0).run(position[::4], timestamps=stamps[::4])
>>> fast, slow = speed.to_frame(), slow.to_frame().add_prefix("slow_")
>>> merged = pd.merge_asof(fast, slow, left_on="timestamp", right_on="slow_timestamp")
>>> len(fast), len(slow), len(merged)
(1000, 250, 1000)
>>> merged.loc[[0, 3, 4, 7], ["timestamp", "slow_timestamp"]]
   timestamp  slow_timestamp
0       0.00            0.00
3       0.03            0.00
4       0.04            0.04
7       0.07            0.04
```

## One row per recording

For a study the table is usually one row per recording: a summary of each feature over the rows that are `OK`. A function that
turns a recorder into a number keeps the rule in one place.

```{doctest}
>>> def summarise(position, stamps):
...     speed = Kinematics(sampling_rate=rate).run(position, timestamps=stamps)
...     arc = SpectralArcLength(window=200, hop=50, sampling_rate=rate).run(speed.velocity, timestamps=stamps)
...     return {"mean_speed": speed.velocity[speed.ok].mean(), "arc": arc.spectral_arc_length[arc.ok].mean()}
>>> recordings = {"smooth": position, "jerky": position + 0.01 * np.sign(np.sin(2 * np.pi * 3 * stamps))[:, None] * [1, 0, 0]}
>>> summary = pd.DataFrame({name: summarise(data, stamps) for name, data in recordings.items()}).T
>>> summary.round(3)
        mean_speed    arc
smooth       0.787 -2.273
jerky        0.798 -2.981
```

## Saving and reading back

A DataFrame is saved with the usual pandas writers. A CSV file keeps the status names and writes NaN as an empty field:

```{doctest}
>>> import tempfile, pathlib
>>> with tempfile.TemporaryDirectory() as folder:
...     path = pathlib.Path(folder) / "recording.csv"
...     table.to_csv(path, index=False)
...     again = pd.read_csv(path)
>>> again.shape == table.shape, bool(again["arc_status"].equals(table["arc_status"]))
(True, True)
```

For a numeric array without pandas, `rec.to_numpy()` returns the fixed outputs as one float matrix (columns in the order of the
flat names) that `numpy.save` or `numpy.savetxt` writes; the status and the timestamps are `rec.status` and `rec.timestamps`.
Image outputs and outputs whose labels are known only at run time are not in `to_frame()` or `to_numpy()`; read them from
`rec["name"]`, a list with one entry per row.

## Notes

- `run` starts from a fresh state for every call (`reset=True`), so features can be reused for several recordings; use
  `reset=False` to continue a long recording in chunks.
- Give `timestamps` whenever the recording has them (see {doc}`realtime_live_parameters`); without them the feature uses
  `sampling_rate`, and the `timestamp` column is NaN.
- A recording of `T` samples gives `T` rows per feature, so a table of many features is `T` rows wide in memory:
  summarise per recording as above when there are many recordings.
