# V2X Message Generator: Project Contents

## Getting started

- [README](README.md) — setup, commands, and sample usage.

## Documentation

- [Formal specification](Documentation/FormalSpecification.md) — current requirements and supported profile.
- [SPaT ASN.1 notes](Documentation/SPaT_ASN1.md) — SPaT message structure and fields.
- [MAP ASN.1 notes](Documentation/MAP_ASN1.md) — MAP message structure and fields.
- [V2X Communications Message Set Dictionary](<Documentation/V2X Communications Message Set Dictionary.pdf>) — J2735 reference PDF.

## Input files

- [Sample intersection](inputFiles/SampleIntersection.json5) — current JSON5 configuration example.

## Source files

- [Command-line interface](src/v2x_project/cli.py) — commands and file handling.
- [Core](src/v2x_project/core.py) — configuration, MAP/SPaT encoding, and decoding.
- [Package entry points](src/v2x_project/__init__.py) and [module entry point](src/v2x_project/__main__.py).
- [J2735 definitions](src/j2735_202409/) — Git submodule used by the generator.

## Tests

- [Configuration tests](tests/test_configuration.py)
- [Generation tests](tests/test_generation.py)
- [Command-line behavior tests](tests/test_cli_behavior.py)
- [MAP decoder tests](tests/test_map_decoder.py)

## Project setup

- [Project metadata and dependencies](pyproject.toml)
- [Dependency lockfile](uv.lock)
- [Python version](.python-version)
- [Git submodule configuration](.gitmodules)
