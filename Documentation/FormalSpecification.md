uFormal Specification
=====================

> <strong>Draft status:</strong> This specification is evolving alongside the
> prototype. Items marked as future work, open details, or requiring evaluation
> are not settled requirements.

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

| Field               | Type    | Requirement and purpose                                                                                                                                                                              |
| ------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `includeTimestamps` | Boolean | Optional; defaults to `true`. Controls timestamp fields in both message types.                                                                                                                       |
| `intersection`      | Object  | Shared intersection identity, containing an integer `id` and a string `name`.                                                                                                                        |
| `map`               | Object  | MAP-specific geometry, lanes, and lane connections. The initial layout and its input fields are defined in §2.1.1 and §4.4.1. A connection's `signalGroup`, when present, refers to a SPaT movement. |
| `spat`              | Object  | SPaT movement definitions and SPaT-specific settings, described in §3.                                                                                                                               |

The input shall not request or supply an intersection `region` value. The
optional `region` component of `IntersectionReferenceID` shall be omitted.

### 2.1.1 MAP input fields

The initial MAP profile shall accept the following fields inside `map`:

| Field                     | Type                                     | Requirement and purpose                                                                                                                                                                          |
| ------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `layout`                  | String                                   | Required. The initial supported value is `fourWayNoLeftTurn`, defined in §4.4.1.                                                                                                                 |
| `refPoint`                | Object                                   | Required. Contains `latitude` and `longitude` in decimal degrees using the WGS-84 datum. Optional `elevation` is in meters. The reference point is the center of the intersection layout.        |
| `laneWidthCm`             | Integer from 1 through 32767, or `false` | Optional; defaults to 366 cm. Sets the lane width and the lateral lane-center offset. `false` omits the MAP `laneWidth` field while the layout still uses the default 366 cm width for geometry. |
| `intersectionHalfExtentM` | Positive number                          | Optional; defaults to 10 m. Distance from the reference point to each straight lane segment's endpoint at the intersection boundary.                                                             |
| `approachExtentM`         | Positive number                          | Optional; defaults to 30 m. Distance from the reference point to each lane segment's outer endpoint. Must be greater than `intersectionHalfExtentM`.                                             |
| `layerType`               | String                                   | Optional; defaults to `intersectionData`. Supported values are the non-extension values listed in §4.1.                                                                                          |

Latitude shall be within -90 to +90 degrees. Longitude shall be within
-179.9999999 to +180 degrees, matching the representable non-sentinel range. The
encoder shall convert each to J2735 1/10th-microdegree units by multiplying by
10,000,000 and rounding to the nearest integer, with exact halfway cases rounded
away from zero. Elevation, when supplied, shall be within the representable
non-sentinel range of -409.5 m through 6143.9 m and shall be converted to 0.1 m
units using the same rounding rule. The encoder shall reject out-of-range
coordinates and geometry parameters that cannot be represented by the selected
node-offset encoding.

### 2.2 MAP/SPaT consistency

| Value or relationship | Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Intersection ID       | The same intersection ID shall be used by MAP and SPaT output for the same intersection.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Signal-group IDs      | A signal group used by a MAP lane connection shall be present in the SPaT movements, and the generator shall check this relationship. In the `fourWayNoLeftTurn` layout, through groups 1 through 4 may be linked; signalized right turns and left-turn links are unsupported. When MAP and SPaT are generated together using this layout, the SPaT configuration shall not define movements for unsupported signalized turns. MAP and SPaT movement/lane data remain independently defined in their respective sections. |
| Timestamps            | MAP and SPaT timestamps shall use a common UTC time basis. For a SPaT batch, the shared start time shall be the MAP timestamp and the timestamp of the first SPaT sample. Subsequent SPaT timestamps shall advance by elapsed simulation time. When `includeTimestamps` is false, optional timestamps shall be omitted from both messages.                                                                                                                                                                                |
| Other revisions       | MAP geometry revision and SPaT message revision are independent counters.                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

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
    layout: "fourWayNoLeftTurn",
    // Illustrative coordinates; replace with the surveyed intersection center.
    refPoint: { latitude: 38.9564590, longitude: -77.1502970 },
    laneWidthCm: 366,
    intersectionHalfExtentM: 10,
    approachExtentM: 30
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

| Field              | ASN.1 type and constraints          | Requirement                                                                                                                                                                                                                                                                                             |
| ------------------ | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `timeStamp`        | Optional `MinuteOfTheYear` integer  | Populated when timestamps are enabled.                                                                                                                                                                                                                                                                  |
| `msgIssueRevision` | `MsgCount`, 0 through 127           | Required; remains zero for the current static-map implementation.                                                                                                                                                                                                                                       |
| `layerType`        | Optional `LayerType` enumeration    | Defaults to `intersectionData`; may be changed through `map.layerType`. Supported values are `none`, `mixedContent`, `generalMapData`, `intersectionData`, `curveData`, `roadwaySectionData`, `parkingAreaData`, and `sharedLaneData`. ASN.1 extension values are not supported by the initial profile. |
| `layerID`          | Optional `LayerID` integer          | Always zero because only one MAP message at a time is generated.                                                                                                                                                                                                                                        |
| `intersections`    | Optional `IntersectionGeometryList` | ASN.1-optional, but required by this profile and contains exactly one `IntersectionGeometry`.                                                                                                                                                                                                           |
| `regional`         | Optional `RegionalExtension` list   | Optional.                                                                                                                                                                                                                                                                                               |
| `roadSegments`     | Optional `RoadSegmentList`          | Not supported. Road-segment fields and subfields are not being implemented at this time.                                                                                                                                                                                                                |
| `dataParameters`   | Optional `DataParameters`           | Not supported.                                                                                                                                                                                                                                                                                          |
| `restrictionList`  | Optional `RestrictionClassList`     | Not supported.                                                                                                                                                                                                                                                                                          |

MAP messages are not generated in batches. For the current static-map
implementation, top-level `msgIssueRevision` shall remain zero.

### 4.2 Intersection geometry

Each generated `IntersectionGeometry` shall follow the J2735 field order:

| Field                 | ASN.1 type and constraints          | Requirement                                                                                                                                                                                                                                                               |
| --------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                | Optional `DescriptiveName`          | Optional; for debug use only.                                                                                                                                                                                                                                             |
| `id`                  | Required `IntersectionReferenceID`  | Uses the shared intersection ID. The initial project profile omits the optional `region` component, so uniqueness is limited to the deployment context that assigns the ID. The name and intersection reference ID shall be shared with the SPaT message.                 |
| `revision`            | Required `MsgCount`, 0 through 127  | Required; the message count remains zero for the current implementation, which generates one MAP at a time.                                                                                                                                                               |
| `refPoint`            | Required `Position3D`               | Reference point from which subsequent data points are offset until another point is specified. JSON5 supplies decimal-degree latitude and longitude, plus optional elevation in meters, through `map.refPoint`; §2.1.1 defines conversion and valid input ranges.         |
| `laneWidth`           | Optional `LaneWidth`                | Reference width for subsequent lanes until another width is specified. Defaults to 366 cm. JSON5 may provide a positive integer number of centimeters through `map.laneWidthCm`, or `false` to omit it. When omitted, the layout uses the default width for its geometry. |
| `speedLimits`         | Optional `SpeedLimitList`           | Speed limits are omitted from the message. If supported later, speed values in mph shall be converted to m/s as specified by J2735.                                                                                                                                       |
| `laneSet`             | Required `LaneList`                 | Contains data for one or more lanes.                                                                                                                                                                                                                                      |
| `preemptPriorityData` | Optional `PreemptPriorityList`      | Describes supported preemption or priority zones.                                                                                                                                                                                                                         |
| `regional`            | Optional 1-to-4 regional extensions | `RegionalExtension` sequence.                                                                                                                                                                                                                                             |
| `...`                 | Extension point                     | Additional standard fields.                                                                                                                                                                                                                                               |
| `roadAuthorityID`     | Optional `RoadAuthorityID`          | Mandatory when `roadRegulatorID` is set to 0.                                                                                                                                                                                                                             |

Optional fields may be omitted when not supplied. The required `id`, `revision`,
`refPoint`, and `laneSet` fields shall be present.

### 4.3 Geometry values and scope

| Item               | Requirement                                                                                                                                                                                    |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Intersection count | The initial profile shall include exactly one intersection geometry per MAP message.                                                                                                           |
| Elevation          | Optional JSON5 input in meters, converted to J2735 0.1 m units. Omit it when not supplied. The `-4096` ASN.1 value is reserved as unavailable and shall not be used for a supplied elevation.  |
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

The initial profile generates lane information from a named layout and its
geometry parameters. Additional layouts may be defined later.

### 4.4.1 Four-way, single-lane, no-left-turn layout

The `fourWayNoLeftTurn` layout has one ingress lane and one egress lane on each
cardinal approach, for eight `GenericLane` records. It allows through and right
turn connections and has no left-turn connections. Right turns are unsignalized
in the initial profile. This describes movement connectivity; right-turn curves
through the intersection box are not separately encoded.

Approach IDs are fixed as north = 1, east = 2, south = 3, and west = 4. Lane IDs
are fixed in compass order, with the ingress lane followed by the egress lane on
each approach:

| Lane ID | Lane          | Travel direction | Approach field       | Centerline path in local east/north coordinates |
| ------- | ------------- | ---------------- | -------------------- | ----------------------------------------------- |
| 1       | North ingress | South            | `ingressApproach: 1` | `x = -w/2`, from `y = +A` to `y = +H`           |
| 2       | North egress  | North            | `egressApproach: 1`  | `x = +w/2`, from `y = +H` to `y = +A`           |
| 3       | East ingress  | West             | `ingressApproach: 2` | `y = +w/2`, from `x = +A` to `x = +H`           |
| 4       | East egress   | East             | `egressApproach: 2`  | `y = -w/2`, from `x = +H` to `x = +A`           |
| 5       | South ingress | North            | `ingressApproach: 3` | `x = +w/2`, from `y = -A` to `y = -H`           |
| 6       | South egress  | South            | `egressApproach: 3`  | `x = -w/2`, from `y = -H` to `y = -A`           |
| 7       | West ingress  | East             | `ingressApproach: 4` | `y = -w/2`, from `x = -A` to `x = -H`           |
| 8       | West egress   | West             | `egressApproach: 4`  | `y = +w/2`, from `x = -H` to `x = -A`           |

Here `w` is the configured lane width in meters (3.66 m when omitted), `H` is
`intersectionHalfExtentM` (10 m by default), and `A` is `approachExtentM` (30 m
by default). `A` shall be greater than `H`. Each lane has two nodes at the
listed endpoints. Lane IDs 1 through 8 are stable project assignments and are
unique within this intersection.

All lanes use the vehicle `laneType` choice with its eight-bit attribute string
set to zero, and a ten-bit `sharedWith` string set to zero. Ingress lanes set
the `ingressPath` directional-use bit; egress lanes set the `egressPath` bit.
Ingress lanes permit straight. The encoder shall omit left-turn maneuvers and
connections.

The required initial connections are:

| Ingress lane | Destination lane | Maneuver | `signalGroup`          |
| ------------ | ---------------- | -------- | ---------------------- |
| 1            | 6                | Through  | 2 (southbound through) |
| 3            | 8                | Through  | 4 (westbound through)  |
| 5            | 2                | Through  | 1 (northbound through) |
| 7            | 4                | Through  | 3 (eastbound through)  |

Each connection shall reference an existing egress lane. Through-connection
signal groups shall also be defined in the SPaT movements, as required by §2.2.
The `connectingLane.maneuver` and ingress lane `maneuvers` fields shall identify
the listed straight and right movements using the corresponding J2735
`AllowedManeuvers` bits.

### 4.5 Node List<br>

The initial profile uses a two-node straight centerline for each approach and
egress lane. Each lane has its own node list describing its centerline. All lane
node lists use the same intersection reference point; the first node is relative
to that point, and each later node is relative to the previous node in that
lane. Other lane geometries may be added later.

The `nodeList` attribute consists of a choice between a `nodes` option, which
encodes points using XY offsets, and a `computed` option, which uses other lane
information. This implementation will use the `nodes` option.

`nodes` is a sequence of 2 to 63 `NodeXY` values. For the four-way layout, the
encoder shall use two nodes per lane at the endpoints listed in §4.4.1, ordered
in the direction of travel.

Each `NodeXY` has a `delta` field and an optional `attributes` field. This
implementation will omit `attributes` and use only `delta`.

Each `delta` is represented as a NodeOffsetPointXY choice using ASN.1. This
implementation will use `node-XY4` (Node-XY-26b). This corresponds with a 26 bit
node type, which supports offsets for nodes up to 40.96 m from the previous
point. Offsets use 1 cm units and can be positive or negative.

#### 4.5.1 Calculating lane offsets

The layout preset determines the start and end points of each lane centerline,
including the lateral position of each lane. The encoder converts those points
to offsets; users do not enter every encoded offset manually. Each lane is
calculated independently, and all lanes are positioned relative to the shared
intersection reference point. Geometry parameters shall be rejected if any
resulting offset cannot be represented by the selected `node-XY4` encoding.

For calculation, represent each desired point as an east-west coordinate `east`
and a north-south coordinate `north`, in meters relative to the intersection
reference point. Positive `east` is east and positive `north` is north. For the
first node, the previous point is the intersection reference point (0, 0). For
each later node, the previous point is the preceding node in the same lane. The
encoded values are:

```text
x = round(100 × (east_current − east_previous))
y = round(100 × (north_current − north_previous))
```

The factor of 100 converts meters to centimeters. Round to the nearest
centimeter, with exact halfway cases rounded away from zero. For example, a lane
whose first node is 5 m west and 1 m south of the intersection reference point
has `x = -500` and `y = -100`. If its next node is 10 m east and 1 m south of
the reference point, that node is encoded as `x = +1500` and `y = 0`, because
its offset is measured from the first node. Each adjacent lane has its own
points and offsets, even though the lanes share the same intersection reference
point.

<p><br></p>

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

6\. Error Handling and User Friendliness
----------------------------------------

The requirements in this section apply to the message generators and the SPaT
decoder. Where §5 defines more specific decoder behavior, §5 takes precedence.

### 6.1 Input validation and diagnostics

| ID    | Requirement                                                                                                                                                                                                                                       |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ERR-1 | Before generating output, validate the JSON5 syntax, document shape, required fields, field types and ranges, supported values, timing constraints, and applicable MAP/SPaT relationships. Do not begin message generation when validation fails. |
| ERR-2 | For a configuration error, identify the input file and the relevant JSON field path whenever available (for example, `spat.movements[1].phases[0].duration`). For a JSON5 syntax error, report the line and column when the parser provides them. |
| ERR-3 | Explain what is invalid and what kind of value is expected. User-facing diagnostics shall use configuration and command-line terms rather than requiring users to interpret ASN.1 or PyCrate internals.                                           |
| ERR-4 | Apply a documented default only when its field is omitted. A present field with an invalid type or value shall be reported as an error; it shall not be silently coerced, clamped, or replaced with a default.                                    |
| ERR-5 | For expected input, decoding, and file-access errors, print a concise diagnostic and exit with a nonzero status. Do not print a Python traceback for these errors.                                                                                |

### 6.2 Command-line and output behavior

| ID    | Requirement                                                                                                                                                                                                                                                                                                                         |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ERR-6 | Each command-line entry point shall provide `--help` output describing its inputs, outputs, and available options.                                                                                                                                                                                                                  |
| ERR-7 | File-access diagnostics shall identify the affected path and whether the operation was reading input or writing output. A success message shall be printed only after the requested output has been written successfully.                                                                                                           |
| ERR-8 | The generator shall validate the configuration before creating or truncating its destination file. It shall write generated output to a temporary file and replace the requested destination only after generation and writing succeed. On failure, it shall exit with a nonzero status and preserve any existing destination file. |
| ERR-9 | The generator shall make its destination-file overwrite behavior clear and shall not require interactive confirmation, so it can be used in scripts. The decoder's JSON overwrite and partial-decode behavior is specified in §5.                                                                                                   |

The terminal output shall remain readable when a file contains multiple
messages. Decoder summaries and per-line error reporting are specified in §5.
The command-line tools do not require a graphical interface in the initial
profile.

7\. Implementation notes
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

8\. Development tools and libraries
-----------------------------------

| Purpose                              | Tool                                                                                    |
| ------------------------------------ | --------------------------------------------------------------------------------------- |
| Package manager                      | `uv`                                                                                    |
| Formatter                            | `ruff`                                                                                  |
| ASN.1 construction and UPER encoding | PyCrate                                                                                 |
| JSON5 parsing                        | PyJson5                                                                                 |
| SAE J2735 ASN.1 definitions          | [USDOT J2735 Python library](https://github.com/usdot-fhwa-stol/j2735_202409/tree/main) |
