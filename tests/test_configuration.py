"""Configuration acceptance and diagnostics from specification section 9."""

import copy
import tempfile
import unittest
from pathlib import Path

import pyjson5

from v2x_project.core import UserInputError, load_configuration, validate_configuration

SAMPLE = Path(__file__).resolve().parents[1] / "inputFiles/SampleIntersection.json5"


def sample_document() -> dict:
    return pyjson5.decode(SAMPLE.read_text(encoding="utf-8"))


class ConfigurationTests(unittest.TestCase):
    def test_sample_and_documented_defaults_are_accepted(self) -> None:
        document = sample_document()
        document["map"].pop("laneWidthCm")
        document["spat"].pop("messageInterval")

        configuration = validate_configuration(document)

        self.assertEqual(configuration.intersection_id, 42)
        self.assertEqual(configuration.map.lane_width_cm, 366)
        self.assertEqual(configuration.spat.interval_ms, 100)
        self.assertEqual(configuration.spat.batch_ticks, 150)

    def test_spat_group_without_map_connection_is_rejected(self) -> None:
        document = sample_document()
        document["spat"]["movements"][0]["signalGroup"] = 5

        with self.assertRaises(UserInputError) as raised:
            validate_configuration(document)

        self.assertIn("spat.movements[0].signalGroup", str(raised.exception))
        self.assertIn("no matching MAP lane connection", str(raised.exception))

    def test_invalid_fields_values_and_timing_identify_the_field(self) -> None:
        cases = (
            ("missing map", lambda doc: doc.pop("map"), "configuration.map"),
            (
                "boolean intersection ID",
                lambda doc: doc["intersection"].update(id=True),
                "intersection.id",
            ),
            (
                "latitude out of range",
                lambda doc: doc["map"]["refPoint"].update(latitude=91),
                "map.refPoint.latitude",
            ),
            (
                "invalid explicit interval",
                lambda doc: doc["spat"].update(messageInterval=None),
                "spat.messageInterval",
            ),
            (
                "duplicate signal group",
                lambda doc: doc["spat"]["movements"][1].update(signalGroup=1),
                "spat.movements[1].signalGroup",
            ),
            (
                "duration not aligned to interval",
                lambda doc: doc["spat"]["movements"][0]["phases"][0].update(
                    duration=10.05
                ),
                "spat.movements[0].phases[0].duration",
            ),
            (
                "different movement totals",
                lambda doc: doc["spat"]["movements"][1]["phases"][0].update(
                    duration=11
                ),
                "spat.movements[1].phases",
            ),
        )
        for label, change, field in cases:
            with self.subTest(label=label):
                document = copy.deepcopy(sample_document())
                change(document)
                with self.assertRaises(UserInputError) as raised:
                    validate_configuration(document)
                self.assertIn(field, str(raised.exception))

    def test_json5_syntax_error_identifies_the_input_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.json5"
            source.write_text("{ intersection: [ }", encoding="utf-8")

            with self.assertRaises(UserInputError) as raised:
                load_configuration(source)

            self.assertIn(str(source), str(raised.exception))
            self.assertIn("JSON5 syntax error", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
