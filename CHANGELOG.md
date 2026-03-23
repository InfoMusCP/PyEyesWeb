# CHANGELOG


## v0.1.0 (2026-03-23)

### Bug Fixes

* fix: Correct parameter name from 'methods' to 'metrics' in StatisticalMoment initialization ([`7ab1722`](https://github.com/InfoMusCP/PyEyesWeb/commit/7ab172286f23074459ed4d865dcf57c9d95700ff))

### Features

* feat: Add new analytical primitives for synchronization, kinetic energy, rarity, and statistical moments. ([`8adbdf1`](https://github.com/InfoMusCP/PyEyesWeb/commit/8adbdf180be372274ba0d830b1aac1f135faeb35))

* feat: add @property to set Smoothness parameters ([`575a9cb`](https://github.com/InfoMusCP/PyEyesWeb/commit/575a9cb0c6ecf7250602159f3e0695ed5abbba17))

* feat: add Equilibrium class with elliptical balance evaluation and interactive demo

- Implemented `Equilibrium` class to evaluate balance using an ellipse aligned
  with the feet line, supporting margin and Y-axis weighting.
- Added full NumPy-style docstrings with detailed type annotations.
- Created interactive matplotlib demo (`demo_equilibrium.py`) to visualize
  equilibrium in real-time by moving the mouse cursor.
- The demo shows:
  - Feet positions as reference points.
  - Dynamic ellipse ROI, rotated according to foot alignment.
  - Barycenter position updated interactively.
  - Equilibrium value displayed and ellipse colored (green inside, red outside). ([`a14d04e`](https://github.com/InfoMusCP/PyEyesWeb/commit/a14d04ebdabcef99dd8b902b9cb40ffc6374d136))

* feat(smoothness): added the functionality for computing smoothness and also a test example ([`5d9b294`](https://github.com/InfoMusCP/PyEyesWeb/commit/5d9b294c890af82af55608ba7bc0d81cc9361952))

* feat(sync): add synchronization module and live demo using MediaPipe ([`a1f55f3`](https://github.com/InfoMusCP/PyEyesWeb/commit/a1f55f34f49facbc4e9659d18bfcf7dd5aa73d66))

### Refactoring

* refactor: rename `BaseLowLevelFeature` to `BaseFeature`, update its usage, and standardize `compute` method parameter names. ([`b6d4d00`](https://github.com/InfoMusCP/PyEyesWeb/commit/b6d4d00d0420fbda5434f89c2f660a7349394d13))

* refactor: Remove old test and benchmark data, introduce new benchmark scripts and results, and update module imports and examples. ([`b6f0c96`](https://github.com/InfoMusCP/PyEyesWeb/commit/b6f0c96a315ec648fff1bebf17b10a02b52d8ac3))

* refactor: extract smoothness calculation utilities to math_utils and signal_processing modules ([`6d46548`](https://github.com/InfoMusCP/PyEyesWeb/commit/6d4654863e7d097b0efad0fb4caa7ff1c9af887c))

* refactor: extract utility functions from sync.py to reusable utils modules ([`5253406`](https://github.com/InfoMusCP/PyEyesWeb/commit/525340624f2e5435cd3b756791852b9c6cc7c454))

### Unknown

* Merge pull request #82 from InfoMusCP/dev

Dev ([`147eeeb`](https://github.com/InfoMusCP/PyEyesWeb/commit/147eeeb7412374d72b02458ef51a6df740d41cda))

* delete: md version of notebooks ([`f3d0828`](https://github.com/InfoMusCP/PyEyesWeb/commit/f3d08289a3e406ece98971bd9b090ddf958c5eb2))

* bump version ([`503a982`](https://github.com/InfoMusCP/PyEyesWeb/commit/503a9825363dbb378c7e120d0beb9c069e93e649))

* Merge branch 'examples' into dev ([`fa8a875`](https://github.com/InfoMusCP/PyEyesWeb/commit/fa8a8756d8568c7b0e716c61ff82353775ef1431))

* add: WIP examples and feat: release pipeline ([`e3d8d4a`](https://github.com/InfoMusCP/PyEyesWeb/commit/e3d8d4afb9f7d46656e293579319b701b733a959))

* add: educational md ([`5903a73`](https://github.com/InfoMusCP/PyEyesWeb/commit/5903a73fc476d426fa2926dc4d1602e767e22e62))

* Merge pull request #81 from InfoMusCP/dev

Dev ([`08ec98a`](https://github.com/InfoMusCP/PyEyesWeb/commit/08ec98aea8b1b240ff01380ad13543d2d324b010))

* Merge branch 'main' into dev ([`85b8fc6`](https://github.com/InfoMusCP/PyEyesWeb/commit/85b8fc6d5d4abf823807c16609c0d25fe9a6f12a))

* Update warning note in README.md ([`5727bf8`](https://github.com/InfoMusCP/PyEyesWeb/commit/5727bf8f6c2403598fc5b8dcc609c0020bd1789a))

* Update README with refactoring notice

Added a note about ongoing refactoring and potential API changes. ([`bb64466`](https://github.com/InfoMusCP/PyEyesWeb/commit/bb64466ed6d6a0c93bb65602512eefb37ab4740e))

* Add reference to additional smoothness research ([`21b3dc0`](https://github.com/InfoMusCP/PyEyesWeb/commit/21b3dc0b6c2781c2302b7f63fc2a697db4c25410))

* Update reference for movement smoothness analysis ([`d337051`](https://github.com/InfoMusCP/PyEyesWeb/commit/d3370515fef1c19414d77f80ebd3536ea6bad6a9))

* Add: mike for documentation versioning ([`d4e27fe`](https://github.com/InfoMusCP/PyEyesWeb/commit/d4e27fe80d9bb31e89a06c75675d3d6fe8c12357))

* add: missing references and links in conceptual documentation ([`ecabc16`](https://github.com/InfoMusCP/PyEyesWeb/commit/ecabc16131261b82e9ab97d15adcb9c9b1690947))

* improved documentation ([`56a279d`](https://github.com/InfoMusCP/PyEyesWeb/commit/56a279d4b68720c05048a99f6d97692cb255363c))

* add: python docstrings and updated markdown documentation ([`a0fd2b5`](https://github.com/InfoMusCP/PyEyesWeb/commit/a0fd2b5c67e2dac9b8c2aac1a4d3e3f4be13cb67))

* Removed absolute path ([`3c74802`](https://github.com/InfoMusCP/PyEyesWeb/commit/3c74802be2b2f66dd6fa27dbd641279b5d2709ed))

* Aligned Compute_Sparc to article Balasubramanian, S., Melendez-Calderon, A., Roby-Brami, A., & Burdet, E. (2015).  On the analysis of movement smoothness. Journal of NeuroEngineering and Rehabilitation,    12(1), 1-11.
Add parameters in compute_sparc ([`286e9bc`](https://github.com/InfoMusCP/PyEyesWeb/commit/286e9bc2286b887edac72b13109d242bf876eb8f))

* Add benchmarks for equilibrium and smootness
Add KinectLoaderV2 (Kinect Log in EyesWeb Standard) ([`71d7ff8`](https://github.com/InfoMusCP/PyEyesWeb/commit/71d7ff82f2df992906cdc2c934544085f9a1c641))

* add todo ([`e44e904`](https://github.com/InfoMusCP/PyEyesWeb/commit/e44e904b06163411833920b37e630d76e47bb21c))

* remove index ([`763744c`](https://github.com/InfoMusCP/PyEyesWeb/commit/763744c30695d1a3b9cd4caba5effd2329b1613a))

* synchronization benchmark ([`c90a2a7`](https://github.com/InfoMusCP/PyEyesWeb/commit/c90a2a788cf2dd5d293e0cd1969ee5ad69980bab))

* update benchmarks ([`23d9fdc`](https://github.com/InfoMusCP/PyEyesWeb/commit/23d9fdca0329b86a1839bf844c5522571058cab9))

* add feature benchmarks ([`997b1c6`](https://github.com/InfoMusCP/PyEyesWeb/commit/997b1c6f910a18622b91cc8baf866c4787bbc0b0))

* rarity test ([`69c5e89`](https://github.com/InfoMusCP/PyEyesWeb/commit/69c5e893c2a0bbcf62dc4e9d08482a57dbaeb7cf))

* add example notebooks ([`1ae3a55`](https://github.com/InfoMusCP/PyEyesWeb/commit/1ae3a55b5acb629e1714f7d27bb7b763a437f227))

* rarity test ([`6c3c80f`](https://github.com/InfoMusCP/PyEyesWeb/commit/6c3c80f51515a068b315f76b478f8e0dfd1ccafa))

* Merge remote-tracking branch 'origin/refactor-sliding-window' into refactor-sliding-window ([`aba5108`](https://github.com/InfoMusCP/PyEyesWeb/commit/aba510882f866f90e639cfe1d0c16744b3c30410))

* refactoring ([`8529131`](https://github.com/InfoMusCP/PyEyesWeb/commit/8529131a73cfb6a685e2277db33e4861434af54d))

* Rarity test ([`e3fae2e`](https://github.com/InfoMusCP/PyEyesWeb/commit/e3fae2e4e5e6974b64e32f83cfd429bc53ce897c))

* refactoring ([`0f05078`](https://github.com/InfoMusCP/PyEyesWeb/commit/0f05078a813b8f78d908dfff0f6b2e274c8e01e8))

* bug fix ([`d785409`](https://github.com/InfoMusCP/PyEyesWeb/commit/d78540989fdab32be8a5741d3667828f7c6a0495))

* removed a left print ([`e92d7d4`](https://github.com/InfoMusCP/PyEyesWeb/commit/e92d7d48f657d4fa8f79f2ef894d66f4c5c80418))

* bug fixed and changed deps due to removal of trapz from numpy>=2.4.0 ([`21a8066`](https://github.com/InfoMusCP/PyEyesWeb/commit/21a806634dec773c3cb1883ff1ccab5c61b99151))

* bug fix pt.2 ([`7b1fb82`](https://github.com/InfoMusCP/PyEyesWeb/commit/7b1fb82a8b2b9cf8a19a1c8d6acdff5b714c3b13))

* bug fix ([`dc82e1c`](https://github.com/InfoMusCP/PyEyesWeb/commit/dc82e1c3c77c8e42f6c483ffc4049921998b4259))

* SlidingWindow now has generic signals instead of joints
refactored other classes  to align with current design ([`1d92adf`](https://github.com/InfoMusCP/PyEyesWeb/commit/1d92adf9f3083d581527db11dc8575d36b19e579))

* Merge branch 'main' into dev-impulsivity ([`cb4b9ff`](https://github.com/InfoMusCP/PyEyesWeb/commit/cb4b9ff5d19d953fa2ee8297f2c998f44671ad1f))

* Merge pull request #75 from Foysal440/main

Add files via upload ([`5085a6e`](https://github.com/InfoMusCP/PyEyesWeb/commit/5085a6eb3c117b7026bf97e54b524551e7f83a35))

* Add files via upload ([`d66c02b`](https://github.com/InfoMusCP/PyEyesWeb/commit/d66c02b51c3b37301fdaba3ef2ef46870c715320))

* Update license badge to MIT ([`fedd375`](https://github.com/InfoMusCP/PyEyesWeb/commit/fedd37587b6483ef389a818bd9c60563a3da7431))

* Add files via upload ([`4c0d928`](https://github.com/InfoMusCP/PyEyesWeb/commit/4c0d9285159c9bc2374e4c395e9e2660c571623d))

* Update license badge in README.md ([`43549f3`](https://github.com/InfoMusCP/PyEyesWeb/commit/43549f39b3fd17dc00f56f46059182af82bef051))

* Merge pull request #76 from InfoMusCP/review_doc

fix doc ([`ab71f59`](https://github.com/InfoMusCP/PyEyesWeb/commit/ab71f594b9eb850838315645adf705db7f49a901))

* fix doc ([`95cdad3`](https://github.com/InfoMusCP/PyEyesWeb/commit/95cdad38688bec9d42e860e409dd9799dd38cbc5))

* fix missing dependency ([`aa2d89a`](https://github.com/InfoMusCP/PyEyesWeb/commit/aa2d89ac51d064b65d9ab500957f97f0f15526a8))

* fix missing dependency ([`795c747`](https://github.com/InfoMusCP/PyEyesWeb/commit/795c7473f5d061cb168f544bf3cbac9df087ac85))

* change doc theme to readthedocs ([`dd298ef`](https://github.com/InfoMusCP/PyEyesWeb/commit/dd298ef3e50dfc93cb1f02500c91725d6a9be3ce))

* fix lightness calculation to ensure sliding window length is an integer and prevent division by zero ([`32c4b3b`](https://github.com/InfoMusCP/PyEyesWeb/commit/32c4b3b3c579e471e0d6ecbcd7447369dc2948c8))

* refactor Lightness class to make sliding window length configurable ([`f44971e`](https://github.com/InfoMusCP/PyEyesWeb/commit/f44971e663152ee28d0346ff38f94f799e324b30))

* Merge pull request #74 from InfoMusCP/docs

rename index.md files to improve clarity and organization in documentation ([`ab0d43a`](https://github.com/InfoMusCP/PyEyesWeb/commit/ab0d43a8893270a5e0b334069498b4b29950710f))

* rename index.md files to improve clarity and organization in documentation ([`bb7b073`](https://github.com/InfoMusCP/PyEyesWeb/commit/bb7b073d8119ba18801a1b945aa4ac001fe712eb))

* Merge pull request #73 from Foysal440/stat

added statistical_moment ([`4d2c5bb`](https://github.com/InfoMusCP/PyEyesWeb/commit/4d2c5bba1cc658b56b9e6331ccdcc4296446a6a6))

* added stat_moment ([`3e58248`](https://github.com/InfoMusCP/PyEyesWeb/commit/3e582483ba00bdba2d53899d3ec410df97d4b0eb))

* remove print from synchronization.py ([`acc0c1d`](https://github.com/InfoMusCP/PyEyesWeb/commit/acc0c1dc1651ced0105ace98450f81abcddb4ded))

* fix accessing rarity value in lightness ([`56880f2`](https://github.com/InfoMusCP/PyEyesWeb/commit/56880f249488a126089217b484540c126a82c483))

* minor fixes to kinetic_energy.py and lightness.py ([`f57d665`](https://github.com/InfoMusCP/PyEyesWeb/commit/f57d665c45e53f82644056c0793b5bdc068c9af9))

* Add Kinetic Energy and Lightness ([`1360f3d`](https://github.com/InfoMusCP/PyEyesWeb/commit/1360f3d8ea08514efc82bf4b05e57c50af229042))

* remove print in rarity.py ([`ec36754`](https://github.com/InfoMusCP/PyEyesWeb/commit/ec36754ae541a7c3ab6d8fdbdaa229bc77ed3841))

* update Rarity class to return a dictionary instead of a float ([`0cfbec4`](https://github.com/InfoMusCP/PyEyesWeb/commit/0cfbec4c811fefff821b20d0a512a4c5bd8a303f))

* fix return values in clusterability.py for consistency ([`6c903fa`](https://github.com/InfoMusCP/PyEyesWeb/commit/6c903fa741bcfb1dafcfad0d61a4245125eed983))

* add rarity.py ([`79e1007`](https://github.com/InfoMusCP/PyEyesWeb/commit/79e1007e3a3bc87867b88511d8a722a63dc72c17))

* Merge branch 'Foysal440-Clusterability' ([`eff0ffc`](https://github.com/InfoMusCP/PyEyesWeb/commit/eff0ffc753f91075725b80fa9eb27d10a9ac591f))

* improve readability and documentation ([`56ade52`](https://github.com/InfoMusCP/PyEyesWeb/commit/56ade520bf50ab20af9df091ccdbf6c0aa9f973d))

* improve readability and documentation ([`c1f128e`](https://github.com/InfoMusCP/PyEyesWeb/commit/c1f128e05a9ba228747d9a1745cca632c6140128))

* Added clusterability.py ([`5632864`](https://github.com/InfoMusCP/PyEyesWeb/commit/56328644105760080c8c4a0dc40ee39625c3b104))

* bump to v0.0.1a5 ([`b7c8bf0`](https://github.com/InfoMusCP/PyEyesWeb/commit/b7c8bf0b297e0fbc226989c44e446c361edd53a9))

* Merge pull request #68 from InfoMusCP/feature/fixes

Feature/fixes ([`5c706d3`](https://github.com/InfoMusCP/PyEyesWeb/commit/5c706d3a9b6c5965ae85e343b9ce6c45bc185bc9))

* Merge branch 'main' into feature/fixes

# Conflicts:
#	docs/user_guide/theoretical_framework/analysis_primitives/synchronization.md
#	docs/user_guide/theoretical_framework/low_level/contraction_expansion.md
#	docs/user_guide/theoretical_framework/low_level/smoothness.md ([`72f2ea5`](https://github.com/InfoMusCP/PyEyesWeb/commit/72f2ea5f7f369f1facf9f0090831c35b737c58b0))

* fix broken links and review docs information ([`ae8cab1`](https://github.com/InfoMusCP/PyEyesWeb/commit/ae8cab1065d65b88e046d1aeb729a6b2c0c5e468))

* Extend smoothness functionality as raised in #66 ([`0f87455`](https://github.com/InfoMusCP/PyEyesWeb/commit/0f8745539f069ee27dee98dddd58fd569dc382d9))

* Clarify velocity input requirement for smoothness module and improve jerk computation ([`ee37a2d`](https://github.com/InfoMusCP/PyEyesWeb/commit/ee37a2d66c9f6da71deee96b73581b10ea2b3c11))

* Enhance type validation in SlidingWindow and clarify comments in PointsDensity ([`938dfd3`](https://github.com/InfoMusCP/PyEyesWeb/commit/938dfd39f91654319145d8f122753af57f448a17))

* Refactor Synchronization and SlidingWindow classes for improved functionality and clarity; update dependencies in pyproject.toml ([`7453e1d`](https://github.com/InfoMusCP/PyEyesWeb/commit/7453e1da4c08b2554aff3ca865583793590e5432))

* contraction expansion ([`42f0e6e`](https://github.com/InfoMusCP/PyEyesWeb/commit/42f0e6e7ada15750c7c40797ba063ca254778297))

* developed and tested geometric symmetry ([`9c7c431`](https://github.com/InfoMusCP/PyEyesWeb/commit/9c7c43199692a123b5551e4a76b697989a4fb947))

* Refactor DirectionChange and Suddenness classes to return dictionaries with calculated values ([`a7e956b`](https://github.com/InfoMusCP/PyEyesWeb/commit/a7e956be8978aa1d3c736accaa6c89056baba56e))

* Add DirectionChange and Suddenness classes for impulsivity evaluation ([`84d5e7a`](https://github.com/InfoMusCP/PyEyesWeb/commit/84d5e7a88b6d24a278a937c2746145f69e07f63c))

* started testing ([`4cc67ca`](https://github.com/InfoMusCP/PyEyesWeb/commit/4cc67cac3545dbc2dd983546d2f64c1adeea9fa2))

* Merge branch 'main' into test-gabriele ([`10bad5e`](https://github.com/InfoMusCP/PyEyesWeb/commit/10bad5ebbc0bf36d3a762b2b75e70760437e56e9))

* Simplify test fixtures using factory pattern ([`487451c`](https://github.com/InfoMusCP/PyEyesWeb/commit/487451c2f587bad0e171196180b0dd0bb1ec1023))

* Apply ThreadSafeHistoryBuffer and validation utilities to bilateral_symmetry ([`d0b97aa`](https://github.com/InfoMusCP/PyEyesWeb/commit/d0b97aa53532feb993e4af7d2db4887d5c2ffba2))

* Apply ThreadSafeHistoryBuffer and utilities to synchronization module ([`a8f4878`](https://github.com/InfoMusCP/PyEyesWeb/commit/a8f4878d9c3aab675a810bd8468a7ee9d0292472))

* Standardize NaN usage to np.nan for consistency ([`c1b585f`](https://github.com/InfoMusCP/PyEyesWeb/commit/c1b585fbf7413beeb4e0f701d7e2bc5c6736c1d5))

* Add helper methods to reduce duplication in signal generators ([`4d8638b`](https://github.com/InfoMusCP/PyEyesWeb/commit/4d8638bd93ce5eafe2c149ef13a71f6a01c3dba7))

* Refactor baseline validation to eliminate duplication in contraction_expansion ([`4d1e62b`](https://github.com/InfoMusCP/PyEyesWeb/commit/4d1e62bea8a28c8f3c23ea06591f967089f4a059))

* Extract phase synchronization computation to reusable utility ([`bf63a13`](https://github.com/InfoMusCP/PyEyesWeb/commit/bf63a1390ad0b7d0a9a05cc7f16345bd6fcec348))

* Add validation utilities for filter params and window size ([`5878754`](https://github.com/InfoMusCP/PyEyesWeb/commit/587875450f95e7791a5feab16f837b4f05cf07ff))

* Add ThreadSafeHistoryBuffer for centralized thread-safe operations ([`9d062b1`](https://github.com/InfoMusCP/PyEyesWeb/commit/9d062b1137d3d3ba34f4ad2eb1c247cf9fea165e))

* Add option to use real data files in CLI tool ([`521391c`](https://github.com/InfoMusCP/PyEyesWeb/commit/521391c7cb5339cbe5c4f6aa3f48d03ce45f0930))

* Fix scipy version constraint in pyproject.toml ([`efc0b61`](https://github.com/InfoMusCP/PyEyesWeb/commit/efc0b61e8e7c3ff80baa70b6f0a02c4d93fa7cf7))

* Update README and pyproject.toml  for dependency specifications ([`272a799`](https://github.com/InfoMusCP/PyEyesWeb/commit/272a79918e7886e11c2e287aa998dcf67dd6cfb2))

* Add missing dependencies for scikit-learn, pytest, opencv, and matplotlib ([`bdf16ab`](https://github.com/InfoMusCP/PyEyesWeb/commit/bdf16ab9c863711f99d2cbf1e6889bf98189693c))

* Refactor testing framework with pytest fixtures and modular architecture ([`8d960a7`](https://github.com/InfoMusCP/PyEyesWeb/commit/8d960a7a1a8ebf6f84de92b63e8c0a1c2bdc09eb))

* Remove sys.path manipulation that caused import issues for Nicola ([`10df0a1`](https://github.com/InfoMusCP/PyEyesWeb/commit/10df0a133ceb5ef1c09f2ca13043db638a52a0df))

* Update documentation ([`0aed2ff`](https://github.com/InfoMusCP/PyEyesWeb/commit/0aed2ff7d75e25f8b09b0d42ff91e15acba720c4))

* Add tests README with usage guide and examples ([`b9c6770`](https://github.com/InfoMusCP/PyEyesWeb/commit/b9c6770404b9b9a5515ce21feb44a9d9952f33a0))

* Add feature testing CLI tool with timestamped output ([`3dbb749`](https://github.com/InfoMusCP/PyEyesWeb/commit/3dbb749f9479192d781d347fe1611c862a80a54a))

* Remove TouchDesigner examples ([`570724b`](https://github.com/InfoMusCP/PyEyesWeb/commit/570724bb84f16b03cc50e916690d149b1a28597f))

* Flatten examples directory structure ([`3f1611b`](https://github.com/InfoMusCP/PyEyesWeb/commit/3f1611b0cfec4cc0375bc6079d19eba9cb360498))

* Add signal generation utilities for feature testing ([`e6ee8e2`](https://github.com/InfoMusCP/PyEyesWeb/commit/e6ee8e2df2b022004cb1af28d8aa8080990daa19))

* Move Smoothness to low_level subpackage and relocate LICENSE to .github folder ([`6ecf06d`](https://github.com/InfoMusCP/PyEyesWeb/commit/6ecf06d41e0b070076f9fd6ead2338876bab01ab))

* Fix Smoothness examples and correct SPARC interpretation in documentation ([`f03e8fd`](https://github.com/InfoMusCP/PyEyesWeb/commit/f03e8fd51516552b01e3d82a528efa668086a82f))

* Correct SPARC value interpretation in documentation (more negative = less smooth) ([`ada3ede`](https://github.com/InfoMusCP/PyEyesWeb/commit/ada3ede5c60d3e7b8d0e0d80520f2d7801d96e8a))

* Add SPARC reference documentation and remove redundant validator comments ([`da9b253`](https://github.com/InfoMusCP/PyEyesWeb/commit/da9b253953df66406283e2a5f613e39ab8752a03))

* Add thread lock, filter_params support, and centralized phase computation utilities to BilateralSymmetryAnalyzer ([`efbca98`](https://github.com/InfoMusCP/PyEyesWeb/commit/efbca98edcd4ad842ba89eaed536c4edfe9476dc))

* Refactor synchronization module: move sync.py to analysis_primitives, use centralized validators, update import paths, and remove redundant comments ([`6f501e3`](https://github.com/InfoMusCP/PyEyesWeb/commit/6f501e3c5d84f320c7dbf7491ed52cba8eff079d))

* Improve SPARC computation with normalized frequency differences and add rate_hz validation ([`ea29b2a`](https://github.com/InfoMusCP/PyEyesWeb/commit/ea29b2aba1483827ba2861e1bbaaaa94ac76ee42))

* Add validate_filter_params_tuple function to centralize filter parameter validation ([`1809010`](https://github.com/InfoMusCP/PyEyesWeb/commit/18090105a384ab042ddc725215c51cb491772b67))

* Refactor bilateral_symmetry to use centralized phase computation utilities ([`2c6fef7`](https://github.com/InfoMusCP/PyEyesWeb/commit/2c6fef727fb6ce6d505d1054294ddaf8bca00825))

* Refactor modules to use centralized validators ([`d1ea34c`](https://github.com/InfoMusCP/PyEyesWeb/commit/d1ea34c3379e1401c97669d1f066b8c1ae3862f2))

* Add validation utilities and extract filter validation ([`e700afc`](https://github.com/InfoMusCP/PyEyesWeb/commit/e700afc54250d1cfdd44cd40b63a3507873bd986))

* Fix typos and broken links in documentation (correct GitHub URL, fix variable names, and grammar corrections) ([`a1ccb04`](https://github.com/InfoMusCP/PyEyesWeb/commit/a1ccb04f8bd67f01dca8520abe0e81fd7cab99cc))

* Add thread lock to Synchronization class to prevent race conditions in plv_history access (fixes #42) ([`bf9dd0b`](https://github.com/InfoMusCP/PyEyesWeb/commit/bf9dd0b23a9249424ea1d2de10ef9ea0416388f6))

* Fix - remove test file. ([`a990ad4`](https://github.com/InfoMusCP/PyEyesWeb/commit/a990ad48818644a532ebf5e478479125a4af1f0f))

* Address issue #39 - tested and made sure all feats have a call method. ([`9621b35`](https://github.com/InfoMusCP/PyEyesWeb/commit/9621b358d6dbfe4164c8a138144e1fa852a1708b))

* Standardize all feature functions to return dictionaries ([`a73c7c0`](https://github.com/InfoMusCP/PyEyesWeb/commit/a73c7c0b09856d9323a80d43a032d9a184369edf))

* Bump version to v0.0.1a4 ([`1c40cd5`](https://github.com/InfoMusCP/PyEyesWeb/commit/1c40cd57d92445ff138a70da5af5df3affe0bf43))

* Bump version to v0.0.1a3 ([`aa20d6b`](https://github.com/InfoMusCP/PyEyesWeb/commit/aa20d6b5607c391440ec2014ab148e1c6588184c))

* bump version to v0.0.1a2 ([`32c3554`](https://github.com/InfoMusCP/PyEyesWeb/commit/32c35547afb733fc8d4484d05be1269ce86c16c7))

* Merge pull request #48 from InfoMusCP/feature/sliding_window

resize sliding_window.py at runtime and add __repr__ method ([`9b2ffc1`](https://github.com/InfoMusCP/PyEyesWeb/commit/9b2ffc1b39eb25fa1343acb0d9b74a621cc98e16))

* resize sliding_window.py at runtime and add __repr__ method ([`5c4f2e5`](https://github.com/InfoMusCP/PyEyesWeb/commit/5c4f2e5e03b01f11ed1f2363072e01a3c422ea61))

* Update README.md ([`55a591f`](https://github.com/InfoMusCP/PyEyesWeb/commit/55a591f319bfb9657303dbdc54a4282fc0c2a273))

* Merge pull request #47 from InfoMusCP/documentation

improve docs structure ([`31fbf33`](https://github.com/InfoMusCP/PyEyesWeb/commit/31fbf331f567ca8b726dde042084b0e2690c898e))

* links docstrings to user guide ([`5c7dd23`](https://github.com/InfoMusCP/PyEyesWeb/commit/5c7dd2355e71756bbcb92c5f29b666b49835bbc1))

* improve framework explanation ([`c2c885b`](https://github.com/InfoMusCP/PyEyesWeb/commit/c2c885bb4480b68b124f9812fb303105185483c0))

* improve docs structure ([`c37e9d5`](https://github.com/InfoMusCP/PyEyesWeb/commit/c37e9d514252f81ef15115f25c808e12f8527ba4))

* Merge pull request #30 from InfoMusCP/documentation

Setup Mkdocs and Getting Started page ([`293e9f0`](https://github.com/InfoMusCP/PyEyesWeb/commit/293e9f06c4645f109400656d5ebd2336b6ec6eba))

* add references to tables ([`8eb36a8`](https://github.com/InfoMusCP/PyEyesWeb/commit/8eb36a8c2a4afa9a513793d80f93a65307c202ba))

* move getting_started.md and integrations.md to specific section ([`e2a52a5`](https://github.com/InfoMusCP/PyEyesWeb/commit/e2a52a54dae1f96c59bb93723561feaf870857a9))

* merge main into current branch ([`9aeb63e`](https://github.com/InfoMusCP/PyEyesWeb/commit/9aeb63e5565f8c7a63280de95c9312e9b3c31ad8))

* Merge pull request #46 from InfoMusCP/nicola-corbellini-patch-1

Create CONTRIBUTING.md ([`2902883`](https://github.com/InfoMusCP/PyEyesWeb/commit/29028832758ca6319e3f165afb825828a63fadd5))

* Create CONTRIBUTING.md ([`2e3bfbd`](https://github.com/InfoMusCP/PyEyesWeb/commit/2e3bfbdb7a1112a806d349a2adb30b785ee98a41))

* minor fixes to readme ([`ac2c083`](https://github.com/InfoMusCP/PyEyesWeb/commit/ac2c083eecdbb1baf9fada7bf1b4099c4b9979e3))

* Merge pull request #45 from InfoMusCP/feature/readme

update README.md ([`1e5e30d`](https://github.com/InfoMusCP/PyEyesWeb/commit/1e5e30de4a513f2aaed0e3d6b6de9eaf6e1f38e7))

* update README.md ([`35202bf`](https://github.com/InfoMusCP/PyEyesWeb/commit/35202bf0cb4959901bb3a9e496d2a2ee4c01a496))

* Merge pull request #44 from InfoMusCP/feature/readme

update README.md and add CITATION.cff ([`9e50624`](https://github.com/InfoMusCP/PyEyesWeb/commit/9e5062415b08f79f982ddc14e7ceb95517c800e6))

* update README.md and add CITATION.cff ([`bc62f9b`](https://github.com/InfoMusCP/PyEyesWeb/commit/bc62f9bc2f1228867e0339fb3f4e0bfc41c7ad95))

* improve documentation ([`b11d79f`](https://github.com/InfoMusCP/PyEyesWeb/commit/b11d79f0b2b9f34e07255c6f791b7de9ee223a1c))

* Merge remote-tracking branch 'origin/main' into documentation ([`91eacb0`](https://github.com/InfoMusCP/PyEyesWeb/commit/91eacb0f8f608b3e9f02b71a46d4f07827658e65))

* Update: Make z-coordinate optional in Equilibrium by accepting both 2D and 3D inputs ([`7bd8e5e`](https://github.com/InfoMusCP/PyEyesWeb/commit/7bd8e5eefef93cbdd5c2523bdf04a36f704ef0ce))

* add user guide, modules documentation and getting started ([`d68cc93`](https://github.com/InfoMusCP/PyEyesWeb/commit/d68cc9385f1ebc4a4aa078b5c69d83e70cdc5b17))

* Merge branch 'main' into documentation ([`1ed5914`](https://github.com/InfoMusCP/PyEyesWeb/commit/1ed5914a5d7da838fa66b4de00f9094bcc056da0))

* Fix: Add __del__ method to SlidingWindow for explicit memory cleanup ([`9a35ffc`](https://github.com/InfoMusCP/PyEyesWeb/commit/9a35ffc30f8ef3f13fb9c3f98c7d645a77003f06))

* Fix: Return NaN instead of None for errors and remove print statements from Smoothness ([`d452bdb`](https://github.com/InfoMusCP/PyEyesWeb/commit/d452bdbdb615d10fe80225b1d80624a1ed0767f9))

* Fix: Add column count validation to Synchronization and return NaN for insufficient data ([`67d324a`](https://github.com/InfoMusCP/PyEyesWeb/commit/67d324ae89b221a1a287cdca557a5a5b4d60912c))

* Fix: Add array shape validation to SPARC function to prevent crashes ([`29b1d34`](https://github.com/InfoMusCP/PyEyesWeb/commit/29b1d34fa25260f8f142cd8de1e6291f0ff2fcc2))

* Fix: Update Synchronization docstring to document validation requirements and exceptions ([`008b12d`](https://github.com/InfoMusCP/PyEyesWeb/commit/008b12d1fb7c298ddaefb86b313ec5819a1b8cde))

* Fix: Add comprehensive input validation to Synchronization class constructor ([`c709114`](https://github.com/InfoMusCP/PyEyesWeb/commit/c7091148bf7626466caac3739b25909f336aa86b))

* Fix: Add validation for rate_hz and use_filter parameters in Smoothness class ([`98a96c1`](https://github.com/InfoMusCP/PyEyesWeb/commit/98a96c18364344ac45b105e9aba33c65e85bc48a))

* Fix: Replace busy wait loop with time.sleep() in TSVReader to reduce CPU usage ([`3717508`](https://github.com/InfoMusCP/PyEyesWeb/commit/37175082a675749638513ee9d2ecba8a27d6e512))

* Fix: Add input validation to SlidingWindow constructor to prevent invalid parameters ([`2e299f0`](https://github.com/InfoMusCP/PyEyesWeb/commit/2e299f0942bc3d3deecf941fc0ca01ff7781fb6b))

* Fix: Return NaN instead of 0.0 on errors in bilateral symmetry analysis ([`ac0150d`](https://github.com/InfoMusCP/PyEyesWeb/commit/ac0150dcf25fddeeb61ede91057392f2a875d6f9))

* Fix: Return NaN instead of infinity for zero baseline in contraction expansion analysis ([`83b9504`](https://github.com/InfoMusCP/PyEyesWeb/commit/83b95040616ef77c76f577ef37eefdc9602a9e5a))

* Fix: Add parameter validation to bandpass filter to prevent invalid frequencies ([`06ec347`](https://github.com/InfoMusCP/PyEyesWeb/commit/06ec3471b6109d058c0791175db5de4705aa0093))

* Fix: Return NaN for constant signals in SPARC function and validate sampling rate ([`f1e8e54`](https://github.com/InfoMusCP/PyEyesWeb/commit/f1e8e544d706f19a377d8b6559797c1f76997013))

* Fix: Handle division by zero in Equilibrium class for degenerate ellipse cases ([`2c58f4b`](https://github.com/InfoMusCP/PyEyesWeb/commit/2c58f4b6c13afa12110ccd343f1aadceb66598eb))

* Fix: Add thread-safe locking to SlidingWindow methods and return copies from to_array() to prevent race conditions ([`c5422b9`](https://github.com/InfoMusCP/PyEyesWeb/commit/c5422b915008736d57242731a0a5898e6eb1d2bc))

* Merge remote-tracking branch 'origin/main' into documentation ([`7551edf`](https://github.com/InfoMusCP/PyEyesWeb/commit/7551edf7bb009567221d26d75d77f927d54c969e))

* Moved gen_pages.py to docs/scripts ([`c4c73eb`](https://github.com/InfoMusCP/PyEyesWeb/commit/c4c73eb4ea92f2bc20798d64793f10d4c927b9be))

* Add docstrings and translate Italian comments to English in TSV reader ([`b84fd78`](https://github.com/InfoMusCP/PyEyesWeb/commit/b84fd78304dcfd8947a9ee39ceaa8a49193081a5))

* Add docstrings to signal processing functions ([`37463d6`](https://github.com/InfoMusCP/PyEyesWeb/commit/37463d6a04138c32a7fe76364963f23ad33da838))

* Add docstrings to math utility functions ([`844aadf`](https://github.com/InfoMusCP/PyEyesWeb/commit/844aadfb9ca17e219d3942f99e2d2124cb2e37a5))

* Add docstrings to contraction expansion module ([`957c945`](https://github.com/InfoMusCP/PyEyesWeb/commit/957c945cbfdbce0e58f1320d914af4870a00df24))

* Add docstrings to smoothness module ([`89d12cb`](https://github.com/InfoMusCP/PyEyesWeb/commit/89d12cb0cbc3ccbdc61dda03314a987e88091fe6))

* Add docstrings to sync module ([`783154a`](https://github.com/InfoMusCP/PyEyesWeb/commit/783154a1a2e2dd9cca8c7b6b83134da3a6383336))

* Merge pull request #29 from InfoMusCP/reorganize-examples-structure

Reorganize examples folder structure with test_scripts and touchdesigner subfolders ([`4e62409`](https://github.com/InfoMusCP/PyEyesWeb/commit/4e62409da9273b8132e94aeca52be1ace8f9e51e))

* Reorganize examples folder structure with test_scripts and touchdesigner subfolders ([`0aa95ae`](https://github.com/InfoMusCP/PyEyesWeb/commit/0aa95ae38d4fcfb262dcfba90ba2a62046f1f35a))

* setup mkdocs.yml and getting_started.md ([`e50caeb`](https://github.com/InfoMusCP/PyEyesWeb/commit/e50caeb0b4b698182529610bbde55df6a7a84285))

* update folder name ([`ddeb0ab`](https://github.com/InfoMusCP/PyEyesWeb/commit/ddeb0abbd9fff7089c8ef9fda4399678215e159c))

* Merge pull request #26 from InfoMusCP/Equilibrium

feat: add Equilibrium class with elliptical balance evaluation and in… ([`ec28e3d`](https://github.com/InfoMusCP/PyEyesWeb/commit/ec28e3d753d6dfd67d99f41ecd8fd252161b3908))

* Merge pull request #25 from InfoMusCP/feature/fix_action

fix action ([`aad66df`](https://github.com/InfoMusCP/PyEyesWeb/commit/aad66dfb6e21fed213866917e3879e13be01f9a7))

* fix action ([`486346e`](https://github.com/InfoMusCP/PyEyesWeb/commit/486346eb2d46e54519da280e0caf7ad21ee80e4a))

* fix action ([`c204bda`](https://github.com/InfoMusCP/PyEyesWeb/commit/c204bdac4b93f290f332a1e1376e378508e40a6b))

* fix action ([`81c2720`](https://github.com/InfoMusCP/PyEyesWeb/commit/81c272028175b99c661518c06a2e1b43009e55cd))

* fix action ([`282a3f5`](https://github.com/InfoMusCP/PyEyesWeb/commit/282a3f5991c2445f92e3c224679c51bde7694b6b))

* fix action ([`f97706f`](https://github.com/InfoMusCP/PyEyesWeb/commit/f97706fe193e1f705a3cb76b7d93738a460a3e30))

* fix action ([`82a3f30`](https://github.com/InfoMusCP/PyEyesWeb/commit/82a3f3064397a03625a448ec17bece914a14136e))

* Merge pull request #24 from InfoMusCP/feature/doc

setup github pages ([`1907aa2`](https://github.com/InfoMusCP/PyEyesWeb/commit/1907aa2493f1376d4825c26d5e7f884226ed0cbf))

* setup github pages ([`fcb0758`](https://github.com/InfoMusCP/PyEyesWeb/commit/fcb07586c2f7462482a22689b06b293ee14dc6f7))

* Merge pull request #23 from InfoMusCP/feature/deploy_pypi

setup pypi deploy ([`c0c6ee5`](https://github.com/InfoMusCP/PyEyesWeb/commit/c0c6ee5dd9b61fa29730b6ab051fc4c27e4522e4))

* Merge branch 'main' into feature/deploy_pypi ([`7539fd1`](https://github.com/InfoMusCP/PyEyesWeb/commit/7539fd1d51a20c8c2dc1eba480d54d5e6ae37f75))

* Update pyproject.toml ([`ab52cc1`](https://github.com/InfoMusCP/PyEyesWeb/commit/ab52cc12a1f2e225f55ee230132302c359cd87a1))

* Merge pull request #22 from InfoMusCP/update-repo-name-to-pyeyesweb

update repository name from infomove to pyeyesweb ([`2c3a7b4`](https://github.com/InfoMusCP/PyEyesWeb/commit/2c3a7b4c84a191ecbd4f96c1281a134f82f119ee))

* update repository name from infomove to pyeyesweb ([`8a4ef86`](https://github.com/InfoMusCP/PyEyesWeb/commit/8a4ef86b9230137365b535988805ee9d9ceee00e))

* setup pypi deploy ([`de1781c`](https://github.com/InfoMusCP/PyEyesWeb/commit/de1781c7e31c710544ba4c7b35d9b542f75f63d7))

* Merge pull request #21 from InfoMusCP/feature/license

add license to pyproject.toml ([`975b67a`](https://github.com/InfoMusCP/PyEyesWeb/commit/975b67ac9f7471f48e7d20f6318b8125fd37c892))

* add license to pyproject.toml ([`bcf8b6f`](https://github.com/InfoMusCP/PyEyesWeb/commit/bcf8b6fae075a279ab4f3ed6a1d69af16fb305e1))

* Create LICENSE ([`4b5d49a`](https://github.com/InfoMusCP/PyEyesWeb/commit/4b5d49aad123f1eaade142171dc85ce8ce62036c))

* Merge pull request #20 from InfoMusCP/feature/sliding_window_doc

add `SlidingWindow` docstrings ([`4ecf6fe`](https://github.com/InfoMusCP/PyEyesWeb/commit/4ecf6fe4ff68828db32d363a908d1e66027f4af6))

* add `SlidingWindow` docstrings ([`119f45d`](https://github.com/InfoMusCP/PyEyesWeb/commit/119f45d50ced07270d99d81b5cef968cd1241728))

* Merge pull request #19 from InfoMusCP/feature/pyproject

update pyproject.toml ([`d97cbef`](https://github.com/InfoMusCP/PyEyesWeb/commit/d97cbef47700ae21f67e522ffcf3f92f98257f1c))

* update pyproject.toml ([`fdbfbd5`](https://github.com/InfoMusCP/PyEyesWeb/commit/fdbfbd5fcfa80dc9f05fe9873ba7ccee7eff0ea5))

* Update README.md to reflect change of repo name ([`4df54c5`](https://github.com/InfoMusCP/PyEyesWeb/commit/4df54c50f07b674be957660a0c65d0faa94817a3))

* remove unnecessary parts ([`6306d38`](https://github.com/InfoMusCP/PyEyesWeb/commit/6306d3869b207a968208c22ea081d24ecca6db55))

* Merge pull request #17 from InfoMusCP/docs/modular-readme

initial documentation structure ([`a833309`](https://github.com/InfoMusCP/PyEyesWeb/commit/a833309ec973c2a87a871ab2b06a4575d175bb55))

* initial documentation structure ([`d2afe48`](https://github.com/InfoMusCP/PyEyesWeb/commit/d2afe48b289536bcd927d9bcfb96ec6de81099f7))

* add comprehensive biomechanical test suite for bilateral symmetry analysis ([`bac585e`](https://github.com/InfoMusCP/PyEyesWeb/commit/bac585e07f3de118aecc49f56a05a807b793e990))

* implement bilateral symmetry analysis with research-based methods ([`9f5bcc1`](https://github.com/InfoMusCP/PyEyesWeb/commit/9f5bcc1eae995deee463fc6f770a20ec6fb54707))

* add example demonstrating contraction_expansion module usage ([`4454e06`](https://github.com/InfoMusCP/PyEyesWeb/commit/4454e06da7423220cf920aaca4da8a82018e88dc))

* implement contraction_expansion module with numba-optimized geometric analysis ([`cbfb4cc`](https://github.com/InfoMusCP/PyEyesWeb/commit/cbfb4ccfc8c1f923bde2667f220808bf5eb665f9))

* add numba dependency to pyproject.toml ([`d77a92a`](https://github.com/InfoMusCP/PyEyesWeb/commit/d77a92a3f7f9b504e12f9f3062daa238ac224e54))

* Merge branch 'fix/core-sync' ([`58da844`](https://github.com/InfoMusCP/PyEyesWeb/commit/58da844a3aa77cf1fb4c307863c15dc96f3230b1))

* Merge pull request #16 from InfoMusCP/fix/core-sync

optimize phase computation with vectorized operations and remove redu… ([`e4950bf`](https://github.com/InfoMusCP/PyEyesWeb/commit/e4950bfb261e4f8351457b945c971b9fdcb7a397))

* optimize phase computation with vectorized operations and remove redundant calculations ([`72dee82`](https://github.com/InfoMusCP/PyEyesWeb/commit/72dee828f2b8a472f612c7fab7a238b33e949978))

* Merge branch 'main' of https://github.com/InfoMusCP/InfoMove ([`937da93`](https://github.com/InfoMusCP/PyEyesWeb/commit/937da93aaeffdc3d0b787c2038af5ca87416a98a))

* Update demo ([`772fb9d`](https://github.com/InfoMusCP/PyEyesWeb/commit/772fb9d6bfddef898429a17beeba69f1d7b55f10))

* Merge pull request #13 from InfoMusCP/feature/win_installation_script

Create TD demo installation script ([`97edd16`](https://github.com/InfoMusCP/PyEyesWeb/commit/97edd16ff49bcf10f6843c11adcccc210f615332))

* Create setup.bat ([`1366730`](https://github.com/InfoMusCP/PyEyesWeb/commit/136673077f586ddce2db728a7c27bdf5f663d5da))

* Merge pull request #9 from InfoMusCP/develop/td_synch_demo

Add TD demo draft ([`861b49f`](https://github.com/InfoMusCP/PyEyesWeb/commit/861b49f417418a7441c62adbe92a4b32e5a2f661))

* remove Lib folder ([`1133775`](https://github.com/InfoMusCP/PyEyesWeb/commit/1133775a1ba6cb5b8a11e6cb3d571d997daa01dd))

* add Lib to .gitignore and remove action ([`016bffa`](https://github.com/InfoMusCP/PyEyesWeb/commit/016bffab42b3d37f1859896cb6339fc639ee9253))

* fix actions ([`44fd9d2`](https://github.com/InfoMusCP/PyEyesWeb/commit/44fd9d25a19618ab624e3c22fecc2d88cb251e04))

* fix build.yml action ([`dc10283`](https://github.com/InfoMusCP/PyEyesWeb/commit/dc102834f49549cfb784e418ddc10ffa391882a5))

* fix build.yml action ([`0960b5b`](https://github.com/InfoMusCP/PyEyesWeb/commit/0960b5bd17da4d59adeb4bb13ffb400190eab56e))

* add pyproject.toml for TD demo and installed Lib ([`a8c9504`](https://github.com/InfoMusCP/PyEyesWeb/commit/a8c9504853d82457be9c543281fcf844ad550024))

* add pyproject.toml for TD demo ([`fb6a8bd`](https://github.com/InfoMusCP/PyEyesWeb/commit/fb6a8bdb4e6291abe044c27543780525bd6d8caa))

* This TSV reader is currently designed starting from exported files from Qualisys Motion Capture. Future versions will support reading generic TSV files with different headers ([`bd726a3`](https://github.com/InfoMusCP/PyEyesWeb/commit/bd726a3a9c3a0af7c9aec10850c2735269f75969))

* Merge pull request #8 from InfoMusCP/develop/sliding_window

Implement `SlidingWindow` ([`6de8872`](https://github.com/InfoMusCP/PyEyesWeb/commit/6de887299f767b82d874ffef5cbb2abc09cab0ba))

* add type checking and empty init ([`40df64a`](https://github.com/InfoMusCP/PyEyesWeb/commit/40df64a63ef3e2a657938f3aedd3636d47b9372f))

* add sliding_window.py and refactor features ([`4c30537`](https://github.com/InfoMusCP/PyEyesWeb/commit/4c305378f577fccce2a22f2fb6e0acb6069951ce))
