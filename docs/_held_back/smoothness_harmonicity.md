<!-- Sections cut from docs/theory/smoothness.md for the early release (2026-11-13). -->

### Harmonicity

A smooth ballistic movement has one peak of speed, and a repeated movement alternates peaks and valleys.
{py:class}`~pyeyesweb.low_level.Harmonicity` compares the number of peaks of the speed in the window with the number of sign
changes of its gradient, the turning points of the speed. It is 1 when peaks and valleys alternate regularly, as in a single
bell-shaped profile or in a regular oscillation, and lower when the speed has turning points that do not belong to that
pattern; a maximum at the border of the window is not counted as a peak. The measure is dimensionless and lies in $[0, 1]$.
Unlike SPARC and LDLJ it does not compare the movement with a reference shape: it says whether the peaks and the valleys
are regular.

