# V2X Message Generator

A Python command-line tool for generating SAE J2735 MAP and SPaT messages from
one JSON5 intersection configuration and decoding raw MAP and SPaT messages for
inspection. Generated messages use UPER and are written as hexadecimal text.

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

Install dependencies and the local J2735 package:

```sh
uv sync
uv pip install ./src/j2735_202409
```

Generate a MAP message:

```sh
uv run v2x-project map inputFiles/SampleIntersection.json5 output/sample_map.txt
```

Generate a SPaT batch:

```sh
uv run v2x-project spat inputFiles/SampleIntersection.json5 output/sample_spat.txt
```

Generate both from the same UTC start time:

```sh
uv run v2x-project both inputFiles/SampleIntersection.json5 --map-output output/sample_map.txt --spat-output output/sample_spat.txt
```

Decode the SPaT batch and save the complete decoded values as JSON:

```sh
uv run v2x-project decode output/sample_spat.txt --json-output output/sample_spat_decoded.json
```

Decode a MAP message to JSON without terminal output:

```sh
uv run v2x-project decode output/sample_map.txt --message-type map --json-output output/sample_map_decoded.json
```

Both decoders accept a hexadecimal message or a file with one message per line.
SPaT is the default message type. MAP decoding writes an array of successfully
decoded messages to JSON and uses a nonzero exit status if any message fails.

The MAP command writes one hexadecimal UPER message. The SPaT command writes
one message per sample time, with one hexadecimal UPER message per line. Use
`uv run v2x-project --help` for command details.

## Sample configuration

[`inputFiles/SampleIntersection.json5`](inputFiles/SampleIntersection.json5)
shows the unified configuration shape: shared intersection identity and
separate MAP and SPaT sections. The initial MAP profile is a four-way,
single-lane layout without left turns. It includes unsignalized right-turn
connectivity and signalized through connections. SPaT phase durations must be
positive, align with the configured message interval, and have matching totals
for all movements.

The implementation accepts message intervals of at least 0.1 seconds in
millisecond increments. `minEndTime` is rounded to the nearest tenth of a
second, with halfway values rounded up, and is encoded as time within its UTC
hour. The decoder reports the day of year and UTC clock time because J2735
`MinuteOfTheYear` does not contain a calendar year.

## Project documentation

- [Proposal](Documentation/Proposal.md): project purpose and intended design.
- [Formal specification](Documentation/FormalSpecification.md): requirements
  for the initial profile.
- [Ideas and considerations](Documentation/IdeasAndConsiderations.md): design
  options and possible future work.
- [SPaT ASN.1 notes](Documentation/SPaT_ASN1.md): notes on the message
  structure.
- [MAP ASN.1 notes](Documentation/MAP_ASN1.md): notes on the message structure.
- [Project contents](toc.md): documentation, sample inputs, and source files.

The `v2x-project` command provides `map`, `spat`, `both`, and `decode`
operations. J2735 ASN.1 definitions are provided by the
`src/j2735_202409` Git submodule; keep it initialized when setting up a fresh
checkout.
