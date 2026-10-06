# SPaT ASN.1 Structure Notes

These notes summarize the generated J2735 ASN.1 definitions currently being
explored in this project. They are an implementation aid, not a substitute for
the applicable SAE J2735 specification. Confirm field constraints and optional
fields against the checked-in 2024-09 definitions as implementation proceeds.

```text
SPAT
├── timeStamp: MinuteOfTheYear (optional)
├── name: DescriptiveName (optional)
├── intersections: IntersectionStateList
│   └── IntersectionState (up to 32 entries)
│       ├── name: DescriptiveName (optional)
│       ├── id: IntersectionReferenceID
│       │   └── id: IntersectionID (0..65535)
│       ├── revision: MsgCount (0..127)
│       ├── status: IntersectionStatusObject (16-bit bit string)
│       ├── moy: MinuteOfTheYear (optional)
│       ├── timestamp: DSecond (optional)
│       ├── enabledLanes: EnabledLaneList (optional)
│       ├── states: MovementList
│       │   └── Movement
│       │       ├── signalGroup: SignalGroupID (0..255)
│       │       └── state-time-speed: MovementEventList
│       │           ├── eventState: MovementPhaseState
│       │           ├── timing: TimeChangeDetails (optional)
│       │           │   ├── startTime: TimeMark
│       │           │   └── minEndTime: TimeMark
│       │           └── speeds: AdvisorySpeedList (optional)
│       ├── maneuverAssistList: ManeuverAssistList (optional)
│       ├── regional (optional)
│       └── roadAuthorityID: RoadAuthorityID (optional)
└── regional (optional)
```

The high-level input model and its mapping to these ASN.1 fields are still being
defined. In particular, the units and conversion rules for user-provided signal
durations need to be documented before the sample configuration is treated as a
stable interface.
