"""Real filesystem regression for result images under non-ASCII paths."""
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from swarm_rescue.simulation.reporting.bombs_io import (
    save_exploration_comparison_image,
    save_wall_destruction_image,
)


class UnicodeResultImagesTest(unittest.TestCase):
    def test_both_result_images_roundtrip_on_unicode_paths(self):
        truth = np.zeros((32, 40), dtype=np.uint8)
        truth[8:14, 8:30] = 1
        with tempfile.TemporaryDirectory(prefix="swarm-images-") as name:
            root = Path(name).resolve()
            self.assertTrue(root.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            output = root / "慧眼测试"
            map_image = output / "地图对比.png"
            wall_image = output / "墙体结果.png"
            save_exploration_comparison_image(map_image, truth, truth)
            save_wall_destruction_image(
                wall_image, truth, [], blast_radius=4, boundary_wall_weight=0.5)
            for path in (map_image, wall_image):
                data = path.read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                self.assertIsNotNone(image)
                self.assertGreaterEqual(image.shape[0], truth.shape[0])
                self.assertGreaterEqual(image.shape[1], truth.shape[1])


if __name__ == "__main__":
    unittest.main()
