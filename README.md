# LabLib
![](https://img.shields.io/badge/os-windows-blue)
[![run all tests](https://github.com/ynput/LabLib/actions/workflows/run_all_tests.yml/badge.svg)](https://github.com/ynput/LabLib/actions/workflows/run_all_tests.yml)
[![documentation](https://github.com/ynput/LabLib/actions/workflows/documentation.yml/badge.svg)](https://github.com/ynput/LabLib/actions/workflows/documentation.yml)

Generate intermediate sequences for VFX processing using OIIO and FFMPEG!

This module aims to help by providing helper classes and functions to:
- Get basic info from videos and images using iinfo and ffprobe as a fallback.
- Read and parse effect json outputted by [AYON/Openpype](https://github.com/ynput) for pipeline automation.
- Create a custom OCIO config file for direct use.
- Create OIIO and FFMPEG matrix values to be used in filters for repositioning.
- Create correctly formed OIIO commandline strings automatically.
- Render out frames with Color and Repositioning baked in using oiiotool

Check out the full documentation over at https://ynput.github.io/LabLib/

## Instructions
The core functionality relies on using **Processors** and **Operators** to compute the correct commandline parameters.

**Operators** are single operation classes that hold your operation parameters (translation, luts, cdls etc.)

**Processors** (usually classes such as `ColorTransformProcessor`) compute **Operators** chains together. They can be fed ordered lists of dicts (with same name attributes as Operator classes) or ordered lists of **Operators** objects, or one at a time for secondary processing between the chained operations. On compute they return their relevant section of commandline flags to be passed to oiio.

**Renderers** take care of returning the fully formed commanline command and executing it.

## Installation
LabLib requires `python-3.9` and uses `poetry` for managing its dependencies.

It's encouraged to use the provided PowerShell script to install and download the binaries for [oiiotool](https://www.patreon.com/posts/openimageio-oiio-63609827), [ffmpeg](https://github.com/GyanD/codexffmpeg/releases/tag/7.0.1), the [OCIO Color Configs](https://github.com/colour-science/OpenColorIO-Configs/releases/tag/v1.2) and the font [Source Code Pro](https://fontsource.org/fonts/source-code-pro) which is used in tests.

- clone this repo
- `.\start.ps1 install`
- `.\start.ps1 get-dependencies`

### Testing
You can run the full suite with `.\start.ps1 test` or to run custom `pytest` commands make sure to be in the cloned repository's directory and run `poetry run pytest [ARGS]`.


## Contributing
The best way to contribute to LabLib currently is to write extensive test cases for all modules. But also sharing your thoughts and ideas on the [Discussions Page](https://github.com/ynput/LabLib/discussions) really helps to keep this project going 💞
