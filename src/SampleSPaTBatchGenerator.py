"""Small reference implementation for generating a timed SPaT batch.

Input is JSON5. Output is UTF-8 text with one hexadecimal UPER SPAT frame
per line. This is an illustrative starting point, not a production encoder.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

import pyjson5
import j2735_202409.j2735_202409 as j2735


SPAT = j2735.SPAT
DEFAULT_INTERVAL = Decimal("0.1")
MAX_PHASE_SECONDS = Decimal("3600")

PHASES = {
    "dark": 1,
    "stop-Then-Proceed": 2,
    "stop-And-Remain": 3,
    "pre-Movement": 4,
    "permissive-Movement-Allowed": 5,
    "protected-Movement-Allowed": 6,
    "permissive-clearance": 7,
    "protected-clearance": 8,
    "caution-Conflicting-Traffic": 9,
}


def _positive_decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a positive number") from None
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{label} must be a positive number")
    return number


def _minute_of_year(moment: datetime) -> int:
    return (moment.timetuple().tm_yday - 1) * 1440 + moment.hour * 60 + moment.minute


def _dsecond(moment: datetime) -> int:
    """Return milliseconds elapsed in the current minute."""
    return moment.second * 1000 + moment.microsecond // 1000


def _time_mark(moment: datetime) -> int:
    """Return tenths of a second elapsed in the current UTC hour."""
    return (moment.minute * 60 + moment.second) * 10 + moment.microsecond // 100_000


def _phase_code(phase: Any, where: str) -> int:
    if not isinstance(phase, str) or phase not in PHASES:
        supported = ", ".join(PHASES)
        raise ValueError(f"{where}: unsupported phase; choose one of {supported}")
    return PHASES[phase]


def _prepare(config: dict[str, Any]) -> tuple[Decimal, list[list[dict[str, Any]]], int]:
    if config.get("messageType") != "SPAT":
        raise ValueError('messageType must be "SPAT"')
    if not isinstance(config.get("includeTimestamps"), bool):
        raise ValueError("includeTimestamps must be true or false")

    interval = _positive_decimal(
        config.get("messageInterval", DEFAULT_INTERVAL), "messageInterval"
    )
    intersection = config.get("intersection")
    if not isinstance(intersection, dict):
        raise ValueError("intersection must be an object")
    intersection_id = intersection.get("id")
    if isinstance(intersection_id, bool) or not isinstance(intersection_id, int):
        raise ValueError("intersection.id must be an integer")
    if not 0 <= intersection_id <= 65535:
        raise ValueError("intersection.id must be between 0 and 65535")
    if not isinstance(intersection.get("name"), str):
        raise ValueError("intersection.name must be a string")

    movements = config.get("movements")
    if not isinstance(movements, list) or not movements:
        raise ValueError("movements must be a non-empty array")

    prepared: list[list[dict[str, Any]]] = []
    batch_ticks: int | None = None
    for movement_index, movement in enumerate(movements):
        where = f"movements[{movement_index}]"
        if not isinstance(movement, dict) or not isinstance(movement.get("name"), str):
            raise ValueError(f"{where}.name must be a string")
        phases = movement.get("phases")
        if not isinstance(phases, list) or not phases:
            raise ValueError(f"{where}.phases must be a non-empty array")

        end_tick = 0
        schedule = []
        for phase_index, phase_item in enumerate(phases):
            phase_where = f"{where}.phases[{phase_index}]"
            if not isinstance(phase_item, dict):
                raise ValueError(f"{phase_where} must be an object")
            phase = phase_item.get("phase")
            code = _phase_code(phase, phase_where)
            duration = _positive_decimal(
                phase_item.get("duration"), f"{phase_where}.duration"
            )
            if duration > MAX_PHASE_SECONDS:
                raise ValueError(f"{phase_where}.duration cannot exceed 3600 seconds")
            ticks = duration / interval
            if ticks != ticks.to_integral_value():
                raise ValueError(
                    f"{phase_where}.duration must be an exact multiple of messageInterval"
                )
            end_tick += int(ticks)
            schedule.append(
                {"end_tick": end_tick, "phase": phase, "signal_group": code}
            )

        if batch_ticks is None:
            batch_ticks = end_tick
        elif end_tick != batch_ticks:
            raise ValueError("all movements must have the same total phase duration")
        prepared.append(schedule)

    assert batch_ticks is not None
    return interval, prepared, batch_ticks


def generate_messages(
    config: dict[str, Any], start_time: datetime | None = None
) -> Iterator[bytes]:
    """Yield one complete UPER-encoded SPAT frame for each sample time."""
    interval, schedules, batch_ticks = _prepare(config)
    if start_time is None:
        start_time = datetime.now(timezone.utc)
    elif start_time.tzinfo is None:
        raise ValueError("start_time must include a timezone")
    start_time = start_time.astimezone(timezone.utc)

    intersection_config = config["intersection"]
    include_timestamps = config["includeTimestamps"]
    for sample_tick in range(batch_ticks):
        elapsed = interval * sample_tick
        message_time = start_time + timedelta(seconds=float(elapsed))
        movement_states = []
        for movement, schedule in zip(config["movements"], schedules):
            active = next(item for item in schedule if sample_tick < item["end_tick"])
            phase_end = start_time + timedelta(
                seconds=float(interval * active["end_tick"])
            )
            movement_states.append(
                {
                    "movementName": movement["name"],
                    # Temporary rule from the specification: derive the ID from phase.
                    "signalGroup": active["signal_group"],
                    "state-time-speed": [
                        {
                            "eventState": active["phase"],
                            "timing": {"minEndTime": _time_mark(phase_end)},
                        }
                    ],
                }
            )

        intersection_state = {
            "id": {"id": intersection_config["id"]},
            "revision": sample_tick % 128,
            "status": (0, 16),
            "states": movement_states,
        }
        if intersection_config.get("name"):
            intersection_state["name"] = intersection_config["name"]
        if include_timestamps:
            intersection_state["moy"] = _minute_of_year(message_time)
            intersection_state["timeStamp"] = _dsecond(message_time)

        frame = {"intersections": [intersection_state]}
        if include_timestamps:
            frame["timeStamp"] = _minute_of_year(message_time)

        # SPAT.SPAT is the top-level J2735 SPAT data frame type.
        SPAT.SPAT.set_val(frame)
        yield SPAT.SPAT.to_uper()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON5 configuration file")
    parser.add_argument(
        "output", type=Path, help="output text file (one hex message per line)"
    )
    args = parser.parse_args()

    try:
        with args.input.open("r", encoding="utf-8") as source:
            config = pyjson5.load(source)
        if not isinstance(config, dict):
            raise ValueError("the JSON5 document must contain an object")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as output:
            for message in generate_messages(config):
                output.write(message.hex() + "\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
