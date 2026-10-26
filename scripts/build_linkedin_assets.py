"""Build LinkedIn-ready images from the genuine application screenshots."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / "assets" / "screenshots"
OUTPUT = ROOT / "assets" / "linkedin"

BG_TOP = (7, 11, 22)
BG_BOTTOM = (10, 17, 32)
PANEL = (16, 24, 42)
PANEL_ALT = (13, 22, 38)
BORDER = (31, 45, 72)
CYAN = (82, 246, 227)
VIOLET = (155, 135, 255)
CORAL = (255, 92, 122)
TEXT = (232, 240, 255)
MUTED = (132, 146, 172)
DIM = (94, 108, 132)

FONT_FILES = {
    "regular": [
        Path("/usr/share/fonts/opentype/inter/Inter-Regular.otf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ],
    "medium": [
        Path("/usr/share/fonts/opentype/inter/Inter-Medium.otf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ],
    "semibold": [
        Path("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ],
    "bold": [
        Path("/usr/share/fonts/opentype/inter/Inter-Bold.otf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ],
    "mono": [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/opentype/inter/Inter-Regular.otf"),
    ],
}


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """Load a local font with a portable fallback."""
    for path in FONT_FILES[weight]:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _gradient(size: tuple[int, int]) -> Image.Image:
    width, height = size
    canvas = Image.new("RGB", size, BG_TOP)
    draw = ImageDraw.Draw(canvas)
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(
            round(start + (end - start) * ratio)
            for start, end in zip(BG_TOP, BG_BOTTOM, strict=True)
        )
        draw.line((0, y, width, y), fill=color)
    return canvas


def _glow(
    size: tuple[int, int],
    center: tuple[int, int],
    radius: tuple[int, int],
    color: tuple[int, int, int],
    alpha: int,
) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = center
    rx, ry = radius
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(*color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(90))


def background(size: tuple[int, int]) -> Image.Image:
    """Deep-navy canvas with restrained glows and a technical grid."""
    canvas = _gradient(size).convert("RGBA")
    width, height = size
    canvas.alpha_composite(
        _glow(size, (int(width * 0.08), 0), (520, 300), CYAN, 22)
    )
    canvas.alpha_composite(
        _glow(size, (int(width * 0.92), int(height * 0.12)), (460, 280), VIOLET, 24)
    )
    grid = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(grid)
    for x in range(0, width, 54):
        draw.line((x, 0, x, height), fill=(*BORDER, 16))
    for y in range(0, height, 54):
        draw.line((0, y, width, y), fill=(*BORDER, 16))
    canvas.alpha_composite(grid)
    return canvas


def tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    tracking: int = 3,
) -> None:
    x, y = xy
    for character in text:
        draw.text((x, y), character, font=text_font, fill=fill)
        x += draw.textlength(character, font=text_font) + tracking


def wrap(
    draw: ImageDraw.ImageDraw,
    text: str,
    text_font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=text_font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def paragraph(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_height: int | None = None,
) -> int:
    x, y = xy
    step = line_height or int(text_font.size * 1.34)
    for line in wrap(draw, text, text_font, max_width):
        draw.text((x, y), line, font=text_font, fill=fill)
        y += step
    return y


def chip(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    label: str,
    text_font: ImageFont.FreeTypeFont,
    *,
    fg: tuple[int, int, int] = MUTED,
    border: tuple[int, int, int] = BORDER,
) -> int:
    x, y = xy
    padding_x = 14
    height = text_font.size + 18
    width = int(draw.textlength(label, font=text_font)) + padding_x * 2
    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=height // 2,
        fill=(*PANEL, 180),
        outline=(*border, 255),
        width=1,
    )
    draw.text(
        (x + padding_x, y + height // 2),
        label,
        font=text_font,
        fill=fg,
        anchor="lm",
    )
    return width


def screenshot(
    canvas: Image.Image,
    source: Path,
    box: tuple[int, int, int, int],
    *,
    crop: tuple[int, int, int, int] | None = None,
    radius: int = 18,
) -> None:
    """Paste a real screenshot with a soft shadow and quiet frame."""
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    image = Image.open(source).convert("RGB")
    if crop is not None:
        image = image.crop(crop)
    image = ImageOps.fit(
        image, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
    )
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (x0 + 8, y0 + 14, x1 + 8, y1 + 14),
        radius=radius,
        fill=(0, 0, 0, 150),
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(24)))
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    canvas.paste(image, (x0, y0), mask)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (x0, y0, x1, y1), radius=radius, outline=(*BORDER, 255), width=1
    )


def panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int] = PANEL,
    outline: tuple[int, int, int] = BORDER,
    radius: int = 22,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=(*fill, 235), outline=(*outline, 255), width=1)


def footer(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    source_note: str = "",
) -> None:
    y = 1282
    draw.line((80, y - 26, width - 80, y - 26), fill=(*BORDER, 255), width=1)
    draw.text(
        (80, y),
        "github.com/Shahbaz2104/space-weather-observatory",
        font=font(20, "medium"),
        fill=MUTED,
    )
    if source_note:
        draw.text(
            (width - 80, y),
            source_note,
            font=font(18, "regular"),
            fill=DIM,
            anchor="ra",
        )


def slide_shell(number: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = background((1080, 1350))
    draw = ImageDraw.Draw(canvas)
    tracked(
        draw,
        (80, 78),
        "SPACE WEATHER OBSERVATORY",
        font(21, "semibold"),
        CYAN,
        3,
    )
    draw.text(
        (1000, 78),
        f"{number:02d} / 06",
        font=font(19, "medium"),
        fill=DIM,
        anchor="ra",
    )
    draw.line((80, 128, 1000, 128), fill=(*BORDER, 255), width=1)
    return canvas, draw


def title(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    size: int = 86,
    y: int = 174,
    color: tuple[int, int, int] = TEXT,
) -> int:
    text_font = font(size, "bold")
    return paragraph(
        draw,
        (80, y),
        text,
        text_font,
        color,
        920,
        line_height=int(size * 1.06),
    )


def cover_slide() -> Image.Image:
    canvas, draw = slide_shell(1)
    tracked(draw, (80, 172), "WHEN THE SUN DISRUPTS EARTH", font(23, "semibold"), CORAL, 4)
    title(draw, "When the Sun\ndisrupts Earth.", size=98, y=222)
    paragraph(
        draw,
        (80, 448),
        "A clear, honest look at geomagnetic storms: real data, visible sources, and "
        "no made-up values.",
        font(30, "regular"),
        MUTED,
        900,
        line_height=44,
    )
    x = 80
    for label, color in (
        ("NOAA / GFZ / NASA", CYAN),
        ("58 TESTS", VIOLET),
        ("FREE · OPEN SOURCE", MUTED),
    ):
        x += chip(draw, (x, 566), label, font(20, "semibold"), fg=color) + 12
    screenshot(
        canvas,
        SCREENSHOTS / "overview.png",
        (90, 650, 990, 1212),
        radius=20,
    )
    draw.text(
        (90, 1218),
        "May 2024 sample data · not live",
        font=font(19, "regular"),
        fill=DIM,
    )
    footer(draw, width=1080)
    return canvas.convert("RGB")


def problem_slide() -> Image.Image:
    canvas, draw = slide_shell(2)
    title(draw, "Three ways a chart can lie.", size=90)
    paragraph(
        draw,
        (80, 390),
        "A chart can mislead without a single wrong number.",
        font(30, "regular"),
        MUTED,
        900,
        line_height=44,
    )
    items = [
        ("01", "A gap drawn as calm", "Missing readings become a flat line."),
        (
            "02",
            "A smooth line drawn as real data",
            "Smoothing invents values that were never measured.",
        ),
        (
            "03",
            "One high number mistaken for a storm",
            "A single reading is not a full storm.",
        ),
    ]
    y = 528
    for number, heading, body in items:
        panel(draw, (80, y, 1000, y + 210))
        draw.text((112, y + 38), number, font=font(28, "mono"), fill=CORAL)
        draw.text((196, y + 32), heading, font=font(33, "semibold"), fill=TEXT)
        paragraph(
            draw,
            (196, y + 92),
            body,
            font(25, "regular"),
            MUTED,
            740,
            line_height=35,
        )
        y += 238
    footer(draw, width=1080, source_note="Show the gaps")
    return canvas.convert("RGB")


def features_slide() -> Image.Image:
    canvas, draw = slide_shell(3)
    title(draw, "Seven linked views.\nOne shared timeline.", size=88)
    paragraph(
        draw,
        (80, 392),
        "From the latest Kp reading to a long-term heatmap, every page uses UTC and "
        "keeps gaps visible.",
        font(29, "regular"),
        MUTED,
        900,
        line_height=42,
    )
    labels = [
        "Overview",
        "Storm Explorer",
        "Activity Heatmap",
        "Solar Wind",
        "Correlation Lab",
        "Animation Studio",
        "Methodology",
    ]
    x, y = 80, 500
    for label in labels:
        width = int(draw.textlength(label, font=font(20, "semibold"))) + 28
        if x + width > 1000:
            x = 80
            y += 46
        x += chip(draw, (x, y), label, font(20, "semibold"), fg=CYAN) + 10
    screenshot(
        canvas,
        SCREENSHOTS / "heatmap.png",
        (90, 650, 990, 1212),
        radius=20,
    )
    draw.text(
        (90, 1218),
        "Activity heatmap · sample data, 2003 and 2024 · not live",
        font=font(19, "regular"),
        fill=DIM,
    )
    footer(draw, width=1080)
    return canvas.convert("RGB")


def integrity_slide() -> Image.Image:
    canvas, draw = slide_shell(4)
    title(draw, "Missing stays missing.", size=82)
    paragraph(
        draw,
        (80, 330),
        "No filled gaps. No fake zeros. No hidden gaps.",
        font(32, "medium"),
        CYAN,
        900,
        line_height=44,
    )
    paragraph(
        draw,
        (80, 392),
        "Charts keep the edges of every gap, so a long record cannot be made to look "
        "complete.",
        font(27, "regular"),
        MUTED,
        900,
        line_height=39,
    )
    screenshot(
        canvas,
        SCREENSHOTS / "storm_explorer.png",
        (90, 512, 990, 1074),
        radius=20,
    )
    draw.text(
        (90, 1080),
        "Storm Explorer · storm length and missing readings · sample, not live",
        font=font(19, "regular"),
        fill=DIM,
    )
    panel(draw, (80, 1124, 1000, 1224), fill=PANEL_ALT)
    paragraph(
        draw,
        (108, 1148),
        "Every download can include a source record: where the data came from, when, "
        "the units, settings, and warnings.",
        font(21, "regular"),
        TEXT,
        864,
        line_height=28,
    )
    footer(draw, width=1080, source_note="Sample data, not live")
    return canvas.convert("RGB")


def statistics_slide() -> Image.Image:
    canvas, draw = slide_shell(5)
    title(draw, "Moving together\nis not proof.", size=92)
    paragraph(
        draw,
        (80, 408),
        "The lab shows how much independent evidence is behind the headline number.",
        font(28, "regular"),
        MUTED,
        900,
        line_height=40,
    )
    cards = [
        ("CORRELATION", "0.627", "1 means a perfect match"),
        ("REAL EVIDENCE", "21.2", "not 243 separate readings"),
        ("READINGS", "243", "three hours each"),
    ]
    x = 80
    for label, value, note in cards:
        panel(draw, (x, 520, x + 288, 690))
        draw.text((x + 26, 546), label, font=font(19, "semibold"), fill=MUTED)
        draw.text((x + 26, 580), value, font=font(52, "mono"), fill=TEXT)
        paragraph(
            draw,
            (x + 26, 644),
            note,
            font(18, "regular"),
            DIM,
            240,
            line_height=24,
        )
        x += 312
    screenshot(
        canvas,
        SCREENSHOTS / "correlation.png",
        (90, 730, 990, 1192),
        radius=20,
    )
    draw.text(
        (90, 1198),
        "May 2024 sample · not live · solar wind speed and Kp",
        font=font(19, "regular"),
        fill=DIM,
    )
    footer(draw, width=1080)
    return canvas.convert("RGB")


def closing_slide() -> Image.Image:
    canvas, draw = slide_shell(6)
    tracked(draw, (80, 172), "CHECK THE EVIDENCE", font(23, "semibold"), CYAN, 4)
    title(draw, "Seven pages.\nReal data.", size=94, y=222)
    paragraph(
        draw,
        (80, 448),
        "Built with Python and Streamlit. Every page shows the limits as clearly as "
        "the numbers.",
        font(29, "regular"),
        MUTED,
        900,
        line_height=42,
    )
    panel(draw, (80, 570, 1000, 792), fill=PANEL_ALT)
    draw.text(
        (112, 594),
        "LIVE DEMO",
        font=font(19, "semibold"),
        fill=CYAN,
    )
    draw.text(
        (112, 622),
        "https://space-weather-observatory-4xedxr5f2n5vpym7t5ix7p.streamlit.app",
        font=font(17, "mono"),
        fill=TEXT,
    )
    draw.text(
        (112, 672),
        "REPOSITORY",
        font=font(19, "semibold"),
        fill=CYAN,
    )
    draw.text(
        (112, 700),
        "github.com/Shahbaz2104/space-weather-observatory",
        font=font(26, "semibold"),
        fill=TEXT,
    )
    draw.text(
        (112, 748),
        "Live data and sample data are labelled. Not a forecast service.",
        font=font(18, "regular"),
        fill=DIM,
    )
    x = 80
    for label, color in (
        ("58 TESTS", VIOLET),
        ("AUTOMATED CHECKS", CYAN),
        ("OPEN SOURCE", MUTED),
    ):
        x += chip(draw, (x, 814), label, font(19, "semibold"), fg=color) + 10
    screenshot(
        canvas,
        SCREENSHOTS / "solar_wind.png",
        (80, 866, 1000, 1212),
        crop=(360, 675, 1600, 990),
        radius=20,
    )
    draw.text(
        (80, 1218),
        "Solar wind · speed and magnetic field · sample, not live",
        font=font(19, "regular"),
        fill=DIM,
    )
    footer(draw, width=1080)
    return canvas.convert("RGB")


def hero() -> Image.Image:
    size = (1200, 627)
    canvas = background(size)
    draw = ImageDraw.Draw(canvas)
    tracked(draw, (64, 62), "SPACE WEATHER OBSERVATORY", font(18, "semibold"), CYAN, 3)
    draw.text((64, 104), "When the Sun", font=font(68, "bold"), fill=TEXT)
    draw.text((64, 176), "disrupts Earth.", font=font(68, "bold"), fill=TEXT)
    draw.line((64, 266, 148, 266), fill=(*CORAL, 255), width=4)
    paragraph(
        draw,
        (64, 296),
        "A clear, honest dashboard for geomagnetic storms — real NOAA, GFZ, and "
        "NASA data, with no made-up values.",
        font(22, "regular"),
        MUTED,
        520,
        line_height=32,
    )
    x = 64
    for label, color in (
        ("NOAA / GFZ / NASA", CYAN),
        ("58 TESTS", VIOLET),
        ("FREE · OPEN SOURCE", MUTED),
    ):
        x += chip(draw, (x, 416), label, font(17, "semibold"), fg=color) + 9
    draw.text(
        (64, 540),
        "github.com/Shahbaz2104/space-weather-observatory",
        font=font(18, "medium"),
        fill=MUTED,
    )
    draw.text(
        (64, 568),
        "Sample data · not a live forecast service",
        font=font(16, "regular"),
        fill=DIM,
    )
    screenshot(
        canvas,
        SCREENSHOTS / "overview.png",
        (610, 110, 1140, 511),
        crop=(360, 60, 1600, 1000),
        radius=18,
    )
    draw.text(
        (610, 526),
        "Overview · May 2024 sample data",
        font=font(16, "regular"),
        fill=DIM,
    )
    return canvas.convert("RGB")


def banner() -> Image.Image:
    size = (1584, 396)
    canvas = background(size)
    draw = ImageDraw.Draw(canvas)
    tracked(draw, (64, 54), "SPACE WEATHER OBSERVATORY", font(20, "semibold"), CYAN, 3)
    draw.text((64, 100), "When the Sun disrupts Earth.", font=font(52, "bold"), fill=TEXT)
    paragraph(
        draw,
        (64, 178),
        "A clear, honest view of geomagnetic storms, solar wind, and the Kp index.",
        font(23, "regular"),
        MUTED,
        720,
        line_height=33,
    )
    draw.text(
        (64, 292),
        "github.com/Shahbaz2104/space-weather-observatory",
        font=font(18, "medium"),
        fill=CYAN,
    )
    screenshot(
        canvas,
        SCREENSHOTS / "overview.png",
        (900, 64, 1518, 255),
        crop=(380, 620, 1510, 970),
        radius=16,
    )
    draw.text(
        (900, 265),
        "May 2024 sample · not live",
        font=font(16, "regular"),
        fill=DIM,
    )
    return canvas.convert("RGB")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    slides = [
        cover_slide(),
        problem_slide(),
        features_slide(),
        integrity_slide(),
        statistics_slide(),
        closing_slide(),
    ]
    for index, image in enumerate(slides, start=1):
        name = {
            1: "cover",
            2: "problem",
            3: "views",
            4: "integrity",
            5: "statistics",
            6: "closing",
        }[index]
        image.save(OUTPUT / f"linkedin-carousel-{index:02d}-{name}.png", optimize=True)
    slides[0].save(
        OUTPUT / "space-weather-linkedin-carousel.pdf",
        save_all=True,
        append_images=slides[1:],
        resolution=150.0,
    )
    hero().save(OUTPUT / "linkedin-hero-1200x627.png", optimize=True)
    banner().save(OUTPUT / "linkedin-banner-1584x396.png", optimize=True)
    print(f"Wrote LinkedIn assets to {OUTPUT}")


if __name__ == "__main__":
    main()
