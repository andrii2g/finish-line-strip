"""Command-line entry point for the finish-line strip generator and reader."""

import argparse
from pathlib import Path

from .photo import read_photo, save_photo
from .race import FIXTURE_ARRIVALS, FRAME_COUNT, build_strip


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and read a synthetic photo finish.")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="Render a two-lane race and export its finish strip.")
    generate.add_argument("path", nargs="?", type=Path, default=Path("finish.png"))
    generate.add_argument(
        "--arrivals",
        nargs=2,
        type=int,
        default=FIXTURE_ARRIVALS,
        metavar=("LANE1", "LANE2"),
        help=f"Arrival frame indices from 0 to {FRAME_COUNT - 1} (default: 40 43).",
    )

    read = commands.add_parser("read", help="Measure arrival times from a generated PNG.")
    read.add_argument("path", type=Path)

    args = parser.parse_args()
    try:
        if args.command == "generate":
            lane1, lane2 = args.arrivals
            save_photo(build_strip((lane1, lane2)), args.path)
            print(f"Wrote {args.path}")
        else:
            result = read_photo(args.path)
            for lane, frame in enumerate(result.frames):
                crossing = "no crossing" if frame is None else f"frame {frame} ({result.elapsed_ms(lane)} ms)"
                print(f"Lane {lane + 1}: {crossing}")
            print("Gap unavailable" if result.gap_ms is None else f"Gap: {result.gap_ms} ms")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
