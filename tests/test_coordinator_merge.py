from custom_components.omvhass.omv import (
    merge_disks_with_filesystems,
    to_int,
)


def test_merge_uses_filesystem_capacity_overrides_disk_size():
    disks = [
        {
            "devicename": "sda",
            "devicefile": "/dev/sda",
            "canonicaldevicefile": "/dev/disk/by-id/sda",
            "size": "500000000000",
            "model": "DiskOne",
        }
    ]
    filesystems = [
        {
            "devicefile": "/dev/sda",
            "size": "400000000000",
            "available": "150000000000",
            "label": "data",
            "mountpoint": "/data",
            "type": "ext4",
        }
    ]

    merged = merge_disks_with_filesystems(disks, filesystems)
    disk = merged[0]

    assert disk["size_bytes"] == 400000000000
    assert disk["available_bytes"] == 150000000000
    assert disk["used_bytes"] == 250000000000
    assert disk["filesystem_label"] == "data"
    assert disk["mountpoint"] == "/data"
    assert disk["filesystem_type"] == "ext4"


def test_merge_keeps_disk_only_data_when_filesystem_missing():
    disks = [
        {
            "devicename": "sdb",
            "devicefile": "/dev/sdb",
            "size": 123456789,
            "model": "DiskTwo",
        }
    ]

    merged = merge_disks_with_filesystems(disks, [])
    disk = merged[0]

    assert disk["size_bytes"] == 123456789
    assert disk["available_bytes"] is None
    assert "filesystem_label" not in disk


def test_to_int_handles_empty_and_strings():
    assert to_int("42") == 42
    assert to_int("42.5") == 42
    assert to_int("") is None
    assert to_int(None) is None
