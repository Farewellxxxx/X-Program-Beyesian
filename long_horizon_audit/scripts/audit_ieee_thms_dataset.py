from __future__ import annotations

import hashlib
import hmac
import csv
import io
from collections import Counter
from pathlib import Path, PurePosixPath
import json
import re
import statistics
from typing import Any, Mapping
import zipfile

from openpyxl import load_workbook


_DIRECT_IDENTIFIER_PATTERNS = (
    "姓名",
    "名字",
    "name",
    "ip地址",
    "ip_address",
    "ip",
    "device_id",
    "deviceid",
    "设备id",
    "设备号",
)

_GROUP_PATTERNS = ("组别", "group", "组")

_CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def _chinese_integer(text: str) -> int | None:
    if not text:
        return None
    if text == "十":
        return 10
    if "十" in text:
        left, right = text.split("十", 1)
        tens = _CHINESE_DIGITS.get(left, 1 if left == "" else None)
        ones = _CHINESE_DIGITS.get(right, 0 if right == "" else None)
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    if len(text) == 1:
        return _CHINESE_DIGITS.get(text)
    return None


def normalize_group_label(value: Any) -> int | None:
    if value is None:
        return None
    text = re.sub(r"\s+", "", str(value)).strip()
    if not text:
        return None
    text = text.removeprefix("第").removesuffix("组")
    digit_match = re.fullmatch(r"\d+", text)
    if digit_match:
        return int(text)
    return _chinese_integer(text)


def _normalized_key(name: Any) -> str:
    return re.sub(r"[\s_\-]+", "", str(name)).casefold()


def _is_direct_identifier(name: Any) -> bool:
    normalized = _normalized_key(name)
    return any(_normalized_key(pattern) in normalized for pattern in _DIRECT_IDENTIFIER_PATTERNS)


def _is_group_field(name: Any) -> bool:
    normalized = _normalized_key(name)
    return (
        "组别" in normalized
        or normalized == "组"
        or normalized == "group"
        or normalized.endswith("group")
    )


def safe_public_record(record: Mapping[str, Any], salt: bytes) -> dict[str, Any]:
    identifiers: list[str] = []
    public: dict[str, Any] = {}
    group_id: int | None = None

    for key, value in record.items():
        if _is_direct_identifier(key):
            if value is not None and str(value).strip():
                identifiers.append(f"{_normalized_key(key)}={str(value).strip()}")
            continue
        if _is_group_field(key):
            group_id = normalize_group_label(value)
            continue
        public[str(key)] = value

    source = "\x1f".join(sorted(identifiers)).encode("utf-8")
    participant_key = hmac.new(salt, source, hashlib.sha256).hexdigest()[:16]
    return {
        "participant_key": participant_key,
        "group_id": group_id,
        **public,
    }


def repair_zip_name(name: str) -> str:
    try:
        return name.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name


def _decode_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def profile_csv_bytes(raw: bytes) -> dict[str, Any]:
    text = _decode_csv(raw)
    reader = csv.DictReader(io.StringIO(text))
    columns = [str(name) for name in (reader.fieldnames or [])]
    rows = list(reader)
    missing_cells = sum(
        value is None or str(value).strip() == ""
        for row in rows
        for value in row.values()
    )

    elapsed_name = next(
        (
            name
            for name in columns
            if _normalized_key(name)
            in {"secondselapsed", "elapsedseconds", "elapsedtime", "seconds"}
        ),
        None,
    )
    elapsed: list[float] = []
    if elapsed_name is not None:
        for row in rows:
            try:
                elapsed.append(float(str(row[elapsed_name]).strip()))
            except (TypeError, ValueError):
                continue
    deltas = [
        later - earlier
        for earlier, later in zip(elapsed, elapsed[1:])
        if later > earlier
    ]
    median_dt_s = statistics.median(deltas) if deltas else None
    sampling_hz = 1.0 / median_dt_s if median_dt_s else None
    return {
        "row_count": len(rows),
        "columns": columns,
        "missing_cells": missing_cells,
        "median_dt_s": median_dt_s,
        "sampling_hz": sampling_hz,
    }


def _is_macos_artifact(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        name.startswith("__MACOSX/")
        or path.name.startswith("._")
        or path.name.startswith("~$")
        or path.name == ".DS_Store"
    )


def archive_inventory(path: str | Path) -> dict[str, Any]:
    real_files = []
    macos_artifact_count = 0
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            repaired = repair_zip_name(info.filename)
            if _is_macos_artifact(repaired):
                macos_artifact_count += 1
                continue
            real_files.append((repaired, info))

    extensions = Counter(PurePosixPath(name).suffix.lower() for name, _ in real_files)
    return {
        "real_file_count": len(real_files),
        "macos_artifact_count": macos_artifact_count,
        "empty_annotation_count": sum(
            PurePosixPath(name).name.casefold() == "annotation.csv"
            and info.file_size == 0
            for name, info in real_files
        ),
        "nested_zip_count": sum(
            PurePosixPath(name).suffix.casefold() == ".zip"
            for name, _ in real_files
        ),
        "extensions": dict(sorted(extensions.items())),
    }


def _participant_key(value: Any, salt: bytes) -> str | None:
    normalized = re.sub(r"\s+", "", str(value or "")).casefold()
    if not normalized:
        return None
    return hmac.new(salt, normalized.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unit_status(sensor_type: str, column: str) -> str:
    normalized = _normalized_key(column)
    if normalized == "secondselapsed":
        return "seconds (header semantics)"
    if normalized == "time":
        return "timestamp unit not declared"
    if normalized in {"x", "y", "z"}:
        if "accelerometer" in sensor_type.casefold() or "gravity" in sensor_type.casefold():
            return "unit not declared in CSV header"
        if "gyroscope" in sensor_type.casefold():
            return "unit not declared in CSV header"
        if "location" in sensor_type.casefold():
            return "coordinate meaning not declared in CSV header"
    return "not declared"


def _profile_workbook(
    raw: bytes,
    source_name: str,
    salt: bytes,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    Counter[str],
    Counter[str],
    list[tuple[str, set[str]]],
]:
    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    dictionary_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    normalized_groups: Counter[str] = Counter()
    group_variants: Counter[str] = Counter()
    participant_key_sets: list[tuple[str, set[str]]] = []

    for sheet in workbook.worksheets:
        values = list(sheet.iter_rows(values_only=True))
        if not values:
            continue
        headers = [str(value or "").strip() for value in values[0]]
        records = [
            dict(zip(headers, row))
            for row in values[1:]
            if any(value not in (None, "") for value in row)
        ]
        direct_columns = [name for name in headers if _is_direct_identifier(name)]
        name_columns = [
            name
            for name in direct_columns
            if "ip" not in _normalized_key(name)
            and "device" not in _normalized_key(name)
            and "设备" not in _normalized_key(name)
        ]
        name_cardinality = {
            name: len(
                {
                    re.sub(r"\s+", "", str(record.get(name) or "")).casefold()
                    for record in records
                    if str(record.get(name) or "").strip()
                }
            )
            for name in name_columns
        }
        participant_column = (
            max(name_cardinality, key=name_cardinality.get)
            if name_cardinality
            else None
        )
        participant_keys = {
            key
            for record in records
            if participant_column is not None
            for key in [_participant_key(record.get(participant_column), salt)]
            if key is not None
        }
        participant_key_sets.append(
            (f"{source_name}:{sheet.title}", participant_keys)
        )

        group_columns = [name for name in headers if _is_group_field(name)]
        for group_column in group_columns:
            for record in records:
                raw_group = str(record.get(group_column) or "").strip()
                if not raw_group:
                    continue
                group_variants[raw_group] += 1
                normalized = normalize_group_label(raw_group)
                normalized_groups[str(normalized) if normalized is not None else "unparsed"] += 1

        for column in headers:
            values_in_column = [record.get(column) for record in records]
            missing = sum(value is None or str(value).strip() == "" for value in values_in_column)
            pii_class = (
                "direct_identifier"
                if _is_direct_identifier(column)
                else "quasi_identifier"
                if any(token in _normalized_key(column) for token in ("年龄", "性别", "age", "gender"))
                else "none"
            )
            dictionary_rows.append(
                {
                    "source_type": "questionnaire",
                    "source_name": source_name,
                    "table_or_sensor": sheet.title,
                    "column_name": column,
                    "row_count": len(records),
                    "missing_count": missing,
                    "unique_count": len(
                        {
                            str(value).strip()
                            for value in values_in_column
                            if value is not None and str(value).strip()
                        }
                    ),
                    "pii_class": pii_class,
                    "unit_status": "question wording / value labels require protocol",
                    "notes": "values not exported",
                }
            )

        summaries.append(
            {
                "source_name": source_name,
                "sheet": sheet.title,
                "row_count": len(records),
                "column_count": len(headers),
                "direct_identifier_columns": direct_columns,
                "participant_key_source": participant_column,
                "unique_participant_keys": len(participant_keys),
                "duplicate_or_repeat_rows_by_participant_key": (
                    len(records) - len(participant_keys)
                    if participant_column is not None
                    else None
                ),
                "missing_cells": sum(
                    value is None or str(value).strip() == ""
                    for record in records
                    for value in record.values()
                ),
            }
        )

    return (
        dictionary_rows,
        summaries,
        normalized_groups,
        group_variants,
        participant_key_sets,
    )


def audit_dataset(
    archive_path: str | Path,
    output_dir: str | Path,
    *,
    salt: bytes,
) -> dict[str, Any]:
    archive_path = Path(archive_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory = archive_inventory(archive_path)
    dictionary_rows: list[dict[str, Any]] = []
    questionnaire_summaries: list[dict[str, Any]] = []
    normalized_groups: Counter[str] = Counter()
    group_variants: Counter[str] = Counter()
    sensor_profiles: list[dict[str, Any]] = []
    nested_archives: list[dict[str, Any]] = []
    sensor_session_ids: set[int] = set()
    sensor_session_file_hashes: dict[int, list[tuple[str, str]]] = {}
    questionnaire_key_sets: list[tuple[str, set[str]]] = []

    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = repair_zip_name(info.filename)
            if _is_macos_artifact(name):
                continue
            path = PurePosixPath(name)
            suffix = path.suffix.casefold()

            if suffix == ".xlsx":
                (
                    workbook_dictionary,
                    summaries,
                    groups,
                    variants,
                    key_sets,
                ) = _profile_workbook(archive.read(info), path.name, salt)
                dictionary_rows.extend(workbook_dictionary)
                questionnaire_summaries.extend(summaries)
                normalized_groups.update(groups)
                group_variants.update(variants)
                questionnaire_key_sets.extend(key_sets)
                continue

            if suffix == ".zip":
                nested_raw = archive.read(info)
                try:
                    with zipfile.ZipFile(io.BytesIO(nested_raw)) as nested:
                        nested_files = [item for item in nested.infolist() if not item.is_dir()]
                        nested_archives.append(
                            {
                                "file_name": path.name,
                                "file_count": len(nested_files),
                                "uncompressed_bytes": sum(item.file_size for item in nested_files),
                                "extensions": dict(
                                    sorted(
                                        Counter(
                                            PurePosixPath(item.filename).suffix.casefold()
                                            for item in nested_files
                                        ).items()
                                    )
                                ),
                            }
                        )
                except zipfile.BadZipFile:
                    nested_archives.append(
                        {
                            "file_name": path.name,
                            "error": "invalid nested ZIP",
                        }
                    )
                continue

            if suffix != ".csv":
                continue

            group_id = None
            for part in path.parts:
                match = re.match(r"^(\d{1,3})(?:\D|$)", part)
                if match:
                    candidate = int(match.group(1))
                    if 0 < candidate < 100:
                        group_id = candidate
            if group_id is not None:
                sensor_session_ids.add(group_id)
            raw_csv = archive.read(info)
            if group_id is not None:
                sensor_session_file_hashes.setdefault(group_id, []).append(
                    (
                        path.name.casefold(),
                        hashlib.sha256(raw_csv).hexdigest(),
                    )
                )

            if path.name.casefold() == "annotation.csv":
                continue

            profile = profile_csv_bytes(raw_csv)
            sensor_type = path.stem
            sensor_profiles.append(
                {
                    "group_id": group_id,
                    "sensor_type": sensor_type,
                    "row_count": profile["row_count"],
                    "column_count": len(profile["columns"]),
                    "columns": ";".join(profile["columns"]),
                    "missing_cells": profile["missing_cells"],
                    "median_dt_s": profile["median_dt_s"],
                    "sampling_hz": profile["sampling_hz"],
                    "compressed_bytes": info.compress_size,
                    "uncompressed_bytes": info.file_size,
                }
            )
            for column in profile["columns"]:
                dictionary_rows.append(
                    {
                        "source_type": "sensor",
                        "source_name": "IEEE_THMS dataset.zip",
                        "table_or_sensor": sensor_type,
                        "column_name": column,
                        "row_count": profile["row_count"],
                        "missing_count": "",
                        "unique_count": "",
                        "pii_class": "none",
                        "unit_status": _unit_status(sensor_type, column),
                        "notes": f"group_id={group_id}; repeated schema row",
                    }
                )

    group_rows = [
        {
            "raw_group_label": raw_group,
            "normalized_group_id": normalize_group_label(raw_group),
            "record_count": count,
            "status": "parsed" if normalize_group_label(raw_group) is not None else "unparsed",
        }
        for raw_group, count in sorted(group_variants.items())
    ]

    dictionary_fieldnames = [
        "source_type",
        "source_name",
        "table_or_sensor",
        "column_name",
        "row_count",
        "missing_count",
        "unique_count",
        "pii_class",
        "unit_status",
        "notes",
    ]
    sensor_fieldnames = [
        "group_id",
        "sensor_type",
        "row_count",
        "column_count",
        "columns",
        "missing_cells",
        "median_dt_s",
        "sampling_hz",
        "compressed_bytes",
        "uncompressed_bytes",
    ]
    _write_csv(
        output_dir / "dataset_dictionary.csv",
        dictionary_rows,
        dictionary_fieldnames,
    )
    _write_csv(
        output_dir / "sensor_file_profiles.csv",
        sensor_profiles,
        sensor_fieldnames,
    )
    _write_csv(
        output_dir / "group_normalization.csv",
        group_rows,
        ["raw_group_label", "normalized_group_id", "record_count", "status"],
    )

    pairwise_linkage = []
    for index, (source_a, keys_a) in enumerate(questionnaire_key_sets):
        for source_b, keys_b in questionnaire_key_sets[index + 1 :]:
            pairwise_linkage.append(
                {
                    "source_a": source_a,
                    "source_b": source_b,
                    "unique_keys_a": len(keys_a),
                    "unique_keys_b": len(keys_b),
                    "exact_overlap": len(keys_a & keys_b),
                    "only_a": len(keys_a - keys_b),
                    "only_b": len(keys_b - keys_a),
                }
            )

    fingerprints: dict[str, list[int]] = {}
    for group_id, file_hashes in sensor_session_file_hashes.items():
        canonical = "\n".join(
            f"{name}:{content_hash}"
            for name, content_hash in sorted(file_hashes)
        )
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        fingerprints.setdefault(fingerprint, []).append(group_id)
    duplicate_sensor_session_groups = sorted(
        sorted(group_ids)
        for group_ids in fingerprints.values()
        if len(group_ids) > 1
    )

    summary: dict[str, Any] = {
        "archive_sha256": _sha256_path(archive_path),
        "inventory": inventory,
        "questionnaires": questionnaire_summaries,
        "questionnaire_name_linkage": {
            "method": "Unicode whitespace/case normalization followed by audit-only HMAC; no values or keys exported",
            "pairwise": pairwise_linkage,
        },
        "normalized_group_counts": dict(sorted(normalized_groups.items())),
        "sensor_session_ids": sorted(sensor_session_ids),
        "sensor_session_count": len(sensor_session_ids),
        "sensor_file_count": len(sensor_profiles),
        "duplicate_sensor_session_groups": duplicate_sensor_session_groups,
        "nested_archives": nested_archives,
        "output_files": [
            "dataset_dictionary.csv",
            "sensor_file_profiles.csv",
            "group_normalization.csv",
            "dataset_audit_summary.json",
        ],
        "privacy": {
            "raw_identifier_values_exported": False,
            "participant_keys_exported": False,
            "direct_identifier_columns_named_for_risk_classification": True,
        },
    }
    (output_dir / "dataset_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Read-only aggregate audit for IEEE_THMS dataset.zip"
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--salt",
        required=True,
        help="Audit-only salt; raw identifiers and participant keys are never exported.",
    )
    args = parser.parse_args()
    summary = audit_dataset(
        args.archive,
        args.output_dir,
        salt=args.salt.encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "questionnaire_tables": len(summary["questionnaires"]),
                "sensor_sessions": summary["sensor_session_count"],
                "sensor_files": summary["sensor_file_count"],
                "outputs": summary["output_files"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
