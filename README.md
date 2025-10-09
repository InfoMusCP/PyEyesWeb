# PyEyesWeb  
## Expressive movement analysis toolkit
*A modern, modular, and accessible Python library for expressive movement analysis — bridging research, health, and the arts*  

[![PyPI version](https://img.shields.io/pypi/v/pyeyesweb.svg)](https://pypi.org/project/pyeyesweb/)
[![Docs](https://img.shields.io/badge/docs-latest-blue.svg)](https://infomuscp.github.io/PyEyesWeb/)
[![License](https://img.shields.io/github/license/USERNAME/PyEyesWeb.svg)](.github/LICENSE) 

`PyEyesWeb` is a research toolkit for extracting quantitative features from human movement data.  
It builds on the **Expressive Gesture Analysis** library of [EyesWeb](https://casapaganini.unige.it/eyesweb_bp), bringing expressive movement analysis into Python as a core aim of the project.
The library provides computational methods to analyze different qualities of movement, supporting applications in **research, health, and the arts**.  
It is designed to facilitate adoption in **artificial intelligence and machine learning pipelines**, while also enabling seamless integration with creative and interactive platforms such as **TouchDesigner, Unity, and Max/MSP**.  

## Installation

```bash
pip install pyeyesweb
```

## Usage
A minimal example of extracting movement features with `PyEyesWeb`
:
```python
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import Smoothness

# Movement smoothness analysis
smoothness = Smoothness(rate_hz=50.0)
window = SlidingWindow(max_length=100, n_columns=1)
window.append([motion_data]) 
# here `motion_data` is a float representing a single sample of motion data
# (e.g., the x coordinate of the left hand at time t).

sparc, jerk = smoothness(window)
```
> [!TIP]
> For more advanced and complete use cases see the [Documentation](https://infomuscp.github.io/PyEyesWeb/)
> and the [examples](examples) folder.

## Documentation

Documentation for `PyEyesWeb` is available online and includes tutorials, API references, and the theoretical and scientific background of the implemented metrics:

- [Getting Started](https://infomuscp.github.io/PyEyesWeb/getting_started): step-by-step guide to installation and basic usage.
- [API Reference](https://infomuscp.github.io/PyEyesWeb/api_reference): technical descriptions of modules, classes, and functions.  
- [Theoretical Foundation](https://infomuscp.github.io/PyEyesWeb/user_guide): background on the scientific principles and research behind the metrics. 

## Support

If you encounter issues or have questions about `PyEyesWeb`, you can get help through the following channels:

- **GitHub Issues:** report bugs, request features, or ask technical questions on the [PyEyesWeb GitHub Issues page](https://github.com/infomuscp/PyEyesWeb/issues).  
- **Discussions / Q&A:** participate in conversations or seek advice in [GitHub Discussions](https://github.com/infomuscp/PyEyesWeb/discussions).  
- **Email:** Reach out to the maintainers at `cp.infomus@gmail.com` for direct support or collaboration inquiries.  

Please provide clear descriptions, minimal reproducible examples, and version information when submitting issues—it helps us respond faster.

## Roadmap

`PyEyesWeb` is under active development, and several features are planned for upcoming releases:  

- **Expanded feature extraction:** addition of more movement expressivity metrics (you can find an example of which features to expect in related [conceptual layer guide]().  
- **Improved examples and tutorials:** more interactive Jupyter notebooks and example datasets to facilitate learning and adoption.  
- **Cross-platform compatibility:** streamlined integration with creative and interactive platforms (e.g., [TouchDesigner plugin](https://github.com/InfoMusCP/PyEyesWebTD), Unity, Max/MSP).  

Future development priorities may evolve based on user feedback and research needs.
Users are encouraged to suggest features or improvements via [GitHub Issues](https://github.com/infomuscp/PyEyesWeb/issues).

## Contributing

Contributions to `PyEyesWeb` are welcome! Whether it's reporting bugs, adding features, improving documentation, or providing examples, your help is appreciated.  

### How to Contribute
1. **Fork the repository**.

2. **Clone the forked repository** set up the development environment
    ```bash
    git clone https://github.com/<YOUR_USERNAME>/PyEyesWeb.git
    cd pyeyesweb
    pip install -e .[dev]
    ```
2. Create a branch for your feature or bug fix:  
   ```bash
   git checkout -b feature/your-feature-name
    ```
3. Make your changes, ensuring code quality and adherence to the project's coding standards.
4. Submit a pull request to the `main` branch, with a clear description of your changes.
5. Engage in code reviews and address any feedback provided by maintainers.

## Authors & Acknowledgments

`PyEyesWeb` is developed by [**InfoMus Lab – Casa Paganini**](http://www.casapaganini.org/index_eng.php), University of Genoa, with the partial support of the **[EU ICT STARTS Resilence Project](https://www.resilence.eu/)**.  
  

<div align="center">
<img src="docs/assets/cp-logo.png" alt="InfoMus Lab Logo" width="512" style="margin:15px"/>
</div>
<div align="center">
<img src="docs/assets/resilence-logo.png" alt="Resilence Project Logo" width="200" style="margin:15px"/>
<img src="docs/assets/eu-logo.png" alt="EU Logo" width="100" style="margin:15px"/>
</div>

### Maintainers & Contributors  
<a href="https://github.com/InfoMusCP/PyEyesWeb/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=InfoMusCP/PyEyesWeb" />
</a>

## License

MIT License
