"""Configuration validation and J2735 MAP/SPaT message construction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterator

import pyjson5
import j2735_202409 as j2735


class UserInputError(ValueError):
    """An input or configuration error suitable for a concise CLI diagnostic."""


class MessageEncodingError(RuntimeError):
    """An unexpected error while constructing or encoding an ASN.1 message."""


PHASES = {
    "dark",
    "stop-Then-Proceed",
    "stop-And-Remain",
    "pre-Movement",
    "permissive-Movement-Allowed",
    "protected-Movement-Allowed",
    "permissive-clearance",
    "protected-clearance",
    "caution-Conflicting-Traffic",
}

SIGNAL_GROUPS = {
    1: "Northbound through",
    2: "Southbound through",
    3: "Eastbound through",
    4: "Westbound through",
    5: "Northbound left turn",
    6: "Southbound left turn",
}

LAYER_TYPES = {
    "none",
    "mixedContent",
    "generalMapData",
    "intersectionData",
    "curveData",
    "roadwaySectionData",
    "parkingAreaData",
    "sharedLaneData",
}

DEFAULT_INTERVAL = Decimal("0.1")
MAX_PHASE_DURATION = Decimal("3600")
NODE_OFFSET_MIN_CM = -4096
NODE_OFFSET_MAX_CM = 4095


@dataclass(frozen=True)
class Phase:
    name: str
    duration: Decimal


@dataclass(frozen=True)
class Movement:
    name: str
    signal_group: int
    phases: tuple[Phase, ...]


@dataclass(frozen=True)
class MapSettings:
    latitude: int
    longitude: int
    elevation: int | None
    lane_width_cm: int | None
    geometry_width_cm: int
    intersection_half_extent_m: Decimal
    approach_extent_m: Decimal
    layer_type: str


@dataclass(frozen=True)
class SpatSettings:
    interval_ms: int
    status: int
    movements: tuple[Movement, ...]
    schedules: tuple[tuple[int, ...], ...]
    batch_ticks: int


@dataclass(frozen=True)
class Configuration:
    include_timestamps: bool
    intersection_id: int
    intersection_name: str
    map: MapSettings
    spat: SpatSettings


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise UserInputError(f"{path}: expected an object")
    return value


def _check_keys(
    value: dict[str, Any], allowed: set[str], required: set[str], path: str
) -> None:
    unknown = set(value) - allowed
    if unknown:
        key = sorted(unknown)[0]
        raise UserInputError(f"{path}.{key}: unsupported field")
    missing = required - set(value)
    if missing:
        key = sorted(missing)[0]
        raise UserInputError(f"{path}.{key}: required field is missing")


def _string(value: Any, path: str, *, descriptive: bool = False) -> str:
    if not isinstance(value, str):
        raise UserInputError(f"{path}: expected a string")
    if descriptive:
        if not 1 <= len(value) <= 63:
            raise UserInputError(f"{path}: expected 1 to 63 ASCII characters")
        if any(ord(char) > 127 for char in value):
            raise UserInputError(f"{path}: expected ASCII characters")
    return value


def _integer(value: Any, path: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise UserInputError(f"{path}: expected an integer from {minimum} through {maximum}")
    if not minimum <= value <= maximum:
        raise UserInputError(f"{path}: expected an integer from {minimum} through {maximum}")
    return value


def _number(value: Any, path: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UserInputError(f"{path}: expected a number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise UserInputError(f"{path}: expected a finite number") from None
    if not result.is_finite():
        raise UserInputError(f"{path}: expected a finite number")
    return result


def _positive_number(value: Any, path: str) -> Decimal:
    result = _number(value, path)
    if result <= 0:
        raise UserInputError(f"{path}: expected a positive number")
    return result


def _round_integer(value: Decimal) -> int:
    """Round to an integer, with exact halfway cases away from zero."""
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def _scaled_value(
    value: Any, path: str, scale: int, minimum: Decimal, maximum: Decimal
) -> int:
    number = _number(value, path)
    if not minimum <= number <= maximum:
        raise UserInputError(f"{path}: expected a value from {minimum} through {maximum}")
    return _round_integer(number * scale)


def _parse_status(value: Any, path: str = "spat.status") -> int:
    if not isinstance(value, str):
        raise UserInputError(f'{path}: expected "0b" plus 16 bits or "0x" plus 4 hex digits')
    if re.fullmatch(r"0[bB][01]{16}", value):
        return int(value[2:], 2)
    if re.fullmatch(r"0[xX][0-9a-fA-F]{4}", value):
        return int(value[2:], 16)
    raise UserInputError(f'{path}: expected "0b" plus 16 bits or "0x" plus 4 hex digits')


def _json5_error(text: str, error: Exception) -> str:
    message = str(error).splitlines()[0] if str(error) else "invalid JSON5 syntax"
    match = re.search(r"\bnear\s+(\d+)", message)
    if match:
        offset = min(int(match.group(1)), len(text))
        prefix = text[:offset]
        line = prefix.count("\n") + 1
        last_newline = prefix.rfind("\n")
        column = offset - last_newline
        return f"JSON5 syntax error at line {line}, column {column}: {message}"
    return f"JSON5 syntax error: {message}"


def load_configuration(path: Path) -> Configuration:
    """Read and fully validate the unified JSON5 configuration."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        raise UserInputError(f"reading input {path}: {error.strerror or error}") from None
    except UnicodeError as error:
        raise UserInputError(f"reading input {path}: configuration is not valid UTF-8 ({error})") from None

    try:
        document = pyjson5.decode(source)
    except pyjson5.Json5Exception as error:
        raise UserInputError(f"{path}: {_json5_error(source, error)}") from None
    if not isinstance(document, dict):
        raise UserInputError(f"{path}: JSON5 document must contain an object")
    try:
        return validate_configuration(document)
    except UserInputError as error:
        raise UserInputError(f"{path}: {error}") from None


def validate_configuration(document: dict[str, Any]) -> Configuration:
    _check_keys(
        document,
        {"includeTimestamps", "intersection", "map", "spat"},
        {"intersection", "map", "spat"},
        "configuration",
    )

    include_timestamps = document.get("includeTimestamps", True)
    if not isinstance(include_timestamps, bool):
        raise UserInputError("includeTimestamps: expected true or false")

    intersection = _mapping(document["intersection"], "intersection")
    _check_keys(intersection, {"id", "name"}, {"id", "name"}, "intersection")
    intersection_id = _integer(intersection["id"], "intersection.id", 0, 65535)
    intersection_name = _string(
        intersection["name"], "intersection.name", descriptive=True
    )

    map_data = _mapping(document["map"], "map")
    _check_keys(
        map_data,
        {
            "layout",
            "refPoint",
            "laneWidthCm",
            "intersectionHalfExtentM",
            "approachExtentM",
            "layerType",
        },
        {"layout", "refPoint"},
        "map",
    )
    layout = _string(map_data["layout"], "map.layout")
    if layout != "fourWayNoLeftTurn":
        raise UserInputError(
            'map.layout: unsupported layout; expected "fourWayNoLeftTurn"'
        )

    ref_point = _mapping(map_data["refPoint"], "map.refPoint")
    _check_keys(
        ref_point,
        {"latitude", "longitude", "elevation"},
        {"latitude", "longitude"},
        "map.refPoint",
    )
    latitude = _scaled_value(
        ref_point["latitude"],
        "map.refPoint.latitude",
        10_000_000,
        Decimal("-90"),
        Decimal("90"),
    )
    longitude = _scaled_value(
        ref_point["longitude"],
        "map.refPoint.longitude",
        10_000_000,
        Decimal("-179.9999999"),
        Decimal("180"),
    )
    elevation = None
    if "elevation" in ref_point:
        elevation = _scaled_value(
            ref_point["elevation"],
            "map.refPoint.elevation",
            10,
            Decimal("-409.5"),
            Decimal("6143.9"),
        )

    configured_width: int | None = 366
    if "laneWidthCm" in map_data:
        value = map_data["laneWidthCm"]
        if value is False:
            configured_width = None
        else:
            configured_width = _integer(value, "map.laneWidthCm", 1, 32767)
    geometry_width = configured_width if configured_width is not None else 366

    half_extent = _positive_number(
        map_data.get("intersectionHalfExtentM", 10),
        "map.intersectionHalfExtentM",
    )
    approach_extent = _positive_number(
        map_data.get("approachExtentM", 30), "map.approachExtentM"
    )
    if approach_extent <= half_extent:
        raise UserInputError(
            "map.approachExtentM: expected a value greater than map.intersectionHalfExtentM"
        )

    layer_type = map_data.get("layerType", "intersectionData")
    layer_type = _string(layer_type, "map.layerType")
    if layer_type not in LAYER_TYPES:
        supported = ", ".join(sorted(LAYER_TYPES))
        raise UserInputError(f"map.layerType: unsupported value; choose one of {supported}")

    map_settings = MapSettings(
        latitude=latitude,
        longitude=longitude,
        elevation=elevation,
        lane_width_cm=configured_width,
        geometry_width_cm=geometry_width,
        intersection_half_extent_m=half_extent,
        approach_extent_m=approach_extent,
        layer_type=layer_type,
    )
    _validate_layout_offsets(map_settings)

    spat_data = _mapping(document["spat"], "spat")
    _check_keys(spat_data, {"movements", "messageInterval", "status"}, {"movements"}, "spat")
    interval = _positive_number(
        spat_data.get("messageInterval", DEFAULT_INTERVAL), "spat.messageInterval"
    )
    if interval < DEFAULT_INTERVAL:
        raise UserInputError("spat.messageInterval: the shortest supported interval is 0.1 seconds")
    interval_milliseconds = interval * 1000
    if interval_milliseconds != interval_milliseconds.to_integral_value():
        raise UserInputError(
            "spat.messageInterval: expected an interval representable in whole milliseconds"
        )
    interval_ms = int(interval_milliseconds)
    status = _parse_status(spat_data.get("status", "0b0000000000000000"))

    movements_data = spat_data["movements"]
    if not isinstance(movements_data, list) or not movements_data:
        raise UserInputError("spat.movements: expected a non-empty array")
    if len(movements_data) > 255:
        raise UserInputError("spat.movements: at most 255 movements are supported")

    movements: list[Movement] = []
    schedules: list[tuple[int, ...]] = []
    group_to_path: dict[int, str] = {}
    batch_ticks: int | None = None
    interval_decimal = Decimal(interval_ms) / Decimal(1000)
    for movement_index, raw_movement in enumerate(movements_data):
        movement_path = f"spat.movements[{movement_index}]"
        movement_data = _mapping(raw_movement, movement_path)
        _check_keys(
            movement_data,
            {"name", "signalGroup", "phases"},
            {"name", "signalGroup", "phases"},
            movement_path,
        )
        name = _string(movement_data["name"], f"{movement_path}.name", descriptive=True)
        signal_group = _integer(
            movement_data["signalGroup"], f"{movement_path}.signalGroup", 1, 6
        )
        if signal_group in group_to_path:
            raise UserInputError(
                f"{movement_path}.signalGroup: ID {signal_group} is already used at "
                f"{group_to_path[signal_group]}"
            )
        group_to_path[signal_group] = f"{movement_path}.signalGroup"

        phases_data = movement_data["phases"]
        if not isinstance(phases_data, list) or not phases_data:
            raise UserInputError(f"{movement_path}.phases: expected a non-empty array")
        if len(phases_data) > 16:
            raise UserInputError(f"{movement_path}.phases: at most 16 phases are supported")
        phases: list[Phase] = []
        ends: list[int] = []
        elapsed_ticks = 0
        for phase_index, raw_phase in enumerate(phases_data):
            phase_path = f"{movement_path}.phases[{phase_index}]"
            phase_data = _mapping(raw_phase, phase_path)
            _check_keys(phase_data, {"phase", "duration"}, {"phase", "duration"}, phase_path)
            phase_name = _string(phase_data["phase"], f"{phase_path}.phase")
            if phase_name not in PHASES:
                supported = ", ".join(sorted(PHASES))
                raise UserInputError(
                    f"{phase_path}.phase: unsupported value; choose one of {supported}"
                )
            duration = _positive_number(phase_data["duration"], f"{phase_path}.duration")
            if duration > MAX_PHASE_DURATION:
                raise UserInputError(f"{phase_path}.duration: cannot exceed 3600 seconds")
            ticks = duration / interval_decimal
            if ticks != ticks.to_integral_value():
                raise UserInputError(
                    f"{phase_path}.duration: must be an exact multiple of spat.messageInterval"
                )
            elapsed_ticks += int(ticks)
            phases.append(Phase(phase_name, duration))
            ends.append(elapsed_ticks)

        if batch_ticks is None:
            batch_ticks = elapsed_ticks
        elif elapsed_ticks != batch_ticks:
            raise UserInputError(
                f"{movement_path}.phases: total duration must match the other movements"
            )
        movements.append(Movement(name, signal_group, tuple(phases)))
        schedules.append(tuple(ends))

    missing_groups = {1, 2, 3, 4} - set(group_to_path)
    if missing_groups:
        missing = ", ".join(
            f"{group} ({SIGNAL_GROUPS[group]})" for group in sorted(missing_groups)
        )
        raise UserInputError(
            "spat.movements: MAP through connections require signal-group IDs "
            f"{missing}; define a movement for each"
        )

    assert batch_ticks is not None
    return Configuration(
        include_timestamps=include_timestamps,
        intersection_id=intersection_id,
        intersection_name=intersection_name,
        map=map_settings,
        spat=SpatSettings(
            interval_ms=interval_ms,
            status=status,
            movements=tuple(movements),
            schedules=tuple(schedules),
            batch_ticks=batch_ticks,
        ),
    )


def validate_combined_output(configuration: Configuration) -> None:
    unsupported = [movement for movement in configuration.spat.movements if movement.signal_group in {5, 6}]
    if unsupported:
        groups = ", ".join(str(movement.signal_group) for movement in unsupported)
        raise UserInputError(
            "spat.movements: signal-group IDs 5 and 6 represent left turns, which "
            f"are unsupported when MAP and SPaT are generated together (found {groups})"
        )


def _layout_points(settings: MapSettings) -> dict[int, tuple[tuple[Decimal, Decimal], ...]]:
    width_half = Decimal(settings.geometry_width_cm) / Decimal(200)
    h = settings.intersection_half_extent_m
    a = settings.approach_extent_m
    return {
        1: ((-width_half, a), (-width_half, h)),
        2: ((width_half, h), (width_half, a)),
        3: ((a, width_half), (h, width_half)),
        4: ((h, -width_half), (a, -width_half)),
        5: ((width_half, -a), (width_half, -h)),
        6: ((-width_half, -h), (-width_half, -a)),
        7: ((-a, -width_half), (-h, -width_half)),
        8: ((-h, width_half), (-a, width_half)),
    }


def _lane_offsets(points: tuple[tuple[Decimal, Decimal], ...]) -> tuple[tuple[int, int], ...]:
    offsets: list[tuple[int, int]] = []
    previous_east = Decimal(0)
    previous_north = Decimal(0)
    for east, north in points:
        x = _round_integer((east - previous_east) * 100)
        y = _round_integer((north - previous_north) * 100)
        offsets.append((x, y))
        previous_east, previous_north = east, north
    return tuple(offsets)


def _validate_layout_offsets(settings: MapSettings) -> None:
    for lane_id, points in _layout_points(settings).items():
        for x, y in _lane_offsets(points):
            if not NODE_OFFSET_MIN_CM <= x <= NODE_OFFSET_MAX_CM:
                raise UserInputError(
                    f"map.approachExtentM, map.intersectionHalfExtentM, or map.laneWidthCm: "
                    f"lane {lane_id} x offset {x} cm cannot be represented "
                    "by node-XY4 (range -4096 through 4095 cm)"
                )
            if not NODE_OFFSET_MIN_CM <= y <= NODE_OFFSET_MAX_CM:
                raise UserInputError(
                    f"map.approachExtentM, map.intersectionHalfExtentM, or map.laneWidthCm: "
                    f"lane {lane_id} y offset {y} cm cannot be represented "
                    "by node-XY4 (range -4096 through 4095 cm)"
                )


def bit_string(bit_positions: tuple[int, ...], width: int) -> tuple[int, int]:
    """Build a PyCrate BIT STRING value from ASN.1 bit positions."""
    value = 0
    for position in bit_positions:
        value |= 1 << (width - 1 - position)
    return value, width


def _map_lanes(settings: MapSettings) -> list[dict[str, Any]]:
    points_by_lane = _layout_points(settings)
    # The required signalized through links from the specification.
    through = {1: (6, 2), 3: (8, 4), 5: (2, 1), 7: (4, 3)}
    # The layout prose also permits unsignalized right turns. Destinations follow
    # the right-hand adjacent egress lane for each approach.
    right_turns = {1: 8, 3: 2, 5: 4, 7: 6}
    lane_names = {
        1: "North ingress",
        2: "North egress",
        3: "East ingress",
        4: "East egress",
        5: "South ingress",
        6: "South egress",
        7: "West ingress",
        8: "West egress",
    }
    approaches = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4}
    lanes: list[dict[str, Any]] = []
    for lane_id in range(1, 9):
        is_ingress = lane_id in through
        lane: dict[str, Any] = {
            "laneID": lane_id,
            "name": lane_names[lane_id],
            "laneAttributes": {
                "directionalUse": bit_string((0,) if is_ingress else (1,), 2),
                "sharedWith": (0, 10),
                "laneType": ("vehicle", (0, 8)),
            },
            "nodeList": (
                "nodes",
                [
                    {
                        "delta": ("node-XY4", {"x": x, "y": y})
                    }
                    for x, y in _lane_offsets(points_by_lane[lane_id])
                ],
            ),
        }
        if is_ingress:
            lane["ingressApproach"] = approaches[lane_id]
            lane["maneuvers"] = bit_string((0, 2), 12)
            destination, signal_group = through[lane_id]
            lane["connectsTo"] = [
                {
                    "connectingLane": {
                        "lane": destination,
                        "maneuver": bit_string((0,), 12),
                    },
                    "signalGroup": signal_group,
                },
                {
                    "connectingLane": {
                        "lane": right_turns[lane_id],
                        "maneuver": bit_string((2,), 12),
                    }
                },
            ]
        else:
            lane["egressApproach"] = approaches[lane_id]
        lanes.append(lane)
    return lanes


def _minute_of_year(moment: datetime) -> int:
    return (moment.timetuple().tm_yday - 1) * 1440 + moment.hour * 60 + moment.minute


def _dsecond(moment: datetime) -> int:
    return moment.second * 1000 + moment.microsecond // 1000


def _time_mark(moment: datetime) -> int:
    """Round a phase end to the nearest tenth within its UTC hour."""
    elapsed_microseconds = (
        ((moment.minute * 60 + moment.second) * 1_000_000) + moment.microsecond
    )
    tenths = (elapsed_microseconds + 50_000) // 100_000
    # An exact rounded hour boundary is represented as 00:00.0 in the next hour.
    return tenths % 36_000


def _timestamp_fields(moment: datetime) -> dict[str, int]:
    return {
        "moy": _minute_of_year(moment),
        "timeStamp": _dsecond(moment),
    }


def encode_map(configuration: Configuration, start_time: datetime) -> bytes:
    moment = start_time.astimezone(timezone.utc)
    intersection: dict[str, Any] = {
        "name": configuration.intersection_name,
        "id": {"id": configuration.intersection_id},
        "revision": 0,
        "refPoint": {
            "lat": configuration.map.latitude,
            "long": configuration.map.longitude,
        },
        "laneSet": _map_lanes(configuration.map),
    }
    if configuration.map.elevation is not None:
        intersection["refPoint"]["elevation"] = configuration.map.elevation
    if configuration.map.lane_width_cm is not None:
        intersection["laneWidth"] = configuration.map.lane_width_cm

    map_value: dict[str, Any] = {
        "msgIssueRevision": 0,
        "layerType": configuration.map.layer_type,
        "layerID": 0,
        "intersections": [intersection],
    }
    if configuration.include_timestamps:
        map_value["timeStamp"] = _minute_of_year(moment)
    try:
        j2735.MapData.MapData.set_val(map_value)
        return j2735.MapData.MapData.to_uper()
    except Exception:
        raise MessageEncodingError(
            "could not encode MAP; check that the configuration fits the supported J2735 profile"
        ) from None


def generate_spat_messages(
    configuration: Configuration, start_time: datetime
) -> Iterator[bytes]:
    """Yield one complete top-level SPAT UPER message per sample time."""
    if start_time.tzinfo is None:
        raise UserInputError("start time must include a timezone")
    start = start_time.astimezone(timezone.utc)
    interval = configuration.spat.interval_ms
    settings = configuration.spat
    for sample_tick in range(settings.batch_ticks):
        sample_time = start + timedelta(milliseconds=interval * sample_tick)
        movement_states: list[dict[str, Any]] = []
        for movement, schedule in zip(settings.movements, settings.schedules):
            phase_index = next(
                index for index, end_tick in enumerate(schedule) if sample_tick < end_tick
            )
            phase = movement.phases[phase_index]
            phase_end = start + timedelta(milliseconds=interval * schedule[phase_index])
            movement_states.append(
                {
                    "movementName": movement.name,
                    "signalGroup": movement.signal_group,
                    "state-time-speed": [
                        {
                            "eventState": phase.name,
                            "timing": {"minEndTime": _time_mark(phase_end)},
                        }
                    ],
                }
            )

        intersection: dict[str, Any] = {
            "name": configuration.intersection_name,
            "id": {"id": configuration.intersection_id},
            "revision": sample_tick % 128,
            "status": (settings.status, 16),
            "states": movement_states,
        }
        frame: dict[str, Any] = {"intersections": [intersection]}
        if configuration.include_timestamps:
            intersection.update(_timestamp_fields(sample_time))
            frame["timeStamp"] = _minute_of_year(sample_time)
        try:
            j2735.SPAT.SPAT.set_val(frame)
            yield j2735.SPAT.SPAT.to_uper()
        except Exception:
            raise MessageEncodingError(
                "could not encode SPaT; check that the configuration fits the supported J2735 profile"
            ) from None


def decode_spat(hex_text: str) -> dict[str, Any]:
    """Decode a raw hexadecimal J2735 SPAT UPER message."""
    compact = "".join(hex_text.split())
    if not compact:
        raise UserInputError("message contains no hexadecimal data")
    try:
        encoded = bytes.fromhex(compact)
    except ValueError as error:
        raise UserInputError(f"invalid hexadecimal message: {error}") from None
    try:
        j2735.SPAT.SPAT.from_uper(encoded)
        decoded = j2735.SPAT.SPAT.get_val()
    except Exception:
        raise UserInputError(
            "cannot decode message as a raw J2735 SPAT UPER frame"
        ) from None
    if not isinstance(decoded, dict) or not isinstance(decoded.get("intersections"), list):
        raise UserInputError("decoded value is not a top-level J2735 SPAT frame")
    return decoded
