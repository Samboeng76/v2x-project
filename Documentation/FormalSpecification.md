Overall Functionality:
----------------------

1. The system shall parse a JSON5 input file containing the information required to generate a J2735 message.
2. The JSON5 input format shall closely follow the structure of the corresponding SAE J2735 ASN.1 message definition.
3. The system shall obtain the required SAE J2735 ASN.1 definitions from the USDOT J2735 Python library.
4. The system shall use PyCrate to construct and encode the generated message using the Unaligned Packed Encoding Rules (UPER).
5. The system shall provide the resulting encoded message as raw hexadecimal bytes.
6. The system shall provide default values for fields for which an input value is not explicitly provided. Specific default values shall be defined as the message implementation is further developed.

SPAT Functionality:
-------------------

1. The SPAT message format to be used is shown below.

   * SPAT IntersectionState Message Required:
     * ID (Region and ID)-- Both Int
     * Revision -- Int
     * Status -- Bitstring (0bxxxx, 16)
     * States -- Meat of the message and further expanded upon below
   * SPAT IntersectionState Message Optional
     * Name -- String
2. Default values should be provided for certain fields (Expand upon this later)
3. Each movement state shall support, at minimum:
   * Movement Name — String
   * Signal Group — Integer
   * State-Time-Speed — List of state and timing information
4. Each State-Time-Speed entry shall support the following fields:
   * Event State
   * Timing (**Might not need all of these**)
      * Start Time
      * Minimum End Time
      * Maximum End Time
      * Likely Time
      * Confidence
      * Next Time
5. Additional SPAT fields defined by the applicable SAE J2735 ASN.1 specification shall be evaluated for inclusion as the implementation is expanded.

Implementation Specifics:
-------------------------

1. The provided USDOT library can be used by `import j2735_202409.j2735_202409 as j2735`

2. A SPAT object can be created by `SPAT = j2735.SPAT`

3. Using the SPAT object, `SPAT.IntersectionState.set_val` can be used to directly modify SPAT fields. The code segment below shows a sample SPAT setup. **Do note that more fields may exist/need to be added.**

```
SPAT.IntersectionState.set_val({
    "name": "Test Intersection",

    "id": {
        "region": 1,
        "id": 42
    },

    "revision": 1,
    "status": (0b1011010010110110, 16),
    "states": [
        {
            "movementName": "Northbound Through",

            "signalGroup": 1,

            "state-time-speed": [
                {
                    "eventState": "stop-And-Remain",

                    "timing": {
                        "startTime": 0,
                        "minEndTime": 100,
                        "maxEndTime": 100,
                        "likelyTime": 100,
                        "confidence": 0,
                        "nextTime": 0
                    }
                }
            ]
        }
    ]
})
```

Tools To Use:
-------------

1. Package Manager:
2. Formatter:
3. Libraries: PyCrate, PyJson5,
   [USDOT J2735](https://github.com/usdot-fhwa-stol/j2735_202409/tree/main)
