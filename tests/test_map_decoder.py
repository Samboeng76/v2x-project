"""Command-line coverage for MAP decoding and the SPaT default."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DecodeCommandTests(unittest.TestCase):
    def run_decode(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "v2x_project", "decode", *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_map_file_writes_complete_json_without_terminal_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "decoded.json"
            result = self.run_decode(
                "output/sample_map.txt",
                "--message-type",
                "map",
                "--json-output",
                str(destination),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((result.stdout, result.stderr), ("", ""))
            messages = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(len(messages), 1)
            self.assertIn("laneSet", messages[0]["intersections"][0])
            self.assertIn("refPoint", messages[0]["intersections"][0])

    def test_map_file_keeps_valid_lines_when_another_line_fails(self) -> None:
        map_hex = (ROOT / "output/sample_map.txt").read_text(encoding="utf-8").strip()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "messages.txt"
            destination = Path(directory) / "decoded.json"
            source.write_text(f"{map_hex}\n\nnot hex\n{map_hex}\n", encoding="utf-8")
            result = self.run_decode(
                str(source),
                "--message-type",
                "map",
                "--json-output",
                str(destination),
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual((result.stdout, result.stderr), ("", ""))
            self.assertEqual(
                len(json.loads(destination.read_text(encoding="utf-8"))), 2
            )

    def test_map_direct_hex_accepts_whitespace(self) -> None:
        map_hex = (ROOT / "output/sample_map.txt").read_text(encoding="utf-8").strip()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "decoded.json"
            result = self.run_decode(
                map_hex[:20] + " \n" + map_hex[20:],
                "--message-type",
                "map",
                "--json-output",
                str(destination),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((result.stdout, result.stderr), ("", ""))
            self.assertEqual(
                len(json.loads(destination.read_text(encoding="utf-8"))), 1
            )

    def test_map_invalid_input_and_arguments_are_silent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "decoded.json"
            invalid_hex = self.run_decode(
                "not hex", "--message-type", "map", "--json-output", str(destination)
            )
            missing_input = self.run_decode("--message-type", "map")

            self.assertEqual(invalid_hex.returncode, 2)
            self.assertEqual((invalid_hex.stdout, invalid_hex.stderr), ("", ""))
            self.assertFalse(destination.exists())
            self.assertEqual(missing_input.returncode, 2)
            self.assertEqual((missing_input.stdout, missing_input.stderr), ("", ""))

    def test_spat_remains_the_default(self) -> None:
        spat_hex = (
            (ROOT / "output/sample_spat.txt")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "decoded.json"
            result = self.run_decode(spat_hex, "--json-output", str(destination))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Full decoded JSON written to", result.stdout)
            self.assertEqual(result.stderr, "")
            self.assertEqual(
                len(json.loads(destination.read_text(encoding="utf-8"))), 1
            )


if __name__ == "__main__":
    unittest.main()
