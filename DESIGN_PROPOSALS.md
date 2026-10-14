# PyEyesWeb design proposals: unified review

Fifteen design notes (`CLASSMETHOD_INPUT_MODE`, `CLUSTERABILITY`, `CURVATURE_ORGANIZATION`, `CURVATURE_SMOOTHNESS`,
`DIRECTION_CHANGE`, `EQUILIBRIUM`, `EVENT_SYNCHRONIZATION`, `GESTURE_SEGMENTER`, `IMPULSIVITY`, `KINETIC_ENERGY_BONES`,
`LIGHTNESS`, `MULTISCALE_ENTROPY`, `PHASE_LOCKING_VALUE`, `SAMPLE_ENTROPY`, `TRIANGLE_SYMMETRY`) merged into one place,
each with a review. Every review was checked against the current code (2026-10-11); where a note's claim is
outdated or wrong, the review says so.

## 1. Principles the reviews apply

These come from decisions already taken (smoothness redesign, `DEVELOPMENT_SPEC.md`). Several notes contradict them;
where they do, the review sides with the principle unless the note gives a reason to change it.

1. **Atomic features.** One class computes one quantity from the signal it is defined on. The user composes
   (`Kinematics` -> `SpectralArcLength`). No manager classes, no `mode="auto"` dispatch on input shape.
2. **No hidden preprocessing.** Differentiation, filtering and projection are the user's explicit choice; a feature
   does not silently filter (the speed metrics lost `use_filter` for this reason).
3. **`from_*` constructors only when the input kind differs for the same quantity** (positions vs velocities).
   `method=` only when the algorithm differs on the same input. Two different quantities with different inputs are
   two classes, not one class with `method=`.
4. **Explicit inputs.** A feature declares exactly what it takes; nothing is silently truncated, averaged or
   projected. Plane and axis choices are made by the caller.
5. **Algorithmic fidelity, free architecture.** Fidelity is about the maths: for the same input and parameters a
   feature gives the EyesWeb numbers. How the core is cut into blocks, what each block takes as input and how Python
   exposes it can be redesigned during development, in C++ and Python alike. A redesign that splits or reshapes a
   block keeps fidelity when a parity test proves that the new composition reproduces the original block exactly
   (bit for bit, as for `CurvatureSmoothness` and the speed metrics). Only a change of the maths itself needs a
   maintainer decision and a line under "Corrected in the core" in `PORTING_STATUS.md`.
6. **No deprecation aliases.** Version 2.0.0 is unreleased: renames are clean. Several notes propose aliases;
   they are not needed.

## 2. Summary

| # | Note | Proposal in one line | Review | Changes numbers? |
|---|---|---|---|---|
| 1 | Classmethod input mode | `from_*` for input modalities, `method=` for algorithms; `signal` -> `input_mode` | Agree, with a narrower scope | No |
| 2 | Curvature organisation | `Curvature` -> `ContourCurvature`; `AverageCurvature` -> `TrajectoryNonPlanarity`; add `TrajectoryCurvature` | Agree on both renames; skip the new class | No |
| 3 | Curvature smoothness | Rename, unify inputs, or merge into `PathSmoothness(method=)` | Rename (option A); fix the input pain in `Kinematics` instead | No |
| 4 | Direction change | Drop `dims`; take `(D,)` points; average markers on ingest | Agree | No |
| 5 | Equilibrium | Take three 2D points; drop `axes` and indices | Agree; skip `from_skeleton` | No |
| 6 | Event synchronization | One `EventSynchronization` facade over six classes | Disagree with the merge; agree with the clean-up | Partly |
| 7 | Gesture segmenter | Take a 1D energy instead of a skeleton | Agree: split the core block into three atomic blocks | No, if the composition is proven equal |
| 8 | Impulsivity | Merge the two impulsivity classes under `method=`; expose `motion_threshold` | Disagree with the merge; agree with the rest | No |
| 9 | Kinetic energy bones | Drop the bones algorithm | Agree, option B (core too) | No |
| 10 | Lightness | Redesign from scratch | Agree it is broken; put it on the drop list until redesigned | Yes |
| 11 | Multi-scale entropy | Split into `MultiScaleEntropy` + `EnsembleDominance` | Agree | No |
| 12 | Phase locking value | Two explicit inputs; default band-pass | Agree on inputs; disagree on a default filter | No |
| 13 | Sample entropy | Default tolerance relative to the window's standard deviation | Agree | Yes |
| 14 | Triangle symmetry | 3D, invert to `symmetry`, apex auto-detection | Agree on the inversion; disagree on 3D plane and apex detection | Partly |
| 15 | Clusterability | Default `n_neighbors`, deterministic sampling, trajectory-aware variants | Agree on the first two; drop-list candidate otherwise | Yes |

## 3. Reviews

### 3.1 Classmethod constructors for input modes (`CLASSMETHOD_INPUT_MODE.md`)

**Proposal.** `KineticEnergy.from_position/from_velocity`, `Kinematics.from_point/from_series/from_trajectory`,
`LogDimensionlessJerk.from_velocity/from_acceleration`; rename `signal` to `input_mode`; `__init__` keeps
`input_mode` so the catalog and generic construction keep working. `Symmetry` and `Rarity` keep `method=`.

**Review.** Agree. The rule matches principle 3, and keeping `input_mode` in `__init__` is right (the contract and
signature tests build features generically). Two remarks:

- `Kinematics.from_trajectory` depends on the Trajectory datatype, a drop candidate. Decide that first.
- The same rule must not be used for convenience compositions (`Equilibrium.from_skeleton`,
  `GestureSegmenter.from_skeleton`, `Impulsivity.from_contraction`): those are not input modes of one quantity.
- Our signature machinery and the signature tests cover constructors only; they must also cover the `from_*`
  methods so their parameters show and typos are caught.

**Decision needed:** approve the rule and the rename `signal` -> `input_mode`.

### 3.2 Curvature names (`CURVATURE_ORGANIZATION_DESIGN.md`)

**Proposal.** Rename `Curvature` (2D contour) to `ContourCurvature`; move and rename `AverageCurvature` to
`TrajectoryNonPlanarity`; add a `TrajectoryCurvature` feature or a `Kinematics.curvature()` constructor.

**Review.** Agree with both renames. Verified: `AverageCurvature` measures the mean distance from local best-fit
planes (points on a circle give 0), so the name is misleading.

- No alias for the old names (principle 6).
- `AverageCurvature` needs the Trajectory datatype; if that is dropped, this feature goes or is rewritten on arrays.
- Skip `TrajectoryCurvature`: `Kinematics(output_type="curvature")` is exactly that quantity. A second class would
  duplicate it. Documentation is the fix.

**Decision needed:** approve `ContourCurvature` and `TrajectoryNonPlanarity` (or `OutOfPlaneDeviation`).

### 3.3 Curvature smoothness (`CURVATURE_SMOOTHNESS_DESIGN.md`)

**Proposal.** Option A rename, option B let `CurvatureSmoothness` take positions, option C merge both into
`PathSmoothness(method=)`.

**Review.** Option A. Option C contradicts the atomic design approved this week (two quantities, two classes), and
the two measures also differ in execution (windowed vs per frame) and range, so one class would carry two
contracts. The real pain behind option B is that `CurvatureSmoothness` needs two `Kinematics` instances (one for
velocity, one for acceleration). Fix that at the source: let `Kinematics` return several outputs at once
(`output_type=["velocity", "acceleration"]`, with `output_dims="components"`), so one instance feeds the feature.
In the core this is cheap: one Savitzky-Golay pass already yields every coefficient, so the block can return all
the requested derivatives from the same filters with no change of maths.

Naming: `CurvatureVelocitySmoothness` is the correlation of curvature and velocity; it is related to the
two-thirds power law but only in Pearson mode (the simplified mode is not a correlation). A neutral, accurate pair:
`CurvatureVelocityCorrelation` and `CurvatureDispersion`.

**Decision needed:** the two names; whether `Kinematics` gets multi-output.

### 3.4 Direction change (`DIRECTION_CHANGE_DESIGN.md`)

**Proposal.** Accept `(D,)` points and `(T, D)` recordings; average `(signals, D)` frames on ingest; remove `dims`.

**Review.** Agree. Averaging on ingest is equivalent to what the core does today (the mean over signals per frame
commutes with the windowing), so the numbers do not change; prove it with a parity test. The `dims` error on a
direct window call disappears with it. This also fixes the dummy-axis hack in the examples.

In the core, the block can take a `(frames, D)` trajectory and lose its signals axis; the reduction over markers
moves to the caller or the wrapper with identical numbers (principle 5).

One caution: averaging several markers is still a hidden reduction (principle 4). A stricter contract would take
`(D,)` only and leave the averaging to the user. Either is defensible; averaging on ingest keeps the EyesWeb
behaviour.

**Decision needed:** strict `(D,)` only, or accept `(signals, D)` with averaging.

### 3.5 Equilibrium (`EQUILIBRIUM_DESIGN.md`)

**Proposal.** `process(left_foot, right_foot, barycenter)` with three 2D points; drop `axes`, the axis and index
parameters; optional `Equilibrium.from_skeleton(up_axis=...)`.

**Review.** Agree with the three-point contract: it removes a silent trap (the default floor plane `axes=(0, 1)` is
wrong for Y-up data such as Qualisys) and the dummy-row workaround for the barycenter. It matches `TriangleSymmetry`.
Skip `from_skeleton` (principle 3: it is a composition, not an input mode). Rename `margin_mm` to `margin`: with
`units=` the parameter is in metres or millimetres, so the `_mm` suffix is now wrong.

**Decision needed:** approve; confirm `margin`.

### 3.6 Event synchronization (`EVENT_SYNCHRONIZATION_DESIGN.md`)

**Proposal.** One `EventSynchronization` with `tau=int|"adaptive"|"estimated"`, `kernel=`, `mode="auto"`, replacing
`EventSynchronization`, both MECS versions, `SpikeSynchronization` and `TauEstimator`; rename
`EventSynchronizationRealTime` to `EventSyncCounter`.

**Review.** Disagree with the merge, agree with the clean-up around it.

- The merged class would hide four algorithms with different inputs and outputs behind one name, and `mode="auto"`
  picks the algorithm from the input shape: a silent switch of meaning, the opposite of principles 1 and 4.
- `kernel=` does not reproduce MECS v1: v1 uses a discrete triangular weighting and different normalisation than v2
  with a linear kernel, so v1 numbers would change.
- Three of these classes are already drop candidates (MECS v1, `EventSynchronizationRealTime`, `TauEstimator`).
  Deciding the drop list first shrinks the family to three classes (pairwise `EventSynchronization`, MECS,
  `SpikeSynchronization`), which is not fragmentation.
- `TauEstimator` as `tau="estimated"` is a nice idea if `TauEstimator` stays; it can be a helper function instead.
- With a free core architecture, what the remaining blocks share (the coincidence search and the kernels) can become
  shared free functions in C++, removing duplicated code without merging the public classes. Merging is then a
  question of meaning, not of code reuse, and on meaning they are different measures.

**Decision needed:** the drop-list items first; then whether `EventSynchronizationRealTime` survives as `EventSyncCounter`.

### 3.7 Gesture segmenter (`GESTURE_SEGMENTER_DESIGN.md`)

**Proposal.** Take a 1D energy (or speed) per call instead of a skeleton; `KineticEnergy` feeds it.

**Review.** Agree: it removes the duplicated kinetic-energy code and makes the segmenter usable on any intensity
signal. One fact the note misses: the segmenter's noise test (`IsUserMotionRandomic2`) is not computed from the energy
but from the per-joint speed variances (verified in `gesture_segmenter.h`), so a 1D energy alone cannot reproduce it.

Since the core can be redesigned (principle 5), the clean answer is to split the EyesWeb block into three atomic core
blocks with unchanged maths:

1. `KineticEnergy`: already exists; the segmenter's internal energy must be checked to be the same formula.
2. A motion-noise detector: per-joint speed variances over 10 samples, giving the noise flag (needs the joints).
3. The segmenter itself: Savitzky-Golay smoothing of a 1D intensity plus the threshold state machine, taking the
   intensity and the noise flag (the flag optional, so any 1D signal can be segmented).

A parity test proves that `KineticEnergy` + noise detector + segmenter reproduces today's `GestureSegmenter` bit for
bit, including the reset quirks; then no number changes and the faithful behaviour is a composition.

**Decision needed:** approve the split; the name of the noise detector.

### 3.8 Impulsivity (`IMPULSIVITY_DESIGN.md`)

**Proposal.** Merge `Impulsivity` (EyesWeb, contraction index and quantity of motion) and `SuddennessImpulsivity`
(trajectory) into `Impulsivity(method=)`; expose the hard-coded `motion_threshold`; strip intermediate outputs; make
direction change and suddenness use the same trajectory.

**Review.**

- Merge: disagree. Different inputs and different quantities make two classes (principles 1 and 3). Rename instead:
  `ContractionImpulsivity` and `SuddennessImpulsivity`.
- `motion_threshold`: agree. Verified: `kMotionThreshold = 0.01` is hard coded in `impulsivity_index.cpp`. Exposing it
  with the same default changes no number.
- Intermediate outputs (`direction_change_val`, `is_sudden`): agree to remove; users who need them run
  `DirectionChange` and `Suddenness`.
- Core: `SuddennessImpulsivity` is a combined C++ block today. It can become a composition of the `DirectionChange`
  and `Suddenness` blocks (it is their product), with no maths of its own and a parity test for the faithful case.
- Input asymmetry: agree, and it is a real finding. Verified: direction change uses the mean of all signals while
  suddenness uses the first signal only. Making both use the same trajectory changes numbers for multi-marker input;
  with the `DirectionChange` redesign (3.4) both would take one `(D,)` point.

**Decision needed:** the names; approve the asymmetry fix as a deliberate change.

### 3.9 Kinetic energy bones (`KINETIC_ENERGY_BONES_NOTE.md`)

**Proposal.** Drop `algorithm="bones"`; option A keeps it in the core, option B removes it everywhere.

**Review.** Option B. It is consistent with the removal of the legacy device presets and `SkeletonManipulator`: dead
code in the core is still code to maintain. Point mode is unchanged. Verified: the class docstring still advertises
"points or bones".

**Decision needed:** approve option B.

### 3.10 Lightness (`LIGHTNESS_DESIGN.md`)

**Proposal.** Full redesign: physical definition, configurable vertical axis, output in [0, 1], validation against
annotated data.

**Review.** Agree that the current formula is broken: rarity of the horizontal share measures surprise, not
lightness, and the examples confirmed the inversion (light > heavy in one of eight pairs). A redesign is research,
not engineering: it needs a definition from the literature and annotated data before code. Until then, put
`Lightness` on the drop-candidates list (or mark it experimental) rather than ship a misleading quality. The axis
point is consistent with principle 4: take the vertical component from the caller, not a hard-coded index.

**Decision needed:** drop list now, redesign later?

### 3.11 Multi-scale entropy (`MULTISCALE_ENTROPY_DESIGN.md`)

**Proposal.** Three tiers: `SampleEntropy`, a new `MultiScaleEntropy` (curve and complexity index), and
`EnsembleDominance` (multi-person).

**Review.** Agree; it is the atomic principle applied to the right place. `CoarseGraining` already exists, so
`MultiScaleEntropy` is coarse graining plus sample entropy per scale plus integration. Two things to settle:

- One tolerance rule for both entropies (the note uses 0.15 sigma here and 0.2 sigma in 3.13).
- `MultiScaleEntropyDominance` is a lab feature with a Python reference; the split must reproduce its numbers.
  In the core it becomes three blocks (multi-scale entropy reusing coarse graining and sample entropy, then
  dominance on the complexity indices), proven equal to today's combined block.

**Decision needed:** approve; pick the tolerance rule.

### 3.12 Phase locking value (`PHASE_LOCKING_VALUE_DESIGN.md`)

**Proposal.** Two explicit inputs (`signal1`, `signal2`) instead of a list truncated to two; a default band-pass;
guidance for 3D data.

**Review.**

- Inputs: agree with approach B. Verified: `_call_block` passes `args[0][:2]`, silently dropping channels. Two
  declared SAMPLE inputs, as in `NoPreparationDetector2`, give the shape check at the first frame for free.
- Default band-pass: disagree. It is hidden preprocessing (principle 2), the same reason `use_filter` was removed from
  the speed metrics. Document the narrow-band requirement in the docstring and examples instead; the user filters.
- Guidance: agree. Note the note's example `Kinematics(output_type="speed")` does not exist; the speed is
  `output_type="velocity"` with the default tangential output.
- The clapping result is an analysis mistake (vertical axis of a horizontal movement), not a feature bug: worth a
  line in the examples.

**Decision needed:** approve inputs; confirm no default filter.

### 3.13 Sample entropy (`SAMPLE_ENTROPY_DESIGN.md`)

**Proposal.** `tolerance=None` by default, meaning `relative_tolerance * std(window)` with `relative_tolerance=0.2`.

**Review.** Agree; it is standard practice and fixes the `inf` outputs on real data. It changes the default numbers
(EyesWeb's default is an absolute 0.3), so it is a fidelity decision. An explicit `tolerance=0.3` keeps the faithful
behaviour. Note: the standard uses the standard deviation of the whole signal; per window is the streaming equivalent
and should be stated.

**Decision needed:** approve the new default.

### 3.14 Triangle symmetry (`TRIANGLE_SYMMETRY_DESIGN.md`)

**Proposal.** Accept 3D points (intrinsic triangle plane or a chosen plane); output `symmetry = 1 - asymmetry`;
make the result independent of vertex order by taking the best apex.

**Review.**

- Inversion to `symmetry`: agree (consistent with `Symmetry`); a renamed output, not a numeric change.
- 3D: disagree with the intrinsic plane. The original is not a pure shape measure: it compares the base vertices to
  the vertical line through the apex (verified: coordinates are taken relative to the apex x). That makes it a
  posture measure (tilt of head over shoulders). In the triangle's own plane that reference disappears and the feature
  becomes "how isosceles is the triangle", a different quantity. Projection onto a plane chosen by the caller keeps the
  meaning; per principle 4, the caller slices the coordinates, as for `Equilibrium`.
- Apex auto-detection: disagree for the same reason. The apex is anatomical (head over shoulders), not the most
  symmetric choice; the max over three apexes would report symmetric postures that are not. Keep the apex as the first
  input and say so in the docstring.

**Decision needed:** approve the inversion; confirm 2D input with caller projection.

### 3.15 Clusterability (`CLUSTERABILITY_DESIGN.md`)

**Proposal.** Default `n_neighbors=2`; deterministic quasi-random sampling; trajectory-aware variants (arc-length
decimation, landmarks); documentation.

**Review.**

- Default `n_neighbors=2`: agree (verified: it is a required argument today).
- Determinism: partly done. A `seed` parameter exists and the seed is reused on reset. A low-discrepancy sequence
  (Halton) removes the randomness completely and changes numbers slightly; reasonable.
- The core finding (continuous trajectories always give H above 0.9) means the Hopkins statistic answers a question
  movement data rarely asks. Arc-length decimation and landmark extraction are preprocessing the user can do before
  calling it (principle 2). Rather than building variants, put `Clusterability` on the drop-candidates list or keep
  it as a generic primitive documented for point sets, not trajectories.

**Decision needed:** keep as a generic primitive, or drop list.

## 4. Suggested order of work

1. Decide the drop list items that these proposals touch (Trajectory datatype, the event-synchronization blocks,
   `Lightness`, `Clusterability`): every removal shrinks the work below.
2. API and core-architecture clean-ups that change no numbers, each with a parity test against the current
   blocks: 3.1, 3.2, 3.3 (names and multi-output `Kinematics`), 3.4, 3.5, 3.7 (split of the segmenter), 3.8 (names,
   `motion_threshold`, outputs, composition), 3.9, 3.11, 3.12 (inputs), 3.14 (inversion), 3.15 (default).
3. Decisions that change the maths, each recorded in `PORTING_STATUS.md`: 3.8 (asymmetry), 3.13, 3.15 (Halton).
4. Research: 3.10.
