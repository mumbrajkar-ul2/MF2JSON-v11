#!/usr/bin/env python3
"""Validate an Integration Spec research YAML artifact.

Usage:
    python tools/validate_research.py path/to/research.yaml
    python tools/validate_research.py path/to/research.yaml --integration-root path/to/integration-project
    python tools/validate_research.py path/to/research.yaml --skip-sha256

Exits 0 on success, 1 on validation failure.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import jsonschema
import yaml

LIBRARY_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = LIBRARY_ROOT / "schemas" / "integration-research.schema.json"
MANIFEST_PATH = LIBRARY_ROOT / "MANIFEST.yaml"
DEFAULT_DE_CSV = LIBRARY_ROOT / "rules" / "eligibility" / "data-elements.csv"
VVL_DIR = LIBRARY_ROOT / "rules" / "eligibility" / "value-lists"


def load_manifest() -> dict:
    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_de_ids(csv_path: Path) -> set[str]:
    ids: set[str] = set()
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            de = (row.get("System DE Number") or "").strip()
            if de:
                ids.add(de)
    return ids


def load_vvl_csv(filename: str) -> dict[tuple[str, str], dict[str, str]]:
    """Map (code, description) -> full row from VVL CSV."""
    path = VVL_DIR / filename
    if not path.is_file():
        return {}
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row.get("code", "").strip(), row.get("description", "").strip())
            rows[key] = row
    return rows


def resolve_source_path(integration_root: Path | None, rel_path: str) -> Path | None:
    if integration_root is not None:
        candidate = integration_root / rel_path
        if candidate.is_file():
            return candidate
    candidate = Path(rel_path)
    if candidate.is_file():
        return candidate
    return None


def validate_research(
    data: dict,
    *,
    integration_root: Path | None,
    skip_sha256: bool,
    de_ids: set[str],
) -> list[str]:
    errors: list[str] = []

    manifest = load_manifest()
    expected_version = None
    for rule_set in manifest.get("rule_sets", []):
        version = rule_set.get("source", {}).get("dictionary_version")
        if version:
            expected_version = version
            break

    meta = data.get("meta", {})
    if expected_version and meta.get("dictionary_version") != expected_version:
        errors.append(
            f"meta.dictionary_version '{meta.get('dictionary_version')}' "
            f"does not match MANIFEST.yaml '{expected_version}'"
        )

    assumptions = data.get("assumptions", [])
    if assumptions:
        errors.append(
            f"assumptions must be empty at research time; found {len(assumptions)} entry(ies)"
        )

    source_fields: list[str] = []
    target_attrs: list[str] = []
    for idx, mapping in enumerate(data.get("field_mappings", [])):
        sf = mapping.get("source_field", "")
        ta = mapping.get("target_attribute", "")
        source_fields.append(sf)
        target_attrs.append(ta)

        if not (mapping.get("source_ref") or "").strip():
            errors.append(f"field_mappings[{idx}] missing source_ref for {sf!r}")
        if not (mapping.get("target_ref") or "").strip():
            errors.append(f"field_mappings[{idx}] missing target_ref for {sf!r}")

        rule = mapping.get("t_msis_rule")
        if rule and rule not in de_ids:
            errors.append(f"field_mappings[{idx}] t_msis_rule {rule!r} not in data-elements.csv")

    for label, values in (("source_field", source_fields), ("target_attribute", target_attrs)):
        seen: set[str] = set()
        for val in values:
            if val in seen:
                errors.append(f"duplicate {label}: {val!r}")
            seen.add(val)

    for src in meta.get("sources", []):
        rel = src.get("path", "")
        expected_hash = (src.get("sha256") or "").lower()
        if skip_sha256:
            continue
        resolved = resolve_source_path(integration_root, rel)
        if resolved is None:
            errors.append(f"meta.sources path not found on disk: {rel!r}")
            continue
        actual = sha256_file(resolved)
        if actual != expected_hash:
            errors.append(
                f"SHA-256 mismatch for {rel}: expected {expected_hash}, got {actual}"
            )

    for vvl_idx, vvl in enumerate(data.get("vvl_members", [])):
        filename = vvl.get("file", "")
        csv_rows = load_vvl_csv(filename)
        if not csv_rows and filename:
            errors.append(f"vvl_members[{vvl_idx}] file not found: {filename!r}")

        for row_idx, row in enumerate(vvl.get("rows", [])):
            code = row.get("code", "").strip()
            desc = row.get("description", "").strip()
            if not (row.get("source_ref") or "").strip():
                errors.append(
                    f"vvl_members[{vvl_idx}].rows[{row_idx}] missing source_ref for code {code!r}"
                )
            csv_row = csv_rows.get((code, desc))
            if filename and csv_rows and csv_row is None:
                errors.append(
                    f"vvl_members[{vvl_idx}] row ({code!r}, {desc!r}) "
                    f"not found verbatim in {filename}"
                )
            elif csv_row:
                de = vvl.get("de", "")
                csv_de = (csv_row.get("t_msis_data_element") or "").strip()
                if de and csv_de and de != csv_de:
                    errors.append(
                        f"vvl_members[{vvl_idx}] de {de!r} != CSV t_msis_data_element {csv_de!r}"
                    )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Integration Spec research YAML.")
    parser.add_argument("research_yaml", type=Path, help="Path to research YAML file")
    parser.add_argument(
        "--integration-root",
        type=Path,
        default=None,
        help="Integration project root for resolving meta.sources paths and SHA-256",
    )
    parser.add_argument(
        "--skip-sha256",
        action="store_true",
        help="Skip SHA-256 verification of meta.sources (useful for fixtures)",
    )
    parser.add_argument(
        "--de-csv",
        type=Path,
        default=DEFAULT_DE_CSV,
        help="Path to data-elements.csv for t_msis_rule validation",
    )
    args = parser.parse_args(argv)

    if not args.research_yaml.is_file():
        print(f"error: file not found: {args.research_yaml}", file=sys.stderr)
        return 1

    integration_root = args.integration_root
    if integration_root is None:
        integration_root = args.research_yaml.resolve().parent.parent

    with args.research_yaml.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    schema = load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if schema_errors:
        print("JSON Schema validation failed:", file=sys.stderr)
        for err in schema_errors:
            path = ".".join(str(p) for p in err.path) or "(root)"
            print(f"  {path}: {err.message}", file=sys.stderr)
        return 1

    de_ids = load_de_ids(args.de_csv)
    semantic_errors = validate_research(
        data,
        integration_root=integration_root,
        skip_sha256=args.skip_sha256,
        de_ids=de_ids,
    )
    if semantic_errors:
        print("Semantic validation failed:", file=sys.stderr)
        for msg in semantic_errors:
            print(f"  {msg}", file=sys.stderr)
        return 1

    print(f"OK: {args.research_yaml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
