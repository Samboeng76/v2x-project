"""Decode hexadecimal UPER-encoded J2735 SPaT messages for inspection.

Pass a hex string directly, or give the path to a text file containing one
message per line. Each decoded message is summarized in the terminal, while
the complete decoded values are written to a JSON file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pycrate_asn1rt.err import PycrateErr

import j2735_202409.j2735_202409 as j2735


def decode_spat(hex_text: str) -> dict[str, Any]:
    """Decode a hex string as the raw J2735 SPAT ASN.1 type."""
    compact_hex = "".join(hex_text.split())
    if not compact_hex:
        raise ValueError("input does not contain a hexadecimal message")
    try:
        encoded = bytes.fromhex(compact_hex)
    except ValueError as error:
        raise ValueError(f"invalid hexadecimal input: {error}") from None

    message = j2735.SPAT.SPAT
    try:
        message.from_uper(encoded)
        decoded = message.get_val()
    except (PycrateErr, ValueError, TypeError, IndexError) as error:
        raise ValueError(f"could not decode SPaT UPER message: {error}") from None
    return decoded


def _clock_time(minute_of_year: Any, dsecond: Any) -> str:
    """Format SPaT MinuteOfTheYear and DSecond fields as a UTC clock time."""
    if not isinstance(minute_of_year, int) or not isinstance(dsecond, int):
        return "time unavailable"
    minute_of_day = minute_of_year % (24 * 60)
    hour, minute = divmod(minute_of_day, 60)
    second, milliseconds = divmod(dsecond, 1000)
    return f"{hour:02}:{minute:02}:{second:02}.{milliseconds // 100} UTC"


def _time_mark(value: Any) -> str:
    """Format an ordinary TimeMark (tenths of a second within an hour)."""
    if not isinstance(value, int) or not 0 <= value <= 36_000:
        return str(value)
    minute, within_minute = divmod(value, 600)
    second, tenth = divmod(within_minute, 10)
    return f"{minute:02}:{second:02}.{tenth} UTC"


def _message_summary(decoded: dict[str, Any], label: str) -> str:
    """Create one compact summary line for a decoded SPAT message."""
    top_moy = decoded.get("timeStamp")
    intersections = decoded.get("intersections", [])
    intersection_summaries = []

    for index, intersection in enumerate(intersections, start=1):
        moy = intersection.get("moy", top_moy)
        dsecond = intersection.get("timeStamp")
        message_time = _clock_time(moy, dsecond)
        name = intersection.get("name") or f"Intersection {index}"
        movement_parts = []
        for movement in intersection.get("states", []):
            movement_name = movement.get("movementName") or "Unnamed movement"
            events = movement.get("state-time-speed", [])
            if not events:
                movement_parts.append(f"{movement_name}: state unavailable")
                continue
            for event in events:
                state = event.get("eventState", "state unavailable")
                timing = event.get("timing", {})
                end_time = timing.get("minEndTime")
                if end_time is None:
                    movement_parts.append(f"{movement_name}: {state}")
                else:
                    movement_parts.append(
                        f"{movement_name}: {state} (ends {_time_mark(end_time)})"
                    )

        summary = f"{message_time} | {name}"
        if movement_parts:
            summary += " | " + " | ".join(movement_parts)
        intersection_summaries.append(summary)

    return f"{label} | " + " || ".join(intersection_summaries)


def _default_output_path(input_path: Path | None) -> Path:
    if input_path is not None:
        return Path("output") / f"{input_path.stem}_decoded.json"
    return Path("output") / "decoded_spat.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "message",
        help="hex-encoded SPaT message, or path to a text file containing it",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="JSON output path (overwritten if it already exists)",
    )
    args = parser.parse_args()

    try:
        input_path = None
        source = Path(args.message)
        if len(args.message) < 240 and source.is_file():
            input_path = source
            decoded_messages = []
            errors = []
            with source.open(encoding="utf-8") as message_file:
                for line_number, line in enumerate(message_file, start=1):
                    if not line.strip():
                        continue
                    try:
                        decoded = decode_spat(line)
                    except ValueError as error:
                        errors.append(f"line {line_number}: {error}")
                        continue
                    decoded_messages.append(decoded)
                    print(_message_summary(decoded, f"Line {line_number}"))
        else:
            decoded = decode_spat(args.message)
            decoded_messages = [decoded]
            errors = []
            print(_message_summary(decoded, "Message"))

        output_path = args.json_output or _default_output_path(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(decoded_messages, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nFull decoded JSON written to {output_path}")
        if errors:
            parser.error("\n".join(errors))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
