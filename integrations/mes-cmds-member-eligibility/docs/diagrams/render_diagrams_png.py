#!/usr/bin/env python3
"""Render architecture diagrams as PNG (white background, black arrows) for Word export."""
from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Install Pillow: pip install pillow")

OUT = Path(__file__).resolve().parent
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FONT = ImageFont.load_default()


def arrow(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, width: int = 2) -> None:
    draw.line((x1, y1, x2, y2), fill=BLACK, width=width)
    import math

    ang = math.atan2(y2 - y1, x2 - x1)
    size = 10
    for da in (2.6, -2.6):
        ax = x2 - size * math.cos(ang - da * 0.3)
        ay = y2 - size * math.sin(ang - da * 0.3)
        draw.line((x2, y2, int(ax), int(ay)), fill=BLACK, width=width)


def box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    label: str,
    title: str | None = None,
) -> None:
    draw.rectangle(xy, outline=BLACK, width=2, fill=WHITE)
    if title:
        draw.text((xy[0] + 8, xy[1] + 6), title, fill=BLACK, font=FONT)
        draw.text((xy[0] + 8, xy[1] + 22), label, fill=BLACK, font=FONT)
    else:
        lines = label.split("\n")
        y = xy[1] + (xy[3] - xy[1] - len(lines) * 12) // 2
        for line in lines:
            draw.text((xy[0] + 6, y), line, fill=BLACK, font=FONT)
            y += 12


def diagram_01() -> None:
    w, h = 920, 520
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    box(draw, (30, 20, 280, 130), "Cursor IDE", title="")
    draw.text((120, 28), "Cursor IDE", fill=BLACK, font=FONT)
    box(draw, (50, 50, 150, 85), "Cursor\nAgent")
    box(draw, (170, 50, 270, 85), ".cursor/\nrules")
    box(draw, (110, 95, 210, 120), "prompts/*.md")

    box(draw, (30, 150, 450, 310), "", title="medicare-validation-rules (shared)")
    draw.text((50, 158), "medicare-validation-rules (shared)", fill=BLACK, font=FONT)
    for i, lbl in enumerate(
        [
            "MANIFEST.yaml",
            "data-elements.md",
            "value-lists/*.csv",
            "research.schema.json",
            "validate_research.py",
            "validate_spec…",
            "md_to_docx.py",
        ]
    ):
        x = 50 + (i % 3) * 130
        y = 185 + (i // 3) * 42
        box(draw, (x, y, x + 120, y + 32), lbl)

    box(draw, (480, 150, 890, 310), "", title="")
    draw.text((500, 158), "mes-cmds-member-eligibility (per flow)", fill=BLACK, font=FONT)
    box(draw, (500, 190, 680, 225), "MEMBERELIGIBILITY.csv")
    box(draw, (700, 190, 870, 225), "MemberEligibilityVO.md")
    box(draw, (500, 240, 680, 275), "research/*.yaml")
    box(draw, (700, 240, 870, 275), "spec/*.md + .docx")

    arrow(draw, 100, 85, 220, 50)
    arrow(draw, 100, 85, 160, 95)
    arrow(draw, 160, 120, 120, 185)
    arrow(draw, 590, 190, 100, 70)
    arrow(draw, 780, 190, 100, 70)
    arrow(draw, 100, 70, 590, 240)
    arrow(draw, 100, 70, 780, 240)
    arrow(draw, 590, 275, 300, 300)
    arrow(draw, 780, 275, 400, 300)
    arrow(draw, 780, 275, 107, 300)

    img.save(OUT / "diagram-01-system-architecture.png", "PNG")


def diagram_02() -> None:
    w, h = 960, 300
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)
    draw.text((380, 10), "Workflow stages (end-to-end)", fill=BLACK, font=FONT)

    labels = [
        "Business\nAnalyst",
        "Cursor Chat 1\nResearch",
        "validate_\nresearch.py",
        "Human\nReview",
        "Cursor Chat 2\nWriter",
        "validate_spec_\nagainst_research",
        "md_to\ndocx",
    ]
    xs = [20, 140, 270, 400, 520, 660, 820]
    bw = [90, 110, 110, 90, 110, 140, 70]
    for x, bw_, lbl in zip(xs, bw, labels):
        box(draw, (x, 45, x + bw_, 90), lbl)

    for i in range(len(xs) - 1):
        x1 = xs[i] + bw[i]
        x2 = xs[i + 1]
        arrow(draw, x1, 67, x2, 67)

    draw.text((300, 250), "Turn 1: Read artifacts → write research/*.yaml", fill=BLACK, font=FONT)
    draw.text((520, 250), "Turn 2: Write spec §1–§5 from research YAML only", fill=BLACK, font=FONT)

    img.save(OUT / "diagram-02-workflow-stages.png", "PNG")


def diagram_03() -> None:
    w, h = 820, 340
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle((30, 20, 790, 310), outline=BLACK, width=2, fill=WHITE)
    draw.text((260, 32), "Cursor control plane — mechanisms", fill=BLACK, font=FONT)

    box(draw, (60, 120, 250, 175), "medicaid-spec-\nconventions.mdc\n(always on)")
    box(draw, (310, 70, 510, 105), "integration-spec-research.md")
    box(draw, (310, 170, 510, 205), "integration-spec-write.md")
    box(draw, (560, 70, 760, 105), "integration-spec-research.mdc")
    box(draw, (560, 170, 760, 205), "integration-spec-writer.mdc")
    box(draw, (310, 250, 510, 285), "@ file references")

    arrow(draw, 250, 145, 308, 88)
    arrow(draw, 250, 145, 308, 188)
    arrow(draw, 510, 88, 558, 88)
    arrow(draw, 510, 188, 558, 188)
    arrow(draw, 410, 250, 410, 108)
    arrow(draw, 380, 250, 360, 210)
    arrow(draw, 440, 250, 460, 210)

    img.save(OUT / "diagram-03-cursor-control-plane.png", "PNG")


def main() -> None:
    diagram_01()
    diagram_02()
    diagram_03()
    print("Wrote PNG diagrams to", OUT)


if __name__ == "__main__":
    main()
