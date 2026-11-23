"""Render a fixed camera view and sample its finish line."""

from PIL import Image, ImageDraw

FPS = 100
FRAME_COUNT = 70
FIXTURE_ARRIVALS = (40, 43)

FRAME_WIDTH = 320
FINISH_X = 200
LANE_HEIGHT = 76
LANE_BACKGROUNDS = ((25, 37, 52), (29, 43, 59))
RACER_COLORS = ((67, 224, 197), (255, 176, 101))
FRAME_HEIGHT = LANE_HEIGHT * len(RACER_COLORS)
RACER_WIDTH = 36
RACER_HALF_HEIGHT = 12
SPEED = 4  # pixels per frame


def lane_center(lane_index: int) -> int:
    return lane_index * LANE_HEIGHT + LANE_HEIGHT // 2


def render_frame(frame_index: int, arrival_frames: tuple[int, int]) -> Image.Image:
    frame = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT))
    draw = ImageDraw.Draw(frame)
    for lane, (arrival, color) in enumerate(zip(arrival_frames, RACER_COLORS, strict=True)):
        top = lane * LANE_HEIGHT
        draw.rectangle((0, top, FRAME_WIDTH - 1, top + LANE_HEIGHT - 1), LANE_BACKGROUNDS[lane])
        front = FINISH_X + (frame_index - arrival) * SPEED
        center = lane_center(lane)
        draw.rectangle(
            (front - RACER_WIDTH + 1, center - RACER_HALF_HEIGHT, front, center + RACER_HALF_HEIGHT),
            color,
        )
    return frame


def build_strip(arrival_frames: tuple[int, int] = FIXTURE_ARRIVALS) -> Image.Image:
    if len(arrival_frames) != len(RACER_COLORS) or any(
        type(arrival) is not int or not 0 <= arrival < FRAME_COUNT for arrival in arrival_frames
    ):
        raise ValueError(f"Expected two arrival frame indices between 0 and {FRAME_COUNT - 1}")

    strip = Image.new("RGB", (FRAME_COUNT, FRAME_HEIGHT))
    for frame_index in range(FRAME_COUNT):
        frame = render_frame(frame_index, arrival_frames)
        column = frame.crop((FINISH_X, 0, FINISH_X + 1, FRAME_HEIGHT))
        strip.paste(column, (frame_index, 0))
    return strip
