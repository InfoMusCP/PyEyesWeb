---
html_theme.sidebar_secondary.remove: true
---

# PyEyesWeb

```{container} pew-hero

<p class="pew-hero-tagline">A research toolkit for the analysis of expressive movement</p>

<p class="pew-hero-lead">PyEyesWeb measures how people move: from the kinematics of a joint to the qualities of a gesture and
the coordination of a group. It is built on the EyesWeb Expressive Gesture Analysis library of InfoMus Lab &ndash;
Casa Paganini, University of Genoa.</p>

<p class="pew-hero-install"><code>pip install pyeyesweb</code></p>
```

::::{grid} 1 2 2 4
:gutter: 3
:class-container: pew-sections

:::{grid-item-card} {fas}`book-open` User guide
:link: user_guide/index
:link-type: doc

Installation, a first feature, the concepts of the library and how to choose a feature for a question.
:::

:::{grid-item-card} {fas}`shapes` Theory
:link: theory/index
:link-type: doc

The conceptual framework of movement qualities, the notation and the definition of every measure, with references.
:::

:::{grid-item-card} {fas}`chalkboard-user` Tutorials
:link: tutorials/index
:link-type: doc

Executed tutorials on recorded movement, from the first feature to a real-time loop, each a downloadable notebook.
:::

:::{grid-item-card} {fas}`code` API reference
:link: api/overview
:link-type: doc

One page per feature, generated from the code: parameters, inputs, outputs with their units.
:::
::::

```{container} pew-credits

<p class="pew-credits-title">Developed by</p>
<a href="http://www.casapaganini.org/index_eng.php"><img class="pew-logo pew-logo-wide" src="_static/cp-logo.png" alt="InfoMus Lab - Casa Paganini, University of Genoa"></a>
<p class="pew-credits-title">With the partial support of</p>
<a href="https://resilence.eu/"><img class="pew-logo" src="_static/resilence-logo.png" alt="Resilence project, EU ICT S+T+ARTS"></a>
<img class="pew-logo" src="_static/eu-logo.png" alt="Funded by the European Union">
<p class="pew-credits-text">PyEyesWeb is developed by InfoMus Lab &ndash; Casa Paganini, University of Genoa, as partner of
the EU ICT S+T+ARTS project Resilence, funded by the European Union's Horizon programme. If you use it in your research,
please <a href="about.html#citing-pyeyesweb">cite it</a>.</p>
```

```{toctree}
:hidden:

user_guide/index
theory/index
tutorials/index
api/overview
developer/index
release_notes
about
```
