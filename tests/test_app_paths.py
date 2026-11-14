import os
import unittest
from unittest.mock import patch

from app_paths import _port_from_environment


class PortConfigurationTests(unittest.TestCase):
    def test_valid_port_is_used(self):
        with patch.dict(os.environ, {"DECKEDGE_PORT": "5012"}):
            self.assertEqual(_port_from_environment(), 5012)

    def test_invalid_or_out_of_range_port_falls_back_to_5000(self):
        for value in ("invalid", "0", "65536", "-1", ""):
            with self.subTest(value=value), patch.dict(os.environ, {"DECKEDGE_PORT": value}):
                self.assertEqual(_port_from_environment(), 5000)


if __name__ == "__main__":
    unittest.main()
