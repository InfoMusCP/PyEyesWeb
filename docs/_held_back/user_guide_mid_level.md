<!-- Sections cut from docs/user_guide/mid_level.md for the early release (2026-11-13). -->

**How sudden or impulsive is it?** {py:class}`~pyeyesweb.mid_level.Suddenness` fits a stable distribution to the speeds
of a trajectory and tells how heavy the tail of the distribution is, that is how often the movement has abrupt speed changes.
{py:class}`~pyeyesweb.mid_level.SuddennessImpulsivity` gives the direction change of the trajectory when it is also sudden, and
{py:class}`~pyeyesweb.mid_level.ContractionImpulsivity` the change per second of the contraction index over a short, energetic
gesture. Theory: {doc}`../theory/impulsivity_suddenness`. The quality of impulsivity is defined in {cite}`mazzarino2009need`.

**How is the space occupied?** {py:class}`~pyeyesweb.mid_level.PositionDependingPotentials` and
{py:class}`~pyeyesweb.mid_level.RegionDependingPotentials` turn the grid cells hit by a point
({py:class}`~pyeyesweb.physical_signals.HitCellDetector`, layer 1) into potentials with a memory of past hits: a cell that is
visited often keeps a high potential and the potential decays where nobody goes. Theory: {doc}`../theory/shape_symmetry_balance`.

