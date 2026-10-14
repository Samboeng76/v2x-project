# V2X Message Generator

A work-in-progress Python project for generating and inspecting SAE J2735
messages. The current runnable example creates a timed batch of SPaT messages
from a JSON5 configuration, encodes them as UPER hexadecimal, and can decode
the result for inspection. MAP generation is still part of the project plan.

## Quick start

Requirements: Python 3.13 or newer and [uv](https://docs.astral.sh/uv/).

Clone the repository with its J2735 definitions submodule:

```sh
git clone --recurse-submodules <repository-url>
cd v2x-project
```

If you already cloned without submodules, initialize them with:

```sh
git submodule update --init --recursive
```

Install the Python dependencies and the local J2735 package:

```sh
uv sync
uv pip install ./src/j2735_202409
```

Generate a SPaT batch from the sample configuration:

```sh
uv run python src/SampleSPaTBatchGenerator.py inputFiles/SampleIntersection.json5 output/sample_spat.txt
```

Decode the generated messages and write their full decoded values to JSON:

```sh
uv run python src/SPaTDecoder.py output/sample_spat.txt --json-output output/sample_spat_decoded.json
```

The generator writes one hexadecimal UPER message per line. The decoder prints
a summary for each valid message and writes the decoded data to the requested
JSON file.

## Sample configuration

The input file [`inputFiles/SampleIntersection.json5`](inputFiles/SampleIntersection.json5)
shows the unified configuration shape: shared intersection identity, separate
MAP and SPaT sections, and stable signal-group references. MAP geometry is a
placeholder while its input schema is being developed. The current SPaT batch
generator reads the SPaT section; phase durations must be positive and align
with the configured message interval.

## Project documentation

- [Proposal](Documentation/Proposal.md): project purpose and intended design.
- [Formal specification](Documentation/FormalSpecification.md): current
  requirements and open details.
- [Ideas and considerations](Documentation/IdeasAndConsiderations.md): design
  options and possible future work.
- [SPaT ASN.1 notes](Documentation/SPaT_ASN1.md): notes on the message
  structure.
- [MAP ASN.1 notes](Documentation/MAP_ASN1.md): notes on the message
  structure.
- [Project contents](toc.md): documentation, sample inputs, and source files.

## Current scope

The command-line scripts under `src/` are the working entry points. The
`v2x-project` package command is currently a placeholder. The J2735 ASN.1
definitions are provided by the `src/j2735_202409` Git submodule; keep that
submodule initialized when setting up a fresh checkout.
