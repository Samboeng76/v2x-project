Overall Functionality:
----------------------

> **Draft status:** This specification is evolving alongside the prototype.
> Items described as future work or requiring evaluation are not settled
> requirements yet.

1. The system shall parse a JSON5 input file containing the information required
   to generate a J2735 message.
2. The JSON5 input format shall be higher level than the ASN.1 definitions.
3. The system shall obtain the required SAE J2735 ASN.1 definitions from the
   USDOT J2735 Python library.
4. The system shall use PyCrate to construct and encode the generated message
   using the Unaligned Packed Encoding Rules (UPER).
5. The system shall provide the resulting encoded message as raw hexadecimal
   bytes.

SPAT Functionality:
-------------------

1. The SPAT message format to be used is shown below.

   * Top-level `SPAT` data frame:
     * `intersections`: list of 1 to 32 `IntersectionState` records
     * `timeStamp`: optional integer (`MinuteOfTheYear`)
     * `name`: optional string (`DescriptiveName`)
   * Each `IntersectionState` requires:
     * ID: `IntersectionReferenceID` containing an integer intersection ID; the
       optional region integer is omitted
     * Revision: integer (`MsgCount`, 0 through 127), managed automatically
     * Status: 16-bit bit string (`IntersectionStatusObject`); defaults to
       (0, 16)
     * States: list of movement-state records (`MovementList`), described below
   * SPAT IntersectionState Message Optional:
     * Name: string (`DescriptiveName`)
2. Status shall be an optional field in the input JSON5 file. The default value
   shall be `(0, 16)` (16 zero bits). The input format of the JSON5 will be a
   string in the format "0bxxxxxxxxxxxxxxxx" or "0x1234."

3. The generator shall manage `revision` automatically: start at 0, increment
   per SPaT message, and wrap from 127 to 0. Do not provide it in JSON5.

4. Each movement state shall support, at minimum:

   * Movement name: string (`DescriptiveName`, optional in the ASN.1 structure)
   * Signal group: integer (`SignalGroupID`, 1 through 254); for the current
     prototype, it shall be derived from the movement phase rather than supplied
     in JSON5
   * State-Time-Speed: list of movement events (`MovementEventList`)
5. Each State-Time-Speed entry shall support the following fields:

   * Event state: enumerated value (`MovementPhaseState`)
   * Timing: ASN.1 record (`TimeChangeDetails`)
     * Minimum end time: integer (`TimeMark`, 0 through 36111), set to the end
       of the current phase interval

   Only `minEndTime` is supported initially. Support for other timing fields may
   be added later.

6. Additional SPAT fields defined by the applicable SAE J2735 ASN.1
   specification shall be evaluated for inclusion as the implementation is
   expanded.

7. The input JSON5 shall consist of the following fields:

   * `messageType`: string; currently `"SPAT"`
   * `includeTimestamps`: Boolean; defaults to true; optional
   * `messageInterval`: decimal; optional number of seconds between messages;
     defaults to `0.1`
   * `status`:string; optional; defaults to (0,16)
   * `intersection`: object containing:
     * `id`: integer intersection ID
     * `name`: string
   * `movements`: array of movement objects containing:
     * `name`: string
     * `phases`: ordered array of phase intervals; each interval contains:
       * `phase`: string enum (`MovementPhaseState`); use one of the ASN.1 names
         below:
         * `unavailable` (0): unsupported by the temporary signal-group rule; 0
           is reserved
         * `dark` (1): signal unlit
         * `stop-Then-Proceed` (2): stop, then proceed when safe
         * `stop-And-Remain` (3): stop
         * `pre-Movement` (4): stop and prepare to proceed
         * `permissive-Movement-Allowed` (5): proceed, yielding to conflicting
           traffic
         * `protected-Movement-Allowed` (6): protected right-of-way
         * `permissive-clearance` (7): prepare to stop; clear if unable to stop
           safely
         * `protected-clearance` (8): clear in the indicated direction
         * `caution-Conflicting-Traffic` (9): proceed with caution; traffic may
           conflict
       * `duration`: positive number of seconds for this phase interval, no more
         than 3600

   The input shall not request or supply a region value; the optional `region`
   component of `IntersectionReferenceID` shall be omitted.

   Temporary simplification: derive `signalGroup` from the phase number. This is
   not a stable movement ID: it changes with phase, and movements in the same
   phase share an ID. Revisit before linking SPaT to MAP.

   Each `duration` specifies how long its phase remains active, up to one hour.
   Durations for every movement shall sum to the same batch length and be exact
   multiples of `messageInterval`. Sample at 0, `messageInterval`, 2 \*
   `messageInterval`, and so on, stopping before the batch end. Each message
   contains the active phase for every movement; `minEndTime` marks that phase
   interval's end in tenths of a second within the current or next UTC hour. Use
   one UTC start time plus elapsed simulation time for timestamps and timing.
   Not every phase applies to every region or operating mode.

8. The input JSON5 shall allow for simplified phase names with "green"
   corresponding to phase 6, "red" corresponding to phase 3, and "yellow"
   corresponding to phase 8 (verify this). 

9. `includeTimestamps` is an optional field in JSON5. If `true`, populate
   available timestamp fields from the message's captured UTC time: top-level
   `timeStamp` and intersection `moy` (`MinuteOfTheYear` integers), and
   intersection `timeStamp` (`DSecond` integer). True will be the defualt value.

10. The batch length is the sum of the ordered phase durations. For example, 10
    seconds of green followed by 5 seconds of yellow produces a 15-second batch:
    150 messages at the default 0.1-second interval.

11. The system shall provide documented defaults for fields that do not require
    a user-provided value. For SPaT, the status default is a 16-bit all-zero bit
    string.

12. The generator shall support batch output to a text file, with one
    hex-encoded UPER message per line. Messages shall represent evenly spaced
    sample times; the generator shall not need to wait in real time while
    creating the file. The sum of the phase durations specifies the batch
    length.

13. The optional JSON5 field `messageInterval` shall be a positive number of
    seconds between messages. It shall default to `0.1` seconds when omitted.

14. Each output line shall encode a complete top-level J2735 `SPAT` data frame,
    including its `intersections` list. For this project, that list shall
    contain the configured intersection; output shall not encode an
    `IntersectionState` by itself.

Example JSON5 input:

```
{
  messageType: "SPAT",
  includeTimestamps: true,
  messageInterval: 0.1,
  
  intersection: {
    id: 42,
    name: "Test Intersection"
  },

  movements: [
    {
      name: "Northbound Through",
      phases: [
        { phase: "protected-Movement-Allowed", duration: 10 },
        { phase: "protected-clearance", duration: 5 }
      ]
    }
  ]
}
```

MAP Functionality:
------------------

1. The system shall convert the completed MAP `MapData` value to UPER-encoded
   bytes.

2. The MAP message format to be used is shown below.

   * Top-level `MapData` data frame:
     * `timeStamp`: optional integer (`MinuteOfTheYear`)
     * `msgIssueRevision`: integer (`MsgCount`, 0 through 127)
     * `layerType`: optional enumeration (`LayerType`)
     * `layerID`: optional integer (`LayerID`)
     * `intersections`: optional list of intersection geometries
       (`IntersectionGeometryList`)
     * `regional`: optional list of regional extensions (`RegionalExtension`)
   * Fields Being ignored:
     * `roadSegments`: optional list of roadway descriptions (`RoadSegmentList`)
     * `dataParameters`: optional metadata about the map contents
       (`DataParameters`)
     * `restrictionList`: optional restriction class assignments
       (`RestrictionClassList`)
3. As seen above, the `dataParameters` and `restrictionList` are not being
   supported. This project also is focused the intersection aspect of the MAP
   messages. Due to this, all fields specifying road segments (`roadSegments`
   and subfields) are not being implemnted at this time.

4. Unlike SPaT messages, MAP messages will not be generated in batches. For the
   current static-map implementation, the top-level `msgIssueRevision` value
   shall remain at zero.

5. Each generated `IntersectionGeometry` shall include:

   * `id`: an `IntersectionReferenceID` with an `IntersectionID`; the optional
     `region` value is omitted in the initial local-project profile
   * `revision`: a `MsgCount` integer from 0 through 127
   * `refPoint`: a `Position3D` containing latitude, longitude, and optional
     elevation
   * `laneSet`: one or more `GenericLane` records

SPaT Debugging Decoding:
------------------------

1. The system shall provide a decoder for raw hexadecimal J2735 `SPAT` messages
   encoded using UPER.
2. The decoder shall accept either:
   * A hexadecimal message supplied directly as a command-line argument; or
   * A text file containing one hexadecimal message per line.
3. Whitespace within a message shall be ignored. Blank lines in an input file
   shall be skipped.
4. The terminal output shall use a compact, human-readable summary with one line
   per decoded message. Each summary shall identify the source line and message
   time, then show each movement's name, signal state, and `minEndTime` in a
   readable time format.
5. The decoder shall also write the complete decoded ASN.1 values as indented
   JSON to a separate file. The JSON document shall contain all successfully
   decoded messages in input order. Each run shall overwrite the selected output
   file; users who want to keep an earlier result shall save a separate copy.
6. For a text-file input, the default JSON output path shall be
   `output/<input-file-name>_decoded.json`, where `<input-file-name>` is the
   input file name without its extension. The user may provide a different JSON
   output path. For a hexadecimal message supplied directly on the command line,
   the default path shall be `output/decoded_spat.json`.
7. When decoding a file, the decoder shall process every nonblank line
   independently and identify each terminal summary by its source line number.
8. If a message contains invalid hexadecimal data or cannot be decoded as a
   J2735 `SPAT` UPER message, the decoder shall report the error. For file
   input, the error shall include the source line number. Only successfully
   decoded messages shall be included in the JSON output file.
9. The initial decoder shall support the raw top-level `SPAT` messages emitted
   by this project. Supporting other J2735 message types or framed transport
   data is future work.
10. This decoder is largly for debugging purposes at the moment.

Implementation Notes
--------------------

1. The provided USDOT library can be used by `import j2735_202409.j2735_202409
   as j2735`

2. A SPAT object can be created by `SPAT = j2735.SPAT`

3. The code below shows an exploratory `IntersectionState` value only. It is not
   a complete output message; batch output shall place the intersection state in
   the top-level `SPAT.intersections` list.

```
SPAT.IntersectionState.set_val({
    "name": "Test Intersection",

    "id": {"id": 42},

    "status": (0, 16),
    "states": [
        {
            "movementName": "Northbound Through",

            "signalGroup": 3,

            "state-time-speed": [
                {
                    "eventState": "stop-And-Remain",

                    "timing": {"minEndTime": 100}
                }
            ]
        }
    ]
})
```

Tools To Use:
-------------

1. Package Manager: uv
2. Formatter: ruff
3. Libraries: PyCrate, PyJson5,
   [USDOT J2735](https://github.com/usdot-fhwa-stol/j2735_202409/tree/main)
