"""Command-line decoding and output preservation from specification section 9."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pyjson5

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "inputFiles/SampleIntersection.json5"


class CommandLineBehaviorTests(unittest.TestCase):
    def run_command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "v2x_project", *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_spat_decoder_keeps_valid_lines_after_bad_input(self) -> None:
        spat_hex = (
            (ROOT / "output/sample_spat.txt")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "messages.txt"
            destination = Path(directory) / "decoded.json"
            source.write_text(f"{spat_hex}\nnot hex\n{spat_hex}\n", encoding="utf-8")

            result = self.run_command(
                "decode", str(source), "--json-output", str(destination)
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("line 2", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("Line 1", result.stdout)
            self.assertIn("Line 3", result.stdout)
            self.assertEqual(
                len(json.loads(destination.read_text(encoding="utf-8"))), 2
            )

    def test_missing_decode_file_is_reported_as_an_input_read_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "missing_messages.txt"
            destination = Path(directory) / "decoded.json"

            result = self.run_command(
                "decode", str(source), "--json-output", str(destination)
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn(f"reading input {source}", result.stderr)
            self.assertFalse(destination.exists())

    def test_existing_hex_named_file_takes_precedence_over_direct_hex(self) -> None:
        spat_hex = (
            (ROOT / "output/sample_spat.txt")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            (temporary / "face").write_text(spat_hex + "\n", encoding="utf-8")
            destination = temporary / "decoded.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "v2x_project",
                    "decode",
                    "face",
                    "--json-output",
                    str(destination),
                ],
                cwd=temporary,
                capture_output=True,
                text=True,
                check=False,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": str(ROOT / "src"),
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Line 1", result.stdout)
            self.assertEqual(
                len(json.loads(destination.read_text(encoding="utf-8"))), 1
            )

    def test_spat_summary_waits_for_json_write(self) -> None:
        spat_hex = (
            (ROOT / "output/sample_spat.txt")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            blocking_file = Path(directory) / "parent-file"
            blocking_file.write_text("not a directory", encoding="utf-8")

            result = self.run_command(
                "decode",
                spat_hex,
                "--json-output",
                str(blocking_file / "decoded.json"),
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("writing JSON output", result.stderr)

    def test_invalid_configuration_preserves_existing_outputs(self) -> None:
        document = pyjson5.decode(SAMPLE.read_text(encoding="utf-8"))
        document["map"]["refPoint"]["latitude"] = 91
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "invalid.json5"
            map_output = temporary / "map.txt"
            spat_output = temporary / "spat.txt"
            source.write_text(json.dumps(document), encoding="utf-8")
            map_output.write_text("original map\n", encoding="utf-8")
            spat_output.write_text("original spat\n", encoding="utf-8")

            result = self.run_command(
                "both",
                str(source),
                "--map-output",
                str(map_output),
                "--spat-output",
                str(spat_output),
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("map.refPoint.latitude", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(map_output.read_text(encoding="utf-8"), "original map\n")
            self.assertEqual(spat_output.read_text(encoding="utf-8"), "original spat\n")

    def test_failed_second_output_preserves_existing_first_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            map_output = temporary / "map.txt"
            blocked_parent = temporary / "blocked"
            map_output.write_text("original map\n", encoding="utf-8")
            blocked_parent.write_text("a file, not a directory\n", encoding="utf-8")

            result = self.run_command(
                "both",
                str(SAMPLE),
                "--map-output",
                str(map_output),
                "--spat-output",
                str(blocked_parent / "spat.txt"),
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("writing output", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(map_output.read_text(encoding="utf-8"), "original map\n")
            self.assertEqual(
                blocked_parent.read_text(encoding="utf-8"), "a file, not a directory\n"
            )


if __name__ == "__main__":
    unittest.main()
