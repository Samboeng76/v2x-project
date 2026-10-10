# MAP ASN.1 Structure Notes

These notes expand the generated J2735 ASN.1 definitions in the project's
checked-in 2024-09 package. They are an implementation aid, not a replacement
for the applicable SAE J2735 specification. The package exposes the top-level
type as `MapData` in the `MapData` module.

MAP carries geographic road information. Its primary use is to describe one or
more intersections and their lane geometry. Lane IDs and signal group IDs let
other messages, especially SPaT, refer to the applicable lanes and movements.

## Structure

```text
MapData
|-- timeStamp: MinuteOfTheYear (optional; 0..527040 minutes)
|-- msgIssueRevision: MsgCount (0..127)
|-- layerType: LayerType (optional)
|-- layerID: LayerID (optional; 0..100)
|-- intersections: IntersectionGeometryList (optional; 1..32)
|   `-- IntersectionGeometry
|       |-- name: DescriptiveName (optional; IA5String, up to 63 characters)
|       |-- id: IntersectionReferenceID
|       |   |-- region: RoadRegulatorID (optional)
|       |   `-- id: IntersectionID (0..65535)
|       |-- revision: MsgCount (0..127)
|       |-- refPoint: Position3D
|       |   |-- lat: Latitude (-900000000..900000001)
|       |   |-- long: Longitude (-1799999999..1800000001)
|       |   |-- elevation: Elevation (-4096..61439, optional)
|       |   `-- regional (optional)
|       |-- laneWidth: LaneWidth (0..32767 cm, optional)
|       |-- speedLimits: SpeedLimitList (optional)
|       |-- laneSet: LaneList (1..255)
|       |   `-- GenericLane
|       |       |-- laneID: LaneID (0..255)
|       |       |-- name: DescriptiveName (optional)
|       |       |-- ingressApproach: ApproachID (optional)
|       |       |-- egressApproach: ApproachID (optional)
|       |       |-- laneAttributes: LaneAttributes
|       |       |   |-- directionalUse: LaneDirection (BIT STRING)
|       |       |   |-- sharedWith: LaneSharing (BIT STRING)
|       |       |   |-- laneType: LaneTypeAttributes (CHOICE)
|       |       |   `-- regional (optional)
|       |       |-- maneuvers: AllowedManeuvers (12-bit BIT STRING, optional)
|       |       |-- nodeList: NodeListXY (CHOICE)
|       |       |   |-- nodes: NodeSetXY (2..63 NodeXY entries)
|       |       |   |   `-- NodeXY
|       |       |   |       |-- delta: NodeOffsetPointXY (CHOICE)
|       |       |   |       `-- attributes: NodeAttributeSetXY (optional)
|       |       |   `-- computed: ComputedLane
|       |       |-- connectsTo: ConnectsToList (optional)
|       |       |   `-- Connection
|       |       |       |-- connectingLane: ConnectingLane
|       |       |       |   |-- lane: LaneID
|       |       |       |   `-- maneuver: AllowedManeuvers (optional)
|       |       |       |-- remoteIntersection: IntersectionReferenceID (optional)
|       |       |       |-- signalGroup: SignalGroupID (optional)
|       |       |       |-- userClass: RestrictionClassID (optional)
|       |       |       `-- connectionID: LaneConnectionID (optional)
|       |       |-- overlays: OverlayLaneList (optional)
|       |       `-- regional (optional)
|       |-- preemptPriorityData: PreemptPriorityList (optional)
|       |-- regional (optional)
|       `-- roadAuthorityID: RoadAuthorityID (optional)
|-- roadSegments: RoadSegmentList (optional; 1..32) (Probably Ignoring)
|   `-- RoadSegment
|       |-- name: DescriptiveName (optional)
|       |-- id: RoadSegmentReferenceID
|       |   |-- region: RoadRegulatorID (optional)
|       |   `-- id: RoadSegmentID
|       |-- revision: MsgCount (0..127)
|       |-- refPoint: Position3D
|       |-- laneWidth: LaneWidth (optional)
|       |-- speedLimits: SpeedLimitList (optional)
|       |-- roadLaneSet: RoadLaneSetList (1..255 GenericLane entries)
|       `-- regional (optional)
|-- dataParameters: DataParameters (optional) (Ignoring)
|-- restrictionList: RestrictionClassList (optional) (Probably Ignoring)
`-- regional (optional)
```

The dots in the definitions allow ASN.1 extension additions. `regional` fields
are extension mechanisms whose values depend on the region-specific definitions;
they are not ordinary free-form text fields. The main tree above focuses on the
standard fields used for intersection and road geometry.

## Reference point and coordinates

`refPoint` is the geographic anchor for an `IntersectionGeometry` or
`RoadSegment`. Lane node offsets are built from this anchor. `Position3D` is:

| Field | ASN.1 type and units | Special values |
| --- | --- | --- |
| `lat` | `Latitude`, signed 1/10 microdegrees (0.0000001 degree), relative to the horizontal datum in use | `900000001` means unavailable; normal range is -90 to +90 degrees |
| `long` | `Longitude`, signed 1/10 microdegrees (0.0000001 degree), relative to the horizontal datum in use | `1800000001` means unavailable; normal range is -180 to +180 degrees |
| `elevation` | Optional `Elevation`, 0.1 m increments above or below the reference ellipsoid (typically WGS-84) | `-4096` means unknown; values span -409.5 m to +6143.9 m |
| `regional` | Optional sequence of regional extensions | Interpretation is defined by the applicable regional extension |

For a lane's XY geometry, the reference point and node offsets form a local
coordinate path. In this non-vehicle coordinate frame, positive X points east
and positive Y points north. Do not treat longitude and latitude integer values
as meters; they are angular coordinates. A complete `node-LatLon` alternative
uses absolute longitude and latitude values, while the ordinary XY node
alternatives encode offsets.

## Lane geometry

`LaneList` contains one or more `GenericLane` values. A lane is a map object,
not necessarily a vehicle lane: it can represent a vehicle lane, a crosswalk,
a median, or another lane type. `laneID` is unique within its intersection and
is the index used by lane references and SPaT associations. The ID is not a
physical left-to-right lane number.

`nodeList` is a CHOICE:

| Alternative | Meaning |
| --- | --- |
| `nodes` / `NodeSetXY` | A path made from 2..63 `NodeXY` entries. Each point is an offset from the previous point; the first is based on the intersection `refPoint`. |
| `computed` / `ComputedLane` | A lane path derived from a referenced lane by translating it, optionally rotating or scaling it. The referenced lane's node attributes are reused. |

`NodeXY.delta` is a CHOICE of compact encodings. The `node-XY1` through
`node-XY6` alternatives use signed X/Y offsets with an LSB of 1 cm and increasing
ranges; choose the smallest alternative that can represent the offset.
`node-LatLon` carries absolute `Longitude` and `Latitude`; the regional
alternative is region-defined. The six XY alternatives represent approximately
these maximum absolute offsets from the previous node:

| Alternative | Encoded width | Maximum axis offset |
| --- | ---: | ---: |
| `node-XY1` | 20 bits | 5.11 m |
| `node-XY2` | 22 bits | 10.23 m |
| `node-XY3` | 24 bits | 20.47 m |
| `node-XY4` | 26 bits | 40.95 m |
| `node-XY5` | 28 bits | 81.91 m |
| `node-XY6` | 32 bits | 327.67 m |

`NodeAttributeSetXY`, when present, can attach or change node/path attributes.
It includes optional local attributes, enabled or disabled segment attributes,
data-bearing lane attributes, and width/elevation changes. The `dWidth` and
`dElevation` values use 1 cm steps; they are deltas from the value currently in
effect, and the standard says not to send zero for these fields. Node attributes
can apply only at a node or persist along following segments, depending on the
attribute.

## Lane attributes and connections

`LaneAttributes` identifies direction of use, optional sharing, and a lane type:

| Field | Encoding / interpretation |
| --- | --- |
| `directionalUse` | `LaneDirection` bit string. Its ingress/egress bits indicate allowed travel directions. |
| `sharedWith` | `LaneSharing` bit string describing other user classes sharing the lane. |
| `laneType` | `LaneTypeAttributes` CHOICE, with type-specific attributes for vehicle, crosswalk, bike, sidewalk, median, parking, striping, barrier, or tracked vehicle lanes. |
| `regional` | Optional regional extension. |

`maneuvers` is an optional 12-bit `AllowedManeuvers` bit string. It describes
permitted movements from the lane. `connectsTo` lists lane-to-lane connections.
For an intersection-local connection, `connectingLane.lane` identifies the
destination `LaneID`. `remoteIntersection` identifies a different intersection
when needed. `signalGroup` links the connection to the corresponding SPaT
movement; it is optional in the ASN.1 structure and is omitted for an
unsignalized connection. `connectionID` is an optional connection index.

`SignalGroupID` is a numeric index, not a physical unit: the ASN.1 range is
0..255, zero means unavailable/unknown, and 255 denotes a permanently allowed
movement. Values 1..254 are the ordinary group identifiers. The same group
assignment must be used by the corresponding SPaT movement.

## Other fields and units

| Field | Meaning, constraints, or units |
| --- | --- |
| `timeStamp` | `MinuteOfTheYear`, elapsed minutes of the current year (typically UTC); 527040 is the invalid value. |
| `msgIssueRevision`, `revision` | `MsgCount`, sequence/revision counter 0..127; wraps from 127 to 0. It has no physical unit. |
| `layerType` | Enumeration describing map content type; no unit. |
| `layerID` | Layer index 0..100; no physical unit. |
| `IntersectionID` | Regional intersection index 0..65535; no physical unit. Values 0..255 are reserved for testing. |
| `RoadRegulatorID` | Region/road authority identifier; no physical unit. It combines with the intersection or road segment ID to qualify the reference. |
| `RoadSegmentID` | Road segment index within a region; no physical unit. Unlike an intersection ID, a region may reuse it over time. |
| `ApproachID` | Approach index; no physical unit. It groups lanes into an inbound or outbound approach. |
| `LaneID` | Lane object index 0..255; 0 means unavailable/unknown and 255 is reserved. |
| `LaneWidth` | 0..32767 cm (1 cm per integer step; maximum 327.67 m). Applies as the reference width until changed. |
| `speedLimits` | Optional ITIS speed limit phrase list. Speeds represented by the phrase use the standard's prescribed conversion to m/s; the list may carry code or text alternatives. |
| `signalGroup` | `SignalGroupID`; identifier only, not a unit. See the special values above. |
| `regional` | Optional region-specific extension sequence; no common unit or universal interpretation. |

## Scope for an initial intersection MAP

The most direct starting profile is one `MapData` containing an
`IntersectionGeometry`, its `id`, `revision`, `refPoint`, and `laneSet`. Each
lane needs a unique `laneID`, `laneAttributes`, and `nodeList`. Add
`connectsTo` where lane connectivity and signal group association are needed
for the MAP/SPaT relationship. The remaining top-level fields, road segments,
restriction classes, preemption/priority information, overlays, and regional
extensions can be added when the chosen input model requires them.

The units, ranges, list sizes, and field semantics in these notes follow the
SAE J2735 2024 definitions for MAP and its referenced data elements. See the
[SAE J2735 2024 preview](https://webstore.ansi.org/preview-pages/SAE/preview_J2735_202409.pdf)
and the generated package under `src/j2735_202409` when implementing encoders.
