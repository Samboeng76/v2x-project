## Implementation Ideas and Notes

### Input / Intersection Model

* Use a JSON configuration as the initial user interface.
* Define a common internal representation of a signalized intersection.
* Keep the configuration at a higher level than the underlying J2735 ASN.1 structures.
* Determine how to represent:

  * Intersection location
  * Approaches and lanes
  * Lane geometry and connections
  * Allowed movements
  * Signal groups
  * Signal phases and timing
* Generate both MAP and SPaT information from the same intersection representation where possible.
* A GUI could be added later, but should remain separate from the core message-generation system.

### Message Generation

* Initial focus is MAP and SPaT.
* Avoid requiring users to specify information that can be derived from the intersection model.
* Keep message-specific generation code separate so additional J2735 message types can be added later.
* Determine which J2735 fields are required, optional, or automatically derived for the supported messages.

### SPaT

* Represent signal behavior using phases and timing rather than manually specifying every message.
* Generate the current signal state from a simulation time.
* Support generating a sequence of SPaT messages as the signal state changes.
* Initially keep the signal model simple and expand it as needed.

### MAP

* Determine a practical representation for lane geometry, such as points or centerlines.
* Represent lane connections and allowed movements in a way that can be translated into J2735 MAP structures.
* Ensure movements and signal groups can be related between MAP and SPaT.

### ASN.1 / Encoding

* Use the appropriate SAE J2735 ASN.1 definitions.
* Determine the J2735 revision used by the project.
* Use an existing ASN.1 implementation, with **pycrate** as the primary option currently being investigated.
* Construct the J2735 ASN.1 objects from the internal intersection representation.
* Encode the resulting structures using the appropriate J2735 encoding rules.
* Keep the ASN.1 representation separate from the higher-level intersection model.

### Decoder / Validation

* Use a decoder to inspect and validate generated messages.
* Prefer an independent implementation for validation when possible.
* The existing FHWA J2735 decoder can be investigated for MAP/SPaT validation.
* Use round-trip testing:

```text
JSON Configuration
        ↓
Intersection Model
        ↓
J2735 Message
        ↓
ASN.1 / UPER Encoding
        ↓
Encoded Message
        ↓
Independent Decoder
        ↓
Compare With Input
```

* Build simple known-good test messages before adding more complicated scenarios.
* Add automated regression tests as the message generator develops.

### Output

* Primary output is the encoded V2X message.
* Support hexadecimal output for inspection and debugging.
* Support raw binary output for eventual transmission.
* Keep message generation separate from transmission.
* Network communication can be added later without changing the core generator.

### Initial Development Plan

1. Get the J2735 ASN.1 definitions working with pycrate.
2. Construct a minimal SPaT message directly from the ASN.1 structures.
3. Verify that the generated message can be decoded.
4. Build the higher-level JSON/intersection representation.
5. Translate the representation into a SPaT message.
6. Add basic SPaT timing and message sequencing.
7. Implement a minimal MAP message.
8. Connect MAP and SPaT through the common intersection model.
9. Add validation and automated tests.
10. Expand the intersection model and message capabilities as needed.

### Future Features

* BSM generation
* Multiple intersections
* More advanced signal timing
* Automated test scenario generation
* Message playback and logging
* Network/UDP transmission
* V2X hardware integration
* Vehicle or traffic simulator integration
* GUI-based intersection creation
* Additional J2735 message types
