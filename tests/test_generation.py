"""Fixed-time MAP and SPaT behavior from specification section 9."""

import unittest
from datetime import UTC, datetime
from pathlib import Path

import pyjson5

from v2x_project.core import (
    UserInputError,
    decode_map,
    decode_spat,
    encode_map,
    generate_spat_messages,
    load_configuration,
    validate_configuration,
)

SAMPLE = Path(__file__).resolve().parents[1] / "inputFiles/SampleIntersection.json5"
START = datetime(2025, 1, 1, 12, 59, 55, 250_000, tzinfo=UTC)


def sample_document() -> dict:
    return pyjson5.decode(SAMPLE.read_text(encoding="utf-8"))


class GenerationTests(unittest.TestCase):
    def test_generation_rejects_naive_start_time(self) -> None:
        configuration = load_configuration(SAMPLE)
        naive_time = datetime(2025, 1, 1, 12, 59, 55)  # noqa: DTZ001 - Test rejection.

        with self.assertRaisesRegex(UserInputError, "timezone"):
            encode_map(configuration, naive_time)
        with self.assertRaisesRegex(UserInputError, "timezone"):
            next(generate_spat_messages(configuration, naive_time))

    def test_decoders_reject_bytes_after_a_complete_message(self) -> None:
        configuration = load_configuration(SAMPLE)
        map_bytes = encode_map(configuration, START)
        spat_bytes = next(generate_spat_messages(configuration, START))

        for name, decoder, message in (
            ("MAP", decode_map, map_bytes),
            ("SPaT", decode_spat, spat_bytes),
        ):
            with self.subTest(message_type=name):
                self.assertEqual(
                    decoder(message.hex())["intersections"][0]["id"]["id"], 42
                )
                for extra in (b"\x00", message):
                    with self.assertRaises(UserInputError):
                        decoder((message + extra).hex())

    def test_message_frames_preserve_values_and_identify_message_type(self) -> None:
        configuration = load_configuration(SAMPLE)
        raw_map = encode_map(configuration, START)
        framed_map = encode_map(configuration, START, message_frame=True)
        raw_spat = next(generate_spat_messages(configuration, START))
        framed_spat = next(
            generate_spat_messages(configuration, START, message_frame=True)
        )

        self.assertEqual(
            decode_map(framed_map.hex(), message_frame=True),
            {"messageId": 18, "value": decode_map(raw_map.hex())},
        )
        self.assertEqual(
            decode_spat(framed_spat.hex(), message_frame=True),
            {"messageId": 19, "value": decode_spat(raw_spat.hex())},
        )
        with self.assertRaisesRegex(UserInputError, "containing SPAT"):
            decode_spat(framed_map.hex(), message_frame=True)
        with self.assertRaisesRegex(UserInputError, "containing MapData"):
            decode_map(framed_spat.hex(), message_frame=True)
        for framed, decoder in ((framed_map, decode_map), (framed_spat, decode_spat)):
            with self.subTest(message_id=framed[1]), self.assertRaises(UserInputError):
                decoder((framed + b"\x00").hex(), message_frame=True)

    def test_specification_example_generates_map_and_single_movement_spat(self) -> None:
        specification = (
            SAMPLE.parents[1] / "Documentation/FormalSpecification.md"
        ).read_text(encoding="utf-8")
        example = specification.split("### 3.7 Example JSON5 input", 1)[1]
        example = example.split("```json5", 1)[1].split("```", 1)[0]
        configuration = validate_configuration(pyjson5.decode(example))

        decoded_map = decode_map(encode_map(configuration, START).hex())
        decoded_spat = decode_spat(
            next(generate_spat_messages(configuration, START)).hex()
        )
        map_groups = {
            connection["signalGroup"]
            for lane in decoded_map["intersections"][0]["laneSet"]
            for connection in lane.get("connectsTo", [])
            if "signalGroup" in connection
        }
        spat_groups = {
            movement["signalGroup"]
            for movement in decoded_spat["intersections"][0]["states"]
        }
        self.assertEqual(map_groups, {1, 2, 3, 4})
        self.assertEqual(spat_groups, {1})

    def test_map_has_expected_intersection_lanes_connections_and_time(self) -> None:
        configuration = load_configuration(SAMPLE)

        decoded = decode_map(encode_map(configuration, START).hex())

        self.assertEqual(decoded["timeStamp"], 779)  # Jan 1, 12:59 UTC
        self.assertEqual(decoded["msgIssueRevision"], 0)
        self.assertEqual(len(decoded["intersections"]), 1)
        intersection = decoded["intersections"][0]
        self.assertEqual(intersection["revision"], 0)
        self.assertEqual(intersection["id"], {"id": 42})
        self.assertEqual(
            intersection["refPoint"], {"lat": 389564590, "long": -771502970}
        )
        lanes = {lane["laneID"]: lane for lane in intersection["laneSet"]}
        self.assertEqual(set(lanes), set(range(1, 9)))
        expected_connections = {
            1: [(6, 2), (8, None)],
            3: [(8, 4), (2, None)],
            5: [(2, 1), (4, None)],
            7: [(4, 3), (6, None)],
        }
        for lane_id, expected in expected_connections.items():
            with self.subTest(lane_id=lane_id):
                self.assertEqual(
                    [
                        (
                            connection["connectingLane"]["lane"],
                            connection.get("signalGroup"),
                        )
                        for connection in lanes[lane_id]["connectsTo"]
                    ],
                    expected,
                )
        for lane_id in (2, 4, 6, 8):
            self.assertNotIn("connectsTo", lanes[lane_id])

    def test_spat_batch_changes_state_at_boundary_and_uses_utc_time(self) -> None:
        configuration = load_configuration(SAMPLE)

        messages = list(generate_spat_messages(configuration, START))

        self.assertEqual(len(messages), 150)
        expected_samples = {
            # Tick 100 begins the second phase at 13:00:05.250 UTC.
            0: (779, 55_250, 53),
            99: (780, 5_150, 53),
            100: (780, 5_250, 103),
            149: (780, 10_150, 103),
        }
        expected_states_before = {
            1: "protected-Movement-Allowed",
            2: "stop-And-Remain",
            3: "stop-And-Remain",
            4: "protected-Movement-Allowed",
        }
        expected_states_after = {
            1: "protected-clearance",
            2: "protected-Movement-Allowed",
            3: "permissive-Movement-Allowed",
            4: "protected-clearance",
        }
        for tick, (minute, dsecond, end_time) in expected_samples.items():
            with self.subTest(tick=tick):
                decoded = decode_spat(messages[tick].hex())
                intersection = decoded["intersections"][0]
                self.assertEqual(decoded["timeStamp"], minute)
                self.assertEqual(intersection["moy"], minute)
                self.assertEqual(intersection["timeStamp"], dsecond)
                self.assertEqual(intersection["id"], {"id": 42})
                self.assertEqual(len(intersection["states"]), 4)
                events = {
                    movement["signalGroup"]: movement["state-time-speed"][0]
                    for movement in intersection["states"]
                }
                expected_states = (
                    expected_states_before if tick < 100 else expected_states_after
                )
                self.assertEqual(
                    {group: event["eventState"] for group, event in events.items()},
                    expected_states,
                )
                for event in events.values():
                    self.assertEqual(event["timing"]["minEndTime"], end_time)

        for tick, revision in ((127, 127), (128, 0), (129, 1)):
            with self.subTest(revision_tick=tick):
                decoded = decode_spat(messages[tick].hex())
                self.assertEqual(decoded["intersections"][0]["revision"], revision)

    def test_timestamps_cross_new_year(self) -> None:
        configuration = load_configuration(SAMPLE)
        start = datetime(2024, 12, 31, 23, 59, 59, 900_000, tzinfo=UTC)

        decoded_map = decode_map(encode_map(configuration, start).hex())
        messages = generate_spat_messages(configuration, start)
        first = decode_spat(next(messages).hex())
        second = decode_spat(next(messages).hex())

        self.assertEqual(decoded_map["timeStamp"], 527_039)
        self.assertEqual(first["timeStamp"], 527_039)
        self.assertEqual(first["intersections"][0]["moy"], 527_039)
        self.assertEqual(first["intersections"][0]["timeStamp"], 59_900)
        self.assertEqual(second["timeStamp"], 0)
        self.assertEqual(second["intersections"][0]["moy"], 0)
        self.assertEqual(second["intersections"][0]["timeStamp"], 0)

    def test_timestamps_can_be_omitted_without_omitting_phase_timing(self) -> None:
        document = sample_document()
        document["includeTimestamps"] = False
        configuration = validate_configuration(document)

        decoded_map = decode_map(encode_map(configuration, START).hex())
        decoded_spat = decode_spat(
            next(generate_spat_messages(configuration, START)).hex()
        )

        self.assertNotIn("timeStamp", decoded_map)
        self.assertNotIn("timeStamp", decoded_spat)
        intersection = decoded_spat["intersections"][0]
        self.assertNotIn("moy", intersection)
        self.assertNotIn("timeStamp", intersection)
        for movement in intersection["states"]:
            self.assertIn("minEndTime", movement["state-time-speed"][0]["timing"])

    def test_min_end_time_rounds_halfway_up_and_wraps_at_hour(self) -> None:
        configuration = load_configuration(SAMPLE)
        for microsecond, expected in ((49_000, 100), (50_000, 101)):
            with self.subTest(microsecond=microsecond):
                start = datetime(2025, 1, 1, 12, 0, 0, microsecond, tzinfo=UTC)
                decoded = decode_spat(
                    next(generate_spat_messages(configuration, start)).hex()
                )
                event = decoded["intersections"][0]["states"][0]["state-time-speed"][0]
                self.assertEqual(event["timing"]["minEndTime"], expected)

        hour_end = datetime(2025, 1, 1, 12, 59, 50, tzinfo=UTC)
        decoded = decode_spat(
            next(generate_spat_messages(configuration, hour_end)).hex()
        )
        for movement in decoded["intersections"][0]["states"]:
            self.assertEqual(movement["state-time-speed"][0]["timing"]["minEndTime"], 0)

    def test_map_coordinate_and_elevation_boundaries(self) -> None:
        cases = (
            ("minimum", -90, -179.9999999, -409.5, -900_000_000, -1_799_999_999, -4095),
            ("maximum", 90, 180, 6143.9, 900_000_000, 1_800_000_000, 61_439),
            ("positive halfway", 0.00000005, 0.00000005, 0.05, 1, 1, 1),
            ("negative halfway", -0.00000005, -0.00000005, -0.05, -1, -1, -1),
        )
        for label, latitude, longitude, elevation, lat, long, elev in cases:
            with self.subTest(label=label):
                document = sample_document()
                document["map"]["refPoint"] = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "elevation": elevation,
                }
                configuration = validate_configuration(document)
                decoded = decode_map(encode_map(configuration, START).hex())
                self.assertEqual(
                    decoded["intersections"][0]["refPoint"],
                    {"lat": lat, "long": long, "elevation": elev},
                )

    def test_node_xy4_offset_boundary(self) -> None:
        document = sample_document()
        document["map"]["approachExtentM"] = 40.95
        configuration = validate_configuration(document)
        decoded = decode_map(encode_map(configuration, START).hex())
        lanes = {
            lane["laneID"]: lane for lane in decoded["intersections"][0]["laneSet"]
        }
        self.assertEqual(len(lanes), 8)
        self.assertEqual(
            lanes[3]["nodeList"][1][0]["delta"],
            ("node-XY4", {"x": 4095, "y": 183}),
        )

        document["map"]["approachExtentM"] = 40.96
        with self.assertRaises(UserInputError) as raised:
            validate_configuration(document)
        self.assertIn("map.approachExtentM", str(raised.exception))
        self.assertIn("node-XY4", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
