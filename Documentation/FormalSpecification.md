Formal Specification
====================

> **Draft status:** This specification is evolving alongside the prototype.
> Items marked as future work, open details, or requiring evaluation are not
> settled requirements.

1\. System requirements
-----------------------

| ID    | Requirement                                                                                                                                                                                                                                                                                                                   |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SYS-1 | The system shall parse a JSON5 input file containing the information required to generate MAP and/or SPaT J2735 messages for an intersection.                                                                                                                                                                                 |
| SYS-2 | The JSON5 input format shall be higher level than the ASN.1 definitions.                                                                                                                                                                                                                                                      |
| SYS-3 | One JSON5 configuration shall describe the intersection and contain settings for both message types. Shared intersection identity and timestamp settings shall be defined once. MAP and SPaT data shall remain in their own sections and be handled by separate generation operations; users may generate MAP, SPaT, or both. |
| SYS-4 | The system shall obtain the required SAE J2735 ASN.1 definitions from the USDOT J2735 Python library.                                                                                                                                                                                                                         |
| SYS-5 | The system shall use PyCrate to construct and encode generated messages using the Unaligned Packed Encoding Rules (UPER).                                                                                                                                                                                                     |
| SYS-6 | The system shall provide each resulting encoded message as raw hexadecimal bytes.                                                                                                                                                                                                                                             |

2\. Shared configuration and consistency
----------------------------------------

### 2.1 Configuration shape

The shared JSON5 configuration shall contain the following fields:

| Field               | Type    | Requirement and purpose                                                                                                                                                           |
| ------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `includeTimestamps` | Boolean | Optional; defaults to `true`. Controls timestamp fields in both message types.                                                                                                    |
| `intersection`      | Object  | Shared intersection identity, containing an integer `id` and a string `name`.                                                                                                     |
| `map`               | Object  | MAP-specific geometry, lanes, and lane connections. The detailed MAP input schema remains to be specified. A connection's `signalGroup`, when present, refers to a SPaT movement. |
| `spat`              | Object  | SPaT movement definitions and SPaT-specific settings, described in §3.                                                                                                            |

The input shall not request or supply an intersection `region` value. The
optional `region` component of `IntersectionReferenceID` shall be omitted.

### 2.2 MAP/SPaT consistency

| Value or relationship | Requirement                                                                                                                                                                                                                                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Intersection ID       | The same intersection ID shall be used by MAP and SPaT output for the same intersection.                                                                                                                                                                                                                                                   |
| Signal-group IDs      | Signal-group IDs shall appear in SPaT movement definitions and corresponding MAP lane connections. The generator shall check that each ID used to link a MAP lane connection to a signalized movement is present in both sections. MAP and SPaT movement/lane data remain independently defined in their respective sections.              |
| Timestamps            | MAP and SPaT timestamps shall use a common UTC time basis. For a SPaT batch, the shared start time shall be the MAP timestamp and the timestamp of the first SPaT sample. Subsequent SPaT timestamps shall advance by elapsed simulation time. When `includeTimestamps` is false, optional timestamps shall be omitted from both messages. |
| Other revisions       | MAP geometry revision and SPaT message revision are independent counters.                                                                                                                                                                                                                                                                  |

These are the cross-message values required to agree in the initial profile.

3\. SPaT requirements
---------------------

### 3.1 Message structure

Each output line shall encode a complete top-level J2735 `SPAT` data frame,
including its `intersections` list. For this project, that list shall contain
the configured intersection; output shall not encode an `IntersectionState` by
itself.

| ASN.1 field                  | Type and constraints                                            | Requirement                                                                                                                      |
| ---------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `SPAT.intersections`         | `IntersectionState` list, 1 to 32 entries                       | Required. The project's output contains the configured intersection.                                                             |
| `SPAT.timeStamp`             | Optional `MinuteOfTheYear` integer                              | Populated when timestamps are enabled.                                                                                           |
| `SPAT.name`                  | Optional `DescriptiveName` string                               | Optional.                                                                                                                        |
| `IntersectionState.id`       | `IntersectionReferenceID` containing an integer intersection ID | Required. The optional region integer is omitted.                                                                                |
| `IntersectionState.revision` | `MsgCount`, 0 through 127                                       | Required and managed automatically: start at 0, increment per SPaT message, then wrap from 127 to 0. Do not provide it in JSON5. |
| `IntersectionState.status`   | 16-bit `IntersectionStatusObject` bit string                    | Optional in JSON5; defaults to `(0, 16)`, meaning 16 zero bits. Input syntax is `"0bxxxxxxxxxxxxxxxx"` or `"0x1234"`.            |
| `IntersectionState.states`   | `MovementList`                                                  | Required; contains movement-state records described below.                                                                       |
| `IntersectionState.name`     | Optional `DescriptiveName` string                               | Optional.                                                                                                                        |

### 3.2 SPaT input fields

The `spat` object shall contain:

| Field             | Type                       | Requirement and default                                                                      |
| ----------------- | -------------------------- | -------------------------------------------------------------------------------------------- |
| `movements`       | Array of movement objects  | Required. Each movement has a `name`, a stable `signalGroup`, and an ordered `phases` array. |
| `messageInterval` | Positive number of seconds | Optional; defaults to `0.1` seconds. `0.1` seconds is the shortest supported interval.       |
| `status`          | String                     | Optional; defaults to the 16-bit all-zero bit string `(0, 16)`.                              |

Each movement object shall contain:

| Field         | ASN.1 mapping       | Requirement                                                                                                                    |
| ------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `name`        | `DescriptiveName`   | String; optional in the ASN.1 structure.                                                                                       |
| `signalGroup` | `SignalGroupID`     | Integer required in JSON5 and stable for the movement across all phase states. Use one of the six initial-profile IDs in §3.3. |
| `phases`      | `MovementEventList` | Ordered array of phase intervals for the movement.                                                                             |

Each phase interval shall contain a `phase` enum value and a positive `duration`
in seconds. Duration shall be no more than 3600 seconds. Supported phase enum
names and their initial-profile support are listed in §3.4.

### 3.3 Initial signal-group profile

Signal-group IDs identify movements and do not change when the active phase
changes. A matching ID in a MAP lane connection refers to its SPaT movement.
These assignments are a project-level mapping, not a universal numbering
prescribed by J2735.

| Signal group | Movement             |
| ------------ | -------------------- |
| `1`          | Northbound through   |
| `2`          | Southbound through   |
| `3`          | Eastbound through    |
| `4`          | Westbound through    |
| `5`          | Northbound left turn |
| `6`          | Southbound left turn |

Other signal-group assignments are not supported by the initial profile.

### 3.4 Phase states and timing

The event state maps to the ASN.1 `MovementPhaseState` enumeration. Each event's
`timing` is a `TimeChangeDetails` record. Initially, only `minEndTime` is
supported: it is an integer `TimeMark` from 0 through 36111 and marks the end of
the current phase interval. Other timing fields may be added later.

| Value | ASN.1 enum name               | Meaning / initial-profile support                |
| ----- | ----------------------------- | ------------------------------------------------ |
| 0     | `unavailable`                 | Not supported in the initial project profile.    |
| 1     | `dark`                        | Signal unlit.                                    |
| 2     | `stop-Then-Proceed`           | Stop, then proceed when safe.                    |
| 3     | `stop-And-Remain`             | Stop.                                            |
| 4     | `pre-Movement`                | Stop and prepare to proceed.                     |
| 5     | `permissive-Movement-Allowed` | Proceed, yielding to conflicting traffic.        |
| 6     | `protected-Movement-Allowed`  | Protected right-of-way.                          |
| 7     | `permissive-clearance`        | Prepare to stop; clear if unable to stop safely. |
| 8     | `protected-clearance`         | Clear in the indicated direction.                |
| 9     | `caution-Conflicting-Traffic` | Proceed with caution; traffic may conflict.      |

Not every phase applies to every region or operating mode. Additional SPaT
fields defined by the applicable SAE J2735 ASN.1 specification shall be
evaluated for inclusion as implementation expands.

> **Open detail:** The phase schedule shall allow simplified names with `green`
> corresponding to phase 6, `red` to phase 3, and `yellow` to phase 8. This
> mapping is marked for verification in the source specification.

### 3.5 Batch generation

The generator shall support batch output to a text file, with one hex-encoded
UPER message per line. Messages shall represent evenly spaced sample times; the
generator shall not need to wait in real time while creating the file.

| Batch rule         | Requirement                                                                                                                                                                       |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Batch length       | Sum of the ordered phase durations. For example, 10 seconds of green followed by 5 seconds of yellow produces a 15-second batch: 150 messages at the default 0.1-second interval. |
| Movement alignment | Durations for every movement shall sum to the same batch length and be exact multiples of `messageInterval`.                                                                      |
| Sample times       | Sample at 0, `messageInterval`, 2 × `messageInterval`, and so on, stopping before the batch end.                                                                                  |
| Message contents   | Each message shall contain the active phase for every movement.                                                                                                                   |
| `minEndTime`       | Marks the phase interval's end in tenths of a second within the current or next UTC hour.                                                                                         |

Use the shared UTC start time plus elapsed simulation time for SPaT timestamps
and timing. When MAP and SPaT are generated together, the MAP timestamp shall
correspond to the shared start time, which is also the timestamp of SPaT's first
sample.

### 3.6 Timestamps, defaults, and additional fields

When `includeTimestamps` is `true`, populate available timestamp fields from the
shared UTC start time and simulation time. The fields are:

| Message field                 | ASN.1 type / timestamp basis |
| ----------------------------- | ---------------------------- |
| MAP `timeStamp`               | `MinuteOfTheYear`            |
| SPaT top-level `timeStamp`    | `MinuteOfTheYear`            |
| SPaT intersection `moy`       | `MinuteOfTheYear`            |
| SPaT intersection `timeStamp` | `DSecond`                    |

The MAP timestamp shall agree to the minute with the first SPaT sample when both
messages are generated for the same batch. When `includeTimestamps` is false,
omit optional timestamps from both messages. Defaults for fields that do not
require a user-provided value shall be documented; for SPaT, status defaults to
a 16-bit all-zero bit string.

### 3.7 Example JSON5 input

```json5
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

4\. MAP requirements
--------------------

### 4.1 Top-level message

The system shall convert the completed `MapData` value to UPER-encoded bytes.
The top-level `MapData` fields are:

| Field              | ASN.1 type and constraints          | Requirement                                                                                                                                                                                                                                                                                                    |
| ------------------ | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `timeStamp`        | Optional `MinuteOfTheYear` integer  | Populated when timestamps are enabled.                                                                                                                                                                                                                                                                         |
| `msgIssueRevision` | `MsgCount`, 0 through 127           | Required; remains zero for the current static-map implementation.                                                                                                                                                                                                                                              |
| `layerType`        | Optional `LayerType` enumeration    | Defaults to `intersectionData`; may be changed through JSON5. Defined values include `none`, `mixedContent`, `generalMapData`, `intersectionData`, `curveData`, `roadwaySectionData`, `parkingAreaData`, and `sharedLaneData`; the enumeration permits additional values through its extension marker (`...`). |
| `layerID`          | Optional `LayerID` integer          | Always zero because only one MAP message at a time is generated.                                                                                                                                                                                                                                               |
| `intersections`    | Optional `IntersectionGeometryList` | Contains the intersection geometry. This implementation supports one intersection per MAP message.                                                                                                                                                                                                             |
| `regional`         | Optional `RegionalExtension` list   | Optional.                                                                                                                                                                                                                                                                                                      |
| `roadSegments`     | Optional `RoadSegmentList`          | Not supported. Road-segment fields and subfields are not being implemented at this time.                                                                                                                                                                                                                       |
| `dataParameters`   | Optional `DataParameters`           | Not supported.                                                                                                                                                                                                                                                                                                 |
| `restrictionList`  | Optional `RestrictionClassList`     | Not supported.                                                                                                                                                                                                                                                                                                 |

MAP messages are not generated in batches. For the current static-map
implementation, top-level `msgIssueRevision` shall remain zero.

### 4.2 Intersection geometry

Each generated `IntersectionGeometry` shall follow the J2735 field order:

| Field                 | ASN.1 type and constraints          | Requirement                                                                                                                                                                                                                                                                                           |
| --------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                | Optional `DescriptiveName`          | Optional; for debug use only.                                                                                                                                                                                                                                                                         |
| `id`                  | Required `IntersectionReferenceID`  | Consists of a region ID and intersection ID assignment as a globally unique value; the initial project profile omits the optional `region` component. The name and intersection reference ID shall be shared with the SPaT message.                                                                   |
| `revision`            | Required `MsgCount`, 0 through 127  | Required; the message count remains zero for the current implementation, which generates one MAP at a time.                                                                                                                                                                                           |
| `refPoint`            | Required `Position3D`               | Reference point from which subsequent data points are offset until another point is specified. Requires longitude and latitude in 1/10th microdegrees, ranging from -1799999999 to 1800000001. This corresponds to -180 degrees to +180 degrees and is the most important section of the MAP message. |
| `laneWidth`           | Optional `LaneWidth`                | Reference width for subsequent lanes until another width is specified. Defaults to 366 cm (12 ft, typical for highways). JSON5 may provide an integer number of centimeters from 0 through 32767, or `false` to omit it.                                                                              |
| `speedLimits`         | Optional `SpeedLimitList`           | Speed limits are omitted from the message. If supported later, speed values in mph shall be converted to m/s as specified by J2735.                                                                                                                                                                   |
| `laneSet`             | Required `LaneList`                 | Contains data for one or more lanes.                                                                                                                                                                                                                                                                  |
| `preemptPriorityData` | Optional `PreemptPriorityList`      | Describes supported preemption or priority zones.                                                                                                                                                                                                                                                     |
| `regional`            | Optional 1-to-4 regional extensions | `RegionalExtension` sequence.                                                                                                                                                                                                                                                                         |
| `...`                 | Extension point                     | Additional standard fields.                                                                                                                                                                                                                                                                           |
| `roadAuthorityID`     | Optional `RoadAuthorityID`          | Mandatory when `roadRegulatorID` is set to 0.                                                                                                                                                                                                                                                         |

Optional fields may be omitted when not supplied. The required `id`, `revision`,
`refPoint`, and `laneSet` fields shall be present.

### 4.3 Geometry values and scope

| Item               | Requirement                                                                                                                                                                                    |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Intersection count | Although MAP supports multiple intersection geometries, this implementation shall include only one intersection's geometry per MAP message. Generate a separate MAP for each intersection.     |
| Elevation          | Optional integer from -4096 through 61439 in 10 cm steps, corresponding to -409.5 m through 6143.9 m. Omit it when not supplied in JSON5.                                                      |
| Speed limits       | Omitted from the message.                                                                                                                                                                      |
| MAP revisions      | Top-level message revision and intersection geometry revision remain zero for the current static-map implementation. MAP geometry revision and SPaT message revision are independent counters. |

### 4.4 Lane set

The `LaneList` contains `GenericLane` records. Each record has the following
fields in ASN.1 order:

| ASN.1 field       | Presence and type                                      | Description                                                                                                                                                                |
| ----------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `laneID`          | Required `LaneID`                                      | Unique ID assigned to this lane object.                                                                                                                                    |
| `name`            | Optional `DescriptiveName`                             | Often used for debugging; may also name pedestrian crossings.                                                                                                              |
| `ingressApproach` | Optional `ApproachID`                                  | Inbound approach to which this lane belongs.                                                                                                                               |
| `egressApproach`  | Optional `ApproachID`                                  | Outbound approach to which this lane belongs.                                                                                                                              |
| `laneAttributes`  | Required `LaneAttributes`                              | Lane-wide attributes: direction of use, geometric co-sharing, and attributes for the selected lane type. These apply along the entire lane.                                |
| `maneuvers`       | Optional `AllowedManeuvers`                            | Maneuvers permitted from this lane.                                                                                                                                        |
| `nodeList`        | Required `NodeListXY`                                  | Lane spatial path and path attributes. These attributes may vary along the lane.                                                                                           |
| `connectsTo`      | Optional `ConnectsToList`                              | Connections to other lanes, including the signal-group ID for each connection when applicable.                                                                             |
| `overlays`        | Optional `OverlayLaneList`                             | Lanes whose paths run on top of this lane's path rather than merely crossing it. An overlay may apply to parallel lanes without repeating the list for each `GenericLane`. |
| `regional`        | Optional sequence of 1 to 4 `RegionalExtension` values | Regional extensions constrained by `Reg-GenericLane`.                                                                                                                      |
| `...`             | ASN.1 extension point                                  | Allows extension additions.                                                                                                                                                |

Rather than requiring MAP lane info to manually specified for every field,
several preset lane layouts will be provided which can be selected when encoding
a message. The sections below detail necessary configurations for various
intersection layouts.

### 4.4.1 Basic Four Way Intersection w/o Left Turn

This table displays the configuration to be used with a basic four way
intersection. Any optional fields not included, are being omitted. A basic four
way will consist of eight lanes.

<table
  style="border-collapse: collapse; width: 97.5949%; border-width: 1px; border-style: dotted;"
  border="1"
>
  <colgroup>
    <col style="width: 49.9352%;">
    <col style="width: 49.9352%;">
  </colgroup>
  <tbody>
    <tr>
      <td><strong>ASN.1 Field</strong><br></td>
      <td><strong>Value</strong><br></td>
    </tr>
    <tr>
      <td><code>laneID</code><br></td>
      <td>
        Lane ID will be assigned starting from zero in the order of created lanes for the intersection.
      </td>
    </tr>
    <tr>
      <td><code>LaneAttributes.directionalUse</code><br></td>
      <td>
        Directional use is a bitstring of size 2, where bit 0 represents an ingressPath and bit 1 represents an egressPath. All lanes approaching the intersection will be defined as ingress and all lanes leaving will be defined as egress.
      </td>
    </tr>
    <tr>
      <td><code>LaneAttributes.sharedWith</code></td>
      <td>
        Shared with is a bitstring of size 10 where each bit represents a different sharing option. For this application, all bits will be set to zero indicating no lane sharing.
      </td>
    </tr>
    <tr>
      <td><code>LaneAttributes.laneType</code></td>
      <td>
        Lane type is a choice. For this application all lanes used will be selected as vehicles. Once a type is chosen, a bitstring of size 8 is used to select attributes. For a standard intersection, all bits will be zero.
      </td>
    </tr>
    <tr>
      <td><code>manuevers</code><br></td>
      <td>Future Work</td>
    </tr>
    <tr>
      <td><code>nodeList</code><br></td>
      <td>
        Node list provides spatial information for all lane approaches. Due to complexity, a standardized approach is used for all intersections. This is expanded upon in a later section.
      </td>
    </tr>
    <tr>
      <td><code>connectsTo</code><br></td>
      <td>Future Work</td>
    </tr>
  </tbody>
</table>

5\. SPaT debugging decoder
--------------------------

The system shall provide a decoder for raw hexadecimal J2735 `SPAT` messages
encoded using UPER.

| ID    | Requirement                                                                                                                                                                                                                                                                                                                      |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DEC-1 | Accept either a hexadecimal message supplied directly as a command-line argument or a text file containing one hexadecimal message per line.                                                                                                                                                                                     |
| DEC-2 | Ignore whitespace within a message and skip blank lines in an input file.                                                                                                                                                                                                                                                        |
| DEC-3 | Print a compact, human-readable terminal summary with one line per decoded message. Each summary shall identify the source line and message time, then show each movement's name, signal state, and `minEndTime` in a readable time format.                                                                                      |
| DEC-4 | Write complete decoded ASN.1 values as indented JSON to a separate file. The JSON document shall contain all successfully decoded messages in input order. Each run shall overwrite the selected output file; users who want to keep an earlier result shall save a separate copy.                                               |
| DEC-5 | For text-file input, default the JSON output path to `output/<input-file-name>_decoded.json`, where `<input-file-name>` is the input file name without its extension. The user may provide a different JSON output path. For a hexadecimal message supplied directly on the command line, default to `output/decoded_spat.json`. |
| DEC-6 | When decoding a file, process every nonblank line independently and identify each terminal summary by its source line number.                                                                                                                                                                                                    |
| DEC-7 | Report invalid hexadecimal data or messages that cannot be decoded as a J2735 `SPAT` UPER message. For file input, include the source line number in the error. Include only successfully decoded messages in the JSON output file.                                                                                              |
| DEC-8 | Initially support raw top-level `SPAT` messages emitted by this project. Support for other J2735 message types or framed transport data is future work.                                                                                                                                                                          |

This decoder is primarily for debugging at this stage.

6\. Implementation notes
------------------------

The provided USDOT library can be imported as:

```python
import j2735_202409.j2735_202409 as j2735
```

A SPaT object can be created with `SPAT = j2735.SPAT`. The following is an
exploratory `IntersectionState` value only. It is not a complete output message;
batch output shall place the intersection state in the top-level
`SPAT.intersections` list.

```python
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

7\. Development tools and libraries
-----------------------------------

| Purpose                              | Tool                                                                                    |
| ------------------------------------ | --------------------------------------------------------------------------------------- |
| Package manager                      | `uv`                                                                                    |
| Formatter                            | `ruff`                                                                                  |
| ASN.1 construction and UPER encoding | PyCrate                                                                                 |
| JSON5 parsing                        | PyJson5                                                                                 |
| SAE J2735 ASN.1 definitions          | [USDOT J2735 Python library](https://github.com/usdot-fhwa-stol/j2735_202409/tree/main) |
