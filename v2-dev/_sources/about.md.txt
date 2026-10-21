# About

PyEyesWeb is developed by [InfoMus Lab &ndash; Casa Paganini](http://www.casapaganini.org/index_eng.php), University of
Genoa. It brings to Python the EyesWeb Expressive Gesture Analysis library, which the lab has developed since 1997 and which
has been used in research, education and industry, and the conceptual framework of movement qualities described in
{doc}`theory/framework`.

```{container} pew-credits pew-credits-page

<a href="http://www.casapaganini.org/index_eng.php"><img class="pew-logo pew-logo-wide" src="_static/cp-logo.png" alt="InfoMus Lab - Casa Paganini, University of Genoa"></a>
```

## Funding

PyEyesWeb is developed with the partial support of the EU ICT S+T+ARTS project [Resilence](https://resilence.eu/), funded by
the European Union's Horizon programme.

```{container} pew-credits pew-credits-page

<a href="https://resilence.eu/"><img class="pew-logo" src="_static/resilence-logo.png" alt="Resilence project, EU ICT S+T+ARTS"></a>
<img class="pew-logo" src="_static/eu-logo.png" alt="Funded by the European Union">
```

(citing-pyeyesweb)=
## Citing PyEyesWeb

If you use PyEyesWeb in your research, please cite (from `CITATION.cff` in the repository):

> S. R. Sabharwal, N. Corbellini, S. Ghisio, P. Coletta, G. Romano, A. A. Foysal, G. Volpe and A. Camurri.
> PyEyesWeb: An open source toolkit for multimodal movement feature extraction. In *MOCO '26: Proceedings of the 10th
> International Conference on Movement and Computing*, ACM, 2026. [doi:10.1145/3802842.3802904](https://doi.org/10.1145/3802842.3802904)

```bibtex
@inproceedings{sabharwal2026pyeyesweb,
  author    = {Sabharwal, Sanket Rajeev and Corbellini, Nicola and Ghisio, Simone and Coletta, Paolo and
               Romano, Gabriele and Foysal, Abdullah Al and Volpe, Gualtiero and Camurri, Antonio},
  title     = {PyEyesWeb: An open source toolkit for multimodal movement feature extraction},
  booktitle = {MOCO '26: Proceedings of the 10th International Conference on Movement and Computing},
  publisher = {ACM},
  year      = {2026},
  doi       = {10.1145/3802842.3802904}
}
```

## Licence

The Python package and the example data are released under the MIT licence (`LICENSE.txt` in the repository). The compiled
core `eyesweb-core`, which the package installs, is distributed as a binary under its own licence, shipped with the wheel; it
requires that InfoMus Lab &ndash; Casa Paganini, University of Genoa is credited and the reference above cited.
