"""Command-line interface for MAP/SPaT generation and SPaT inspection."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .core import (
    Configuration,
    MessageEncodingError,
    UserInputError,
    decode_spat,
    encode_map,
    generate_spat_messages,
    load_configuration,
    validate_combined_output,
)


@dataclass
class _OutputJob:
    path: Path
    description: str
    write: Callable[[Any], None]


@dataclass
class _StagedFile:
    destination: Path
    temporary: Path
    description: str
    backup: Path | None = None


def _binary_job(path: Path, description: str, chunks: Iterable[bytes]) -> _OutputJob:
    def write(stream: Any) -> None:
        for chunk in chunks:
            stream.write(chunk.hex().encode("ascii"))
            stream.write(b"\n")

    return _OutputJob(path, description, write)


def _stage_outputs(jobs: list[_OutputJob]) -> list[_StagedFile]:
    """Write all outputs to sibling temporary files before replacing destinations."""
    resolved = [job.path.resolve() for job in jobs]
    if len(set(resolved)) != len(resolved):
        raise UserInputError("MAP and SPaT output paths must be different")

    staged: list[_StagedFile] = []
    try:
        for job in jobs:
            try:
                job.path.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{job.path.name}.", suffix=".tmp", dir=job.path.parent
                )
                temporary = Path(temporary_name)
                staged_file = _StagedFile(job.path, temporary, job.description)
                staged.append(staged_file)
                with os.fdopen(descriptor, "wb") as stream:
                    job.write(stream)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as error:
                raise UserInputError(
                    f"writing output {job.path}: {error.strerror or error}"
                ) from None
            except (MessageEncodingError, UserInputError):
                raise
            except Exception as error:
                raise MessageEncodingError(f"writing {job.description}: {error}") from None

        # Save existing destinations so a failed multi-file commit can roll back
        # any output already replaced earlier in the commit sequence.
        for item in staged:
            if item.destination.exists() and item.destination.is_file():
                try:
                    descriptor, backup_name = tempfile.mkstemp(
                        prefix=f".{item.destination.name}.",
                        suffix=".backup",
                        dir=item.destination.parent,
                    )
                    os.close(descriptor)
                    item.backup = Path(backup_name)
                    shutil.copy2(item.destination, item.backup)
                except OSError as error:
                    raise UserInputError(
                        f"reading existing output {item.destination} before replacement: "
                        f"{error.strerror or error}"
                    ) from None

        committed: list[_StagedFile] = []
        try:
            for item in staged:
                os.replace(item.temporary, item.destination)
                committed.append(item)
        except OSError as error:
            rollback_errors: list[str] = []
            for item in reversed(committed):
                try:
                    if item.backup is not None:
                        os.replace(item.backup, item.destination)
                        item.backup = None
                    else:
                        item.destination.unlink(missing_ok=True)
                except OSError as rollback_error:
                    rollback_errors.append(
                        f"could not restore {item.destination}: "
                        f"{rollback_error.strerror or rollback_error}"
                    )
            detail = f"writing output {item.destination}: {error.strerror or error}"
            if rollback_errors:
                detail += "; " + "; ".join(rollback_errors)
                detail += "; backup files were retained where restoration failed"
            raise UserInputError(detail) from None
        for item in staged:
            if item.backup is not None:
                try:
                    item.backup.unlink(missing_ok=True)
                    item.backup = None
                except OSError:
                    # The new destination is already committed; a leftover
                    # backup is harmless and can be removed by the user.
                    pass
        return staged
    except (OSError, UserInputError, MessageEncodingError):
        raise
    finally:
        for item in staged:
            try:
                item.temporary.unlink(missing_ok=True)
            except OSError:
                pass
            if item.backup is not None:
                # If rollback left the backup in place, keep it available for
                # manual recovery instead of deleting the only old copy.
                committed_destination_changed = (
                    item.destination.exists()
                    and item.temporary.exists() is False
                    and item.backup.exists()
                )
                if not committed_destination_changed:
                    try:
                        item.backup.unlink(missing_ok=True)
                    except OSError:
                        pass


def _reject_source_overwrite(source: Path, targets: list[Path]) -> None:
    source_resolved = source.resolve()
    for target in targets:
        if target.resolve() == source_resolved:
            raise UserInputError(f"output path {target} is the same as input file {source}")


def _run_generation(args: argparse.Namespace) -> int:
    configuration: Configuration = load_configuration(args.config)
    start_time = datetime.now(timezone.utc)

    if args.operation == "map":
        _reject_source_overwrite(args.config, [args.output])
        encoded_map = encode_map(configuration, start_time)
        _stage_outputs([_binary_job(args.output, "MAP output", [encoded_map])])
        print(f"MAP UPER message written to {args.output}")
        return 0

    if args.operation == "spat":
        _reject_source_overwrite(args.config, [args.output])
        messages = generate_spat_messages(configuration, start_time)
        _stage_outputs([_binary_job(args.output, "SPaT output", messages)])
        print(f"SPaT batch written to {args.output}")
        return 0

    try:
        validate_combined_output(configuration)
    except UserInputError as error:
        raise UserInputError(f"{args.config}: {error}") from None
    _reject_source_overwrite(args.config, [args.map_output, args.spat_output])
    map_bytes = encode_map(configuration, start_time)
    spat_messages = generate_spat_messages(configuration, start_time)
    jobs = [
        _binary_job(args.map_output, "MAP output", [map_bytes]),
        _binary_job(args.spat_output, "SPaT output", spat_messages),
    ]
    _stage_outputs(jobs)
    print(f"MAP UPER message written to {args.map_output}")
    print(f"SPaT batch written to {args.spat_output}")
    return 0


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, bytes):
        return value.hex()
    return value


def _format_message_time(minute_of_year: Any, dsecond: Any) -> str:
    if (
        isinstance(minute_of_year, bool)
        or not isinstance(minute_of_year, int)
        or isinstance(dsecond, bool)
        or not isinstance(dsecond, int)
    ):
        return "time unavailable"
    day_of_year = minute_of_year // 1440 + 1
    minute_of_day = minute_of_year % 1440
    hour, minute = divmod(minute_of_day, 60)
    seconds, milliseconds = divmod(dsecond, 1000)
    return f"DOY {day_of_year:03} {hour:02}:{minute:02}:{seconds:02}.{milliseconds:03} UTC"


def _format_time_mark(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 36_000:
        return str(value)
    minute, remaining = divmod(value, 600)
    second, tenth = divmod(remaining, 10)
    return f"{minute:02}:{second:02}.{tenth}"


def _summary(decoded: dict[str, Any], source: str) -> str:
    intersections = decoded.get("intersections", [])
    top_minute = decoded.get("timeStamp")
    reports: list[str] = []
    for intersection_index, intersection in enumerate(intersections, start=1):
        if not isinstance(intersection, dict):
            continue
        minute = intersection.get("moy", top_minute)
        time = _format_message_time(minute, intersection.get("timeStamp"))
        name = intersection.get("name") or f"Intersection {intersection_index}"
        movement_summaries: list[str] = []
        for movement in intersection.get("states", []):
            if not isinstance(movement, dict):
                continue
            movement_name = movement.get("movementName") or "Unnamed movement"
            events = movement.get("state-time-speed", [])
            if not events:
                movement_summaries.append(f"{movement_name}: state unavailable")
                continue
            for event in events:
                state = event.get("eventState", "state unavailable")
                timing = event.get("timing") or {}
                end = timing.get("minEndTime") if isinstance(timing, dict) else None
                if end is None:
                    movement_summaries.append(f"{movement_name}: {state}")
                else:
                    movement_summaries.append(
                        f"{movement_name}: {state} (minEndTime { _format_time_mark(end) })"
                    )
        summary = f"{source} | {time} | {name}"
        if movement_summaries:
            summary += " | " + " | ".join(movement_summaries)
        reports.append(summary)
    return " || ".join(reports) if reports else f"{source} | no intersection data"


def _atomic_json_write(path: Path, values: list[dict[str, Any]]) -> None:
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(_jsonable(values), stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except OSError as error:
        raise UserInputError(
            f"writing JSON output {path}: {error.strerror or error}"
        ) from None
    except (TypeError, ValueError) as error:
        raise UserInputError(f"writing JSON output {path}: {error}") from None


def _run_decode(args: argparse.Namespace) -> int:
    input_path: Path | None = None
    try:
        message_argument = args.message
        looks_like_hex = bool(message_argument) and all(
            char in "0123456789abcdefABCDEF \t\r\n\v\f" for char in message_argument
        )
        candidate = Path(message_argument) if not looks_like_hex else None
        if candidate is not None and candidate.is_file():
            input_path = candidate
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except OSError as error:
                raise UserInputError(
                    f"reading input {candidate}: {error.strerror or error}"
                ) from None
            except UnicodeError as error:
                raise UserInputError(
                    f"reading input {candidate}: file is not valid UTF-8 ({error})"
                ) from None
            decoded_messages: list[dict[str, Any]] = []
            errors: list[str] = []
            for line_number, line in enumerate(lines, start=1):
                if not line.strip():
                    continue
                try:
                    decoded = decode_spat(line)
                except UserInputError as error:
                    errors.append(f"line {line_number}: {error}")
                    continue
                decoded_messages.append(decoded)
                print(_summary(decoded, f"Line {line_number}"))
        else:
            decoded = decode_spat(args.message)
            decoded_messages = [decoded]
            errors = []
            print(_summary(decoded, "Message"))

        output_path = args.json_output
        if output_path is None:
            output_path = (
                Path("output") / f"{input_path.stem}_decoded.json"
                if input_path is not None
                else Path("output") / "decoded_spat.json"
            )
        if input_path is not None and output_path.resolve() == input_path.resolve():
            raise UserInputError(
                f"JSON output path {output_path} is the same as input file {input_path}"
            )
        _atomic_json_write(output_path, decoded_messages)
        print(f"Full decoded JSON written to {output_path}")
        if errors:
            for error in errors:
                print(f"error: {input_path}: {error}", file=sys.stderr)
            return 2
        return 0
    except (OSError, UserInputError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="v2x-project",
        description="Generate and inspect J2735 MAP and SPaT UPER messages.",
    )
    commands = parser.add_subparsers(dest="operation", required=True)

    for name, description in (
        ("map", "Generate one static MAP message from the unified JSON5 configuration."),
        ("spat", "Generate a complete SPaT batch from the unified JSON5 configuration."),
    ):
        command = commands.add_parser(name, description=description, help=description)
        command.add_argument("config", type=Path, help="unified JSON5 intersection configuration")
        command.add_argument(
            "output",
            type=Path,
            help="destination text file; one hex-encoded UPER message per line (overwritten)",
        )

    both = commands.add_parser(
        "both",
        description="Generate one MAP message and a SPaT batch from the same start time.",
        help="generate MAP and SPaT outputs together",
    )
    both.add_argument("config", type=Path, help="unified JSON5 intersection configuration")
    both.add_argument("--map-output", type=Path, required=True, help="MAP output file (overwritten)")
    both.add_argument(
        "--spat-output",
        type=Path,
        required=True,
        help="SPaT output file with one hex message per line (overwritten)",
    )

    decode = commands.add_parser(
        "decode",
        description="Decode raw top-level J2735 SPAT UPER messages for debugging.",
        help="decode a hex message or a file containing one message per line",
    )
    decode.add_argument(
        "message",
        help="hex-encoded message or path to a text file containing hex messages",
    )
    decode.add_argument(
        "--json-output",
        type=Path,
        help="decoded JSON destination (overwritten; defaults under output/)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.operation == "decode":
            return _run_decode(args)
        return _run_generation(args)
    except (OSError, UserInputError, MessageEncodingError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

