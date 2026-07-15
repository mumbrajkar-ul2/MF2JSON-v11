#!/usr/bin/env python3
"""Generate a fixed-layout CSV from a COBOL copybook (.CPY).

Writes ``<stem>_generated.csv`` next to the copybook by default (or to ``--output``).

Byte-length rules (matching this project's MEMBERELIGIBILITY layout convention):

- Display (CHAR): length = digit count from PIC X(n) / 9(n) / S9(n)[Vn…]
- COMP-3: length = ceil((digits + 1) / 2)  (packed decimal with sign nibble)
- COMP (binary): 1–4 digits → 2 bytes, 5–9 → 4 bytes, 10–18 → 8 bytes

Usage:
    python tools/cpy_to_csv.py source/MEMBERELIGIBILITY.CPY
    python tools/cpy_to_csv.py source/MEMBERELIGIBILITY.CPY --compare source/MEMBERELIGIBILITY.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Elementary item: level, name, PIC clause (optional USAGE keywords folded into pic_raw)
FIELD_RE = re.compile(
    r"^\s*(\d{2})\s+"
    r"([\w-]+)\s+"
    r"PIC\s+(.+?)\s*\.\s*$",
    re.IGNORECASE,
)

PIC_TOKEN_RE = re.compile(
    r"""
    ^
    (?P<body>S?9(?:\(\d+\))?(?:V(?:9(?:\(\d+\))?)+)?|X(?:\(\d+\))?|[AX9]+)
    (?:\s+(?P<usage>COMP-3|COMP|COMPUTATIONAL-3|COMPUTATIONAL))?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class LayoutField:
    field_name: str
    picture: str
    storage: str
    start_pos: int
    end_pos: int
    length: int


def _expand_pic_digits(pic_body: str) -> int:
    """Count logical digits/characters in a PIC body (display size)."""
    body = pic_body.upper().replace(" ", "")
    # Parenthesized forms: X(08), 9(04), S9(7)V99
    total = 0
    i = 0
    while i < len(body):
        ch = body[i]
        if ch in {"S", "V"}:
            i += 1
            continue
        if ch in {"X", "A", "9"}:
            if i + 1 < len(body) and body[i + 1] == "(":
                close = body.index(")", i + 2)
                total += int(body[i + 2 : close])
                i = close + 1
            else:
                total += 1
                i += 1
            continue
        raise ValueError(f"Unsupported PIC character {ch!r} in {pic_body!r}")
    return total


def _normalize_usage(usage: str | None) -> str | None:
    if not usage:
        return None
    u = usage.upper()
    if u in {"COMP-3", "COMPUTATIONAL-3"}:
        return "COMP-3"
    if u in {"COMP", "COMPUTATIONAL"}:
        return "COMP"
    raise ValueError(f"Unsupported USAGE {usage!r}")


def _storage_and_length(pic_body: str, usage: str | None) -> tuple[str, int]:
    digits = _expand_pic_digits(pic_body)
    if usage == "COMP-3":
        return "COMP-3", math.ceil((digits + 1) / 2)
    if usage == "COMP":
        if 1 <= digits <= 4:
            return "COMP", 2
        if 5 <= digits <= 9:
            return "COMP", 4
        if 10 <= digits <= 18:
            return "COMP", 8
        raise ValueError(f"COMP digit count {digits} out of range for {pic_body!r}")
    return "CHAR", digits


def _format_picture(pic_body: str, usage: str | None) -> str:
    """Match existing CSV picture style: 'PIC X(08)' or 'PIC S9(7)V99 COMP-3'."""
    body = pic_body.strip()
    if usage:
        return f"PIC {body} {usage}"
    return f"PIC {body}"


def parse_copybook(text: str) -> list[LayoutField]:
    fields: list[LayoutField] = []
    pos = 1
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\n")
        # Strip fixed-form sequence / indicator areas if present (cols 1–6)
        stripped = line.lstrip()
        if not stripped or stripped.startswith("*"):
            continue
        # Comment lines that start with * after spaces already handled; also skip */ blocks style
        if re.match(r"^\d{6}\*", line):
            continue

        m = FIELD_RE.match(stripped)
        if not m:
            # Group items without PIC (01/05 group headers) are skipped
            continue

        level, name, pic_raw = m.group(1), m.group(2), m.group(3).strip()
        # Normalize whitespace inside PIC clause
        pic_raw = re.sub(r"\s+", " ", pic_raw)

        # USAGE may appear after PIC as separate tokens already captured in pic_raw
        # Also handle "PIC … USAGE COMP-3" variants
        pic_raw = re.sub(r"\bUSAGE\s+", "", pic_raw, flags=re.IGNORECASE)

        pm = PIC_TOKEN_RE.match(pic_raw)
        if not pm:
            raise ValueError(f"{line_no}: cannot parse PIC clause {pic_raw!r} for {name}")

        pic_body = pm.group("body")
        usage = _normalize_usage(pm.group("usage"))
        storage, length = _storage_and_length(pic_body, usage)
        picture = _format_picture(pic_body, usage)

        # Only emit elementary items (must have PIC — already required)
        # Skip 01 record itself if it somehow had PIC
        if level == "01" and usage is None and storage == "CHAR" and name.endswith("RECORD"):
            # Still include if it has PIC; this copybook's 01 has no PIC
            pass

        end_pos = pos + length - 1
        fields.append(
            LayoutField(
                field_name=name,
                picture=picture,
                storage=storage,
                start_pos=pos,
                end_pos=end_pos,
                length=length,
            )
        )
        pos = end_pos + 1

    return fields


def write_csv(fields: list[LayoutField], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(
            ["field_name", "picture", "storage", "start_pos", "end_pos", "length"]
        )
        for f in fields:
            writer.writerow(
                [f.field_name, f.picture, f.storage, f.start_pos, f.end_pos, f.length]
            )


def default_output_path(cpy_path: Path) -> Path:
    return cpy_path.with_name(f"{cpy_path.stem}_generated.csv")


def compare_csv(generated: Path, expected: Path) -> list[str]:
    errors: list[str] = []
    with generated.open(newline="", encoding="utf-8") as gf, expected.open(
        newline="", encoding="utf-8"
    ) as ef:
        gen_rows = list(csv.DictReader(gf))
        exp_rows = list(csv.DictReader(ef))
    if len(gen_rows) != len(exp_rows):
        errors.append(f"row count {len(gen_rows)} != expected {len(exp_rows)}")
    for i, (g, e) in enumerate(zip(gen_rows, exp_rows), start=2):
        for key in ("field_name", "picture", "storage", "start_pos", "end_pos", "length"):
            if (g.get(key) or "") != (e.get(key) or ""):
                errors.append(
                    f"L{i} {key}: generated={g.get(key)!r} expected={e.get(key)!r}"
                )
    if abs(len(gen_rows) - len(exp_rows)) > 0:
        longer = gen_rows if len(gen_rows) > len(exp_rows) else exp_rows
        label = "extra generated" if len(gen_rows) > len(exp_rows) else "missing vs expected"
        for row in longer[min(len(gen_rows), len(exp_rows)) :]:
            errors.append(f"{label}: {row.get('field_name')}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate field-layout CSV from a COBOL copybook (.CPY)."
    )
    parser.add_argument(
        "copybook",
        type=Path,
        help="Path to .CPY / .cpy copybook",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: <stem>_generated.csv beside the copybook)",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        default=None,
        help="Optional reference CSV to diff against after generation",
    )
    args = parser.parse_args(argv)

    cpy_path: Path = args.copybook
    if not cpy_path.is_file():
        print(f"error: copybook not found: {cpy_path}", file=sys.stderr)
        return 1

    text = cpy_path.read_text(encoding="utf-8", errors="replace")
    fields = parse_copybook(text)
    if not fields:
        print(f"error: no elementary PIC fields found in {cpy_path}", file=sys.stderr)
        return 1

    out_path = args.output or default_output_path(cpy_path)
    write_csv(fields, out_path)

    record_len = fields[-1].end_pos
    print(f"Wrote {out_path} ({len(fields)} fields, record length {record_len})")

    if args.compare:
        errs = compare_csv(out_path, args.compare)
        if errs:
            print(f"COMPARE FAILED vs {args.compare} ({len(errs)} differences):", file=sys.stderr)
            for msg in errs[:50]:
                print(f"  {msg}", file=sys.stderr)
            if len(errs) > 50:
                print(f"  ... and {len(errs) - 50} more", file=sys.stderr)
            return 1
        print(f"COMPARE OK vs {args.compare}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
