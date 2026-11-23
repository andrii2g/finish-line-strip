import tempfile
import unittest
from pathlib import Path

from PIL import Image

from finish_line_strip.photo import read_photo, save_photo
from finish_line_strip.race import build_strip


class PhotoFinishTests(unittest.TestCase):
    def test_saved_fixture_has_a_thirty_millisecond_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "finish.png"
            save_photo(build_strip(), path)
            result = read_photo(path)

        self.assertEqual(result.frames, (40, 43))
        self.assertEqual(result.elapsed_ms(0), 400)
        self.assertEqual(result.elapsed_ms(1), 430)
        self.assertEqual(result.gap_ms, 30)

    def test_reader_handles_reversed_order_ties_and_boundary_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "finish.png"
            for arrivals, gap in [((43, 40), 30), ((40, 40), 0), ((69, 0), 690)]:
                with self.subTest(arrivals=arrivals):
                    save_photo(build_strip(arrivals), path)
                    result = read_photo(path)
                    self.assertEqual(result.frames, arrivals)
                    self.assertEqual(result.gap_ms, gap)

    def test_reader_rejects_png_without_strip_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ordinary.png"
            Image.new("RGB", (10, 10)).save(path)
            with self.assertRaisesRegex(ValueError, "missing valid finish-line strip metadata"):
                read_photo(path)


if __name__ == "__main__":
    unittest.main()
