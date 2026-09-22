
```graphviz
digraph mygraph {
  fontname="Helvetica,Arial,sans-serif"
  node [fontname="Helvetica,Arial,sans-serif"]
  edge [fontname="Helvetica,Arial,sans-serif"]
  node [shape=box];
  "//absl/random:random"
  "//absl/random:random" -> "//absl/random:distributions"
  "//absl/random:random" -> "//absl/random:seed_sequences"
  "//absl/random:random" -> "//absl/random/internal:pool_urbg"
  "//absl/random:random" -> "//absl/random/internal:nonsecure_base"
  "//absl/random:distributions"
  "//absl/random:distributions" -> "//absl/strings:strings"
  "//absl/random:seed_sequences"
  "//absl/random:seed_sequences" -> "//absl/random/internal:seed_material"
  "//absl/random:seed_sequences" -> "//absl/random/internal:salted_seed_seq"
  "//absl/random:seed_sequences" -> "//absl/random/internal:pool_urbg"
  "//absl/random:seed_sequences" -> "//absl/random/internal:nonsecure_base"
  "//absl/random/internal:nonsecure_base"
  "//absl/random/internal:nonsecure_base" -> "//absl/random/internal:pool_urbg"
  "//absl/random/internal:nonsecure_base" -> "//absl/random/internal:salted_seed_seq"
  "//absl/random/internal:nonsecure_base" -> "//absl/random/internal:seed_material"
  "//absl/random/internal:pool_urbg"
  "//absl/random/internal:pool_urbg" -> "//absl/random/internal:seed_material"
  "//absl/random/internal:salted_seed_seq"
  "//absl/random/internal:salted_seed_seq" -> "//absl/random/internal:seed_material"
  "//absl/random/internal:seed_material"
  "//absl/random/internal:seed_material" -> "//absl/strings:strings"
  "//absl/strings:strings"
}
```

```text
SPAT
├── timeStamp -> MinuteOfTheYear (Optional)
├── name -> DescriptiveName (Optional)
│
├── intersections -> IntersectionStateList
│   └── IntersectionStateList -> Sequence (Max 32) of IntersectionState
│       ├── name -> DescriptiveName (Optional)
│       ├── id -> IntersectionReferenceID
│       │   └── id -> IntersectionID -> Integer 0 through 65535
│       ├── revision -> MsgCount -> Integer 0 through 127
│       ├── status -> IntersectionStatusObject
│       │   └── Bitstring (Size 16) of status indicators
│       ├── moy -> MinuteOfTheYear (Optional)
│       ├── timestamp -> DSecond (Optional)
│       ├── enabledLanes -> EnabledLaneList (Optional)
│       │
│       ├── states -> MovementList
│       │   ├── signalGroup -> SignalGroupID -> Integer 0 through 255
│       │   └── state-time-speed -> MovementEventList
│       │       ├── eventState -> MovementPhaseState -> Enumerated Phase Types
│       │       ├── timing -> TimeChangeDetails (Optional)
│       │       │   ├── startTime -> TimeMark -> Integer
│       │       │   └── minEndTime -> TimeMark -> Integer
│       │       └── speeds -> AdvisorySpeedList (Optional)
│       │
│       ├── maneuverAssistList -> ManeuverAssistList (Optional)
│       ├── regional (Optional)
│       └── roadAuthorityID -> RoadAuthorityID (Optional)
│
└── regional (Optional)
```

```mermaid
journey
    title My working day
    section Go to work
      Make tea: 5: Me
      Go upstairs: 3: Me
      Do work: 1: Me, Cat
    section Go home
      Go downstairs: 5: Me
      Sit down: 5: You
```