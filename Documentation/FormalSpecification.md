sOverall Functionality:
-----------------------

> **Draft status:** This specification is evolving alongside the prototype.
> Items described as future work or requiring evaluation are not settled
> requirements yet.

1. The system shall parse a JSON5 input file containing the information required
   to generate MAP and/or SPaT J2735 messages for an intersection.
2. The JSON5 input format shall be higher level than the ASN.1 definitions.
3. One JSON5 configuration shall describe the intersection and contain the
   settings for both message types. Shared intersection identity and timestamp
   settings shall be defined once. MAP and SPaT data shall remain in their own
   sections and shall be handled by separate generation operations; users may
   generate MAP, SPaT, or both.
4. The system shall obtain the required SAE J2735 ASN.1 definitions from the
   USDOT J2735 Python library.
5. The system shall use PyCrate to construct and encode the generated message
   using the Unaligned Packed Encoding Rules (UPER).
6. The system shall provide the resulting encoded message as raw hexadecimal
   bytes.

MAP/SPaT cross-message consistency:
-----------------------------------

1. The intersection ID shall be shared by the MAP and SPaT output for the same
   intersection.
2. Signal-group IDs shall appear in the SPaT movement definitions and in the
   corresponding MAP lane connections. The generator shall check that each ID
   used to link a MAP lane connection to a signalized movement is present in
   both sections. The MAP and SPaT movement/lane data remain independently
   defined in their respective sections.
3. MAP and SPaT timestamps shall use a common UTC time basis. For a SPaT batch,
   the shared start time shall be the MAP timestamp and the timestamp of the
   first SPaT sample; subsequent SPaT timestamps shall advance by the elapsed
   simulation time. When `includeTimestamps` is false, optional timestamps shall
   be omitted from both messages.
4. These are the cross-message values required to agree in the initial profile.
   MAP geometry revision and SPaT message revision are independent counters.

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
   * Signal group: integer (`SignalGroupID`); required in JSON5 and stable for
     the movement across all phase states. The initial project profile supports:
     * `1`: Northbound through
     * `2`: Southbound through
     * `3`: Eastbound through
     * `4`: Westbound through
     * `5`: Northbound left turn
     * `6`: Southbound left turn Other signal group assignments are not
       supported by this initial profile.
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

7. The shared JSON5 configuration shall contain the intersection identity and
   timestamp setting. Message-specific data shall be grouped under `map` and
   `spat` sections. The current SPaT fields and phase schedule are described
   below; the complete MAP input schema remains to be specified as MAP
   generation is implemented.

   The shared configuration shall contain:

   * `includeTimestamps`: Boolean; defaults to true; controls timestamp fields
     in both message types
   * `intersection`: shared object containing:
     * `id`: integer intersection ID
     * `name`: string
   * `map`: object containing MAP-specific geometry, lanes, and lane
     connections. A connection's `signalGroup`, when present, refers to a SPaT
     movement; the detailed MAP schema remains to be specified.
   * `spat`: object containing SPaT movement definitions and SPaT-specific
     settings:
     * `movements`: array of movement objects containing:
       * `name`: string
       * `signalGroup`: integer; one of the six supported stable movement IDs
       * `phases`: ordered array of phase intervals
     * `messageInterval`: decimal; optional number of seconds between messages;
       defaults to `0.1`
     * `status`: string; optional; defaults to (0, 16)

   Each SPaT movement's `phases` array contains ordered phase intervals. Each
   interval contains: \* `phase`: string enum (`MovementPhaseState`); use one of
   the ASN.1 names below: \* `unavailable` (0): not supported in the initial
   project profile \* `dark` (1): signal unlit \* `stop-Then-Proceed` (2): stop,
   then proceed when safe \* `stop-And-Remain` (3): stop \* `pre-Movement` (4):
   stop and prepare to proceed \* `permissive-Movement-Allowed` (5): proceed,
   yielding to conflicting traffic \* `protected-Movement-Allowed` (6):
   protected right-of-way \* `permissive-clearance` (7): prepare to stop; clear
   if unable to stop safely \* `protected-clearance` (8): clear in the indicated
   direction \* `caution-Conflicting-Traffic` (9): proceed with caution; traffic
   may conflict \* `duration`: positive number of seconds for this phase
   interval, no more than 3600

   The input shall not request or supply a region value; the optional `region`
   component of `IntersectionReferenceID` shall be omitted.

   Signal group IDs identify movements and do not change when the active phase
   changes. A matching ID in a MAP lane connection refers to its SPaT movement.
   The six assignments above are the initial project profile; they are a
   project-level mapping, not a universal numbering prescribed by J2735.

   Each `duration` specifies how long its phase remains active, up to one hour.
   Durations for every movement shall sum to the same batch length and be exact
   multiples of `messageInterval`. Sample at 0, `messageInterval`, 2 \*
   `messageInterval`, and so on, stopping before the batch end. Each message
   contains the active phase for every movement; `minEndTime` marks that phase
   interval's end in tenths of a second within the current or next UTC hour. Use
   the shared UTC start time plus elapsed simulation time for SPaT timestamps
   and timing. When MAP and SPaT are generated together, the MAP timestamp
   corresponds to the shared start time, which is also the timestamp of SPaT's
   first sample. Not every phase applies to every region or operating mode.

8. The SPaT phase schedule shall allow for simplified phase names with "green"
   corresponding to phase 6, "red" corresponding to phase 3, and "yellow"
   corresponding to phase 8 (verify this). 

9. `includeTimestamps` is an optional field in the shared JSON5 configuration.
   If `true`, populate available timestamp fields from the shared UTC start time
   and simulation time. MAP's `timeStamp` and SPaT's top-level `timeStamp` and
   intersection `moy` use `MinuteOfTheYear`. SPaT's intersection `timeStamp`
   uses `DSecond`. The MAP timestamp shall agree to the minute with the first
   SPaT sample when both messages are generated for the same batch.

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
    `0.1` seconds is the shortest supported interval.

14. Each output line shall encode a complete top-level J2735 `SPAT` data frame,
    including its `intersections` list. For this project, that list shall
    contain the configured intersection; output shall not encode an
    `IntersectionState` by itself.

Example JSON5 input:

```
{
  includeTimestamps: true,

  intersection: {
    id: 42,
    name: "Test Intersection"
  },

  map: {
    // MAP lanes and lane connections are defined here.
  },

  spat: {
    messageInterval: 0.1,
    movements: [
      {
        name: "Northbound Through",
        signalGroup: 1,
        phases: [
          { phase: "protected-Movement-Allowed", duration: 10 },
          { phase: "protected-clearance", duration: 5 }
        ]
      }
    ]
  }
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
     * `layerType`: optional enumeration (`LayerType`) with values `none`,
       `mixedContent`, `generalMapData`, `intersectionData`, `curveData`,
       `roadwaySectionData`, `parkingAreaData`, and `sharedLaneData`; the
       enumeration permits additional values through its extension marker
       (`...`)
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
   and subfields) are not being implemnted at this time.<br>

4. Since this generator is focused on intersections, Layer Type will default to
   `intersectionData`. However, the value can be changed via the input JSON5.

5. Since only one MAP message at a time is being generated, Layer ID will always
   be equal to zero.<br>

6. Unlike SPaT messages, MAP messages will not be generated in batches. For the
   current static-map implementation, the top-level `msgIssueRevision` value
   shall remain at zero.

7. Each generated `IntersectionGeometry` shall follow the J2735 field order:

   * `name`: optional `DescriptiveName`, for debug use only
   * `id`: required `IntersectionReferenceID`, consisting of a region ID and
     intersection ID assignment as a globally unique value; this project omits
     the optional `region` component in its initial profile
   * `revision`: required `MsgCount` from 0 through 127
   * `refPoint`: required `Position3D` providing the reference point from which
     subsequent data points are offset until another point is specified
   * `laneWidth`: optional `LaneWidth` used as the reference width for
     subsequent lanes until another width is specified
   * `speedLimits`: optional `SpeedLimitList` providing regulatory speed limits
     for subsequent lanes until another speed is specified; speed values in mph
     shall be converted to m/s as specified by J2735
   * `laneSet`: required `LaneList` containing data for one or more lanes
   * `preemptPriorityData`: optional `PreemptPriorityList` describing supported
     preemption or priority zones
   * `regional`: optional sequence of 1 through 4 regional extensions
     (`RegionalExtension`)
   * `...`: extension point for additional standard fields
   * `roadAuthorityID`: optional `RoadAuthorityID`; mandatory when
     `roadRegulatorID` is set to 0

   Optional fields may be omitted when not supplied. The required `id`,
   `revision`, `refPoint`, and `laneSet` fields shall be present.

8. The MAP format allows for sending multiple intersections' geometry data at
   once. However, this implementation will only allow for one intersection's
   geometry information to be sent per MAP message. Meaning, a new MAP will have
   to be generated for each intersection.

9. For the MAP Intersection Geometry field, the name and intersection reference
   ID shall shared with the SPAT message.

10. Similarly to the top level MAP message, the message count will always be set
    to zero since only one MAP is being generated. 

11. Referece point shall require a longitude and latitude in 1/10th microdegrees
    ranging from -1799999999 to 1800000001. This corresponds to -180 degrees to
    +180 degrees and is the most important section of the MAP message.

12. Elevation is an optional field that requires an integer ranging from -4096
    to 61439. This is in 10cm steps meaning this range is from -409.5m to
    6143.9m. If this field is not supplied by the input JSON5, it is just
    omitted from the message.

13. Lane width shall have a default integer value of 366cm (12ft which is
    typical for highways). The input JSON5 can accept either a different integer
    value in cenimeters from 0 to 32767 or false to omit it from the message.

14. Speed limits shall be omitted from the message.<br>

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
