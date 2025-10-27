from custom_components.omvhass.const import DOMAIN, DEFAULT_SCAN_INTERVAL


def test_domain_constant():
    assert DOMAIN == "omvhass"


def test_default_scan_interval_seconds():
    # DEFAULT_SCAN_INTERVAL is a datetime.timedelta
    assert DEFAULT_SCAN_INTERVAL.total_seconds() == 300
