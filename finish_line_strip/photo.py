"""Export an annotated finish image and recover times from its pixels."""

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from .race import FPS, FRAME_HEIGHT, LANE_HEIGHT, RACER_COLORS, RACER_HALF_HEIGHT, lane_center

METADATA_KEY = "finish-line-strip-v1"
SAMPLE_PERIOD_MS = 1000 // FPS
PIXELS_PER_FRAME = 10
PLOT_X = 88
PLOT_Y = 100
INK = "#eff5fb"
MUTED = "#a3b7cc"
RULE = "#50657c"


@dataclass(frozen=True)
class Result:
    frames: tuple[int | None, ...]
    sample_period_ms: int

    def elapsed_ms(self, lane: int) -> int | None:
        frame = self.frames[lane]
        return None if frame is None else frame * self.sample_period_ms

    @property
    def gap_ms(self) -> int | None:
        first, second = self.frames
        if first is None or second is None:
            return None
        return abs(second - first) * self.sample_period_ms


def _first_occupied(image: Image.Image, columns: range, row: int, color: tuple[int, int, int]) -> int | None:
    # Each solid racer covers its lane's center row for the entire crossing.
    return next((frame for frame, x in enumerate(columns) if image.getpixel((x, row)) == color), None)


def save_photo(strip: Image.Image, path: str | Path) -> Result:
    frames = tuple(
        _first_occupied(strip, range(strip.width), lane_center(lane), color)
        for lane, color in enumerate(RACER_COLORS)
    )
    result = Result(frames, SAMPLE_PERIOD_MS)
    plot_right = PLOT_X + strip.width * PIXELS_PER_FRAME
    plot_bottom = PLOT_Y + FRAME_HEIGHT
    photo = Image.new("RGB", (plot_right + 30, plot_bottom + 72), "#0f1925")
    photo.paste(strip.resize((plot_right - PLOT_X, FRAME_HEIGHT), Image.Resampling.NEAREST), (PLOT_X, PLOT_Y))

    draw = ImageDraw.Draw(photo)
    title = ImageFont.load_default(size=30)
    label = ImageFont.load_default(size=14)
    small = ImageFont.load_default(size=12)
    draw.text((24, 20), "Finish-line strip", font=title, fill=INK)
    draw.text((25, 62), f"{FPS} fps  /  {SAMPLE_PERIOD_MS} ms per column", font=label, fill=MUTED)
    gap = "Gap unavailable" if result.gap_ms is None else f"{result.gap_ms} ms gap"
    draw.text((plot_right, 43), gap, font=title, anchor="rm", fill=INK)

    for lane, (frame, color) in enumerate(zip(frames, RACER_COLORS, strict=True)):
        center = PLOT_Y + lane_center(lane)
        draw.text((24, center), f"LANE {lane + 1}", font=small, anchor="lm", fill=color)
        if frame is not None:
            x = PLOT_X + frame * PIXELS_PER_FRAME
            band_top = center - RACER_HALF_HEIGHT
            draw.line((x, band_top - 18, x, band_top - 5), fill=color)
            draw.polygon(((x - 4, band_top - 6), (x + 4, band_top - 6), (x, band_top - 1)), fill=color)
            time_label = f"{result.elapsed_ms(lane)} ms"
            label_x = x + 8
            if label_x + draw.textlength(time_label, font=label) > plot_right:
                draw.text((x - 8, band_top - 12), time_label, font=label, anchor="rm", fill=color)
            else:
                draw.text((label_x, band_top - 12), time_label, font=label, anchor="lm", fill=color)

    draw.line((PLOT_X, PLOT_Y + LANE_HEIGHT - 1, plot_right - 1, PLOT_Y + LANE_HEIGHT - 1), fill=RULE)
    draw.line((PLOT_X, plot_bottom, plot_right - 1, plot_bottom), fill=RULE)
    for frame in range(strip.width):
        x = PLOT_X + frame * PIXELS_PER_FRAME
        major = frame % 5 == 0
        draw.line((x, plot_bottom, x, plot_bottom + (8 if major else 4)), fill=RULE)
        if major:
            draw.text((x, plot_bottom + 15), str(frame * SAMPLE_PERIOD_MS), font=small, anchor="mt", fill=MUTED)
    draw.text(((PLOT_X + plot_right) // 2, plot_bottom + 44), "Elapsed time (ms)", font=label, anchor="mt", fill=INK)

    metadata = PngImagePlugin.PngInfo()
    metadata.add_text(METADATA_KEY, json.dumps({
        "sample_period_ms": SAMPLE_PERIOD_MS,
        "plot_x": PLOT_X,
        "pixels_per_frame": PIXELS_PER_FRAME,
        "frame_count": strip.width,
        "lanes": [[PLOT_Y + lane_center(lane), color] for lane, color in enumerate(RACER_COLORS)],
    }))
    photo.save(path, format="PNG", pnginfo=metadata)
    return result


def read_photo(path: str | Path) -> Result:
    with Image.open(path) as photo:
        try:
            metadata = json.loads(photo.info[METADATA_KEY])
            start = metadata["plot_x"]
            width = metadata["pixels_per_frame"]
            count = metadata["frame_count"]
            period = metadata["sample_period_ms"]
            if any(type(value) is not int for value in (start, width, count, period)):
                raise ValueError
            if start < 0 or min(width, count, period) < 1 or start + width * count > photo.width:
                raise ValueError
            lanes = [(row, tuple(color)) for row, color in metadata["lanes"]]
            if len(lanes) != 2 or any(
                type(row) is not int or not 0 <= row < photo.height or len(color) != 3
                or any(type(channel) is not int or not 0 <= channel <= 255 for channel in color)
                for row, color in lanes
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Image is missing valid finish-line strip metadata") from error

        image = photo.convert("RGB")
        columns = range(start, start + width * count, width)
        frames = tuple(_first_occupied(image, columns, row, color) for row, color in lanes)
        return Result(frames, period)
