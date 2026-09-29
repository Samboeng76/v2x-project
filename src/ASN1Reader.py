import j2735_202409.j2735_202409 as j2735
from pycrate_core.charpy import Charpy


SPAT = j2735.SPAT

status = SPAT.IntersectionState._cont["status"]
print("TYPE:", status.TYPE)
print("TYPEREF:", status.get_typeref())
print("TYPEREF LIST:", status.get_typeref_list())
print("CONST:", status.get_const())

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

print(SPAT.IntersectionState.get_val())

encoded = SPAT.IntersectionState.to_uper()

print("UPER bytes:", encoded)
print("Hex:", encoded.hex())