import unittest
from custom_components.omvhass.const import DOMAIN, DEFAULT_SCAN_INTERVAL


class TestConst(unittest.TestCase):
    def test_domain_constant(self):
        self.assertEqual(DOMAIN, "omvhass")

    def test_default_scan_interval_seconds(self):
        self.assertEqual(DEFAULT_SCAN_INTERVAL.total_seconds(), 300)


if __name__ == "__main__":
    unittest.main()
