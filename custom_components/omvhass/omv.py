"""Helpers for interacting with the OpenMediaVault RPC payloads."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def to_int(value: Any) -> int | None:
    """Best-effort conversion to int (bytes)."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


def merge_disks_with_filesystems(
    disks: Iterable[Dict[str, Any]], filesystems: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Attach filesystem capacity details to disk payloads."""
    fs_by_device: Dict[str, Dict[str, Any]] = {}
    for fs in filesystems:
        devicefile = fs.get("devicefile")
        canonical = fs.get("canonicaldevicefile")
        if devicefile:
            fs_by_device[devicefile] = fs
        if canonical:
            fs_by_device.setdefault(canonical, fs)

    merged: List[Dict[str, Any]] = []
    for disk in disks:
        disk_copy = dict(disk)
        primary_key = disk.get("devicefile")
        fallback_key = disk.get("canonicaldevicefile")
        filesystem = None
        if primary_key:
            filesystem = fs_by_device.get(primary_key)
        if not filesystem and fallback_key:
            filesystem = fs_by_device.get(fallback_key)

        size_bytes = (
            to_int(filesystem.get("size")) if filesystem else to_int(disk.get("size"))
        )
        available_bytes = (
            to_int(filesystem.get("available")) if filesystem else None
        )

        if filesystem:
            disk_copy["filesystem_label"] = filesystem.get("label")
            disk_copy["mountpoint"] = filesystem.get("mountpoint")
            disk_copy["filesystem_type"] = filesystem.get("type")

        disk_copy["size_bytes"] = size_bytes
        disk_copy["available_bytes"] = available_bytes
        if size_bytes is not None and available_bytes is not None:
            disk_copy["used_bytes"] = max(size_bytes - available_bytes, 0)

        merged.append(disk_copy)

    return merged
