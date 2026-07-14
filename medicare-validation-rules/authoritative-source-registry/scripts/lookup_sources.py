#!/usr/bin/env python3
"""Filter authoritative Medicaid sources by entity, jurisdiction, or artifact type."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:
    print("Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REGISTRY_DIR = Path(__file__).resolve().parent.parent
YAML_PATH = REGISTRY_DIR / "source-url-registry.yaml"


def load_registry() -> dict:
    with YAML_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def domain_allowed(url: str, allowed: set[str]) -> bool:
    host = urlparse(url).hostname or ""
    return host.lower() in allowed


def _tags(values: list) -> list[str]:
    return [str(v).lower().replace("-", "_") for v in values]


def match_source(source: dict, args: argparse.Namespace) -> bool:
    if args.jurisdiction:
        j = args.jurisdiction.lower()
        if source.get("jurisdiction", "").lower() != j:
            return False
    if args.tier:
        if source.get("tier") != args.tier:
            return False
    if args.entity:
        entity = args.entity.lower().replace("-", "_")
        use_for = _tags(source.get("use_for", []))
        priority = _tags(source.get("priority_for", []))
        if entity not in use_for and entity not in priority:
            return False
    if args.artifact:
        artifact = args.artifact.lower().replace("-", "_")
        use_for = _tags(source.get("use_for", []))
        priority = _tags(source.get("priority_for", []))
        aliases = {
            "lov": "value_lists",
            "value_list": "value_lists",
            "vvl": "value_lists",
            "standard": "standard_updates",
            "rule": "rule_lookup",
        }
        needle = aliases.get(artifact, artifact)
        if needle not in use_for and needle not in priority:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity", help="Domain: member, provider, claims, plan, eligibility, etc.")
    parser.add_argument("--jurisdiction", choices=["federal", "virginia"])
    parser.add_argument("--artifact", help="lov, rule, standard, manual, regulation, file_layout")
    parser.add_argument("--tier", choices=["tier_1", "tier_2", "tier_3", "tier_4"])
    parser.add_argument("--list-domains", action="store_true", help="Print allowed domain allowlist")
    parser.add_argument("--validate-url", help="Check if a URL hostname is on the allowlist")
    args = parser.parse_args()

    reg = load_registry()
    allowed = {d.lower() for d in reg.get("allowed_domains", [])}

    if args.list_domains:
        for d in sorted(allowed):
            print(d)
        return 0

    if args.validate_url:
        ok = domain_allowed(args.validate_url, allowed)
        print("ALLOWED" if ok else "DENIED")
        return 0 if ok else 1

    sources = reg.get("sources", [])
    matched = [s for s in sources if match_source(s, args)]
    matched.sort(key=lambda s: (s.get("tier", ""), s.get("name", "")))

    print(json.dumps({"count": len(matched), "sources": matched}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
