# napari-subboxer

[![License](https://img.shields.io/pypi/l/napari-subboxer.svg?color=green)](https://github.com/alisterburt/napari-subboxer/raw/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-subboxer.svg?color=green)](https://pypi.org/project/napari-subboxer)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-subboxer.svg?color=green)](https://python.org)
[![tests](https://github.com/alisterburt/napari-subboxer/workflows/tests/badge.svg)](https://github.com/alisterburt/napari-subboxer/actions)
[![codecov](https://codecov.io/gh/alisterburt/napari-subboxer/branch/master/graph/badge.svg)](https://codecov.io/gh/alisterburt/napari-subboxer)

A napari plugin to define [subboxing transformations] and a CLI tool to apply them.

The plugin is under active development, unstable and provided with no guarantees.
If you would like to use it, please get in touch!

![subboxer demo](https://user-images.githubusercontent.com/7307488/143312042-770a4ed2-7519-4114-9119-2323196aadfd.gif)


## Installation

You can install `napari-subboxer` via [pip]:

    pip install napari-subboxer

It is recommended to install `napari-subboxer` into a clean virtual environment.

## Usage

The expected workflow for using this plugin and further refinement is 
1. define and save subboxing transformations using `napari-subboxer define`
2. apply transformations using `napari-subboxer apply`
3. re-reconstruct/extract your particle set with the new set of poses
4. reconstruct your particles to create a new reference centered on your subparticle
5. refine refine refine!

`napari-subboxer define` define has three modes, activated via buttons in the GUI
- add new point
- define z-axis of each point
- define in plane orientation of each point

In add or define-z mode alt-click on the plane to add a new point.
In in-plane mode alt-click and drag to set the in plane orientation of the current point

The plane can be moved by clicking and dragging. 
The plane can be reoriented with the x/y/z/o keys 
(o sets the plane normal to the camera view direction).

Subboxing transformations can currently only be applied on RELION 3.1 star files.

## Contributing

Contributions are very welcome. 

## License

Distributed under the terms of the [BSD-3] license,
"napari-subboxer" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin

[file an issue]: https://github.com/alisterburt/napari-subboxer/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
