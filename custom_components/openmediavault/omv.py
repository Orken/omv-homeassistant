"""Helpers for interacting with the OpenMediaVault RPC payloads."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


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
    merged: List[Dict[str, Any]] = []
    for disk in disks:
        filesystem = _find_matching_filesystem(disk, filesystems)
        disk_copy = dict(disk)

        size_bytes = (
            to_int(filesystem.get("size")) if filesystem else to_int(disk.get("size"))
        )
        available_bytes = _filesystem_available(filesystem) if filesystem else None

        if filesystem:
            disk_copy["filesystem_label"] = filesystem.get("label")
            disk_copy["mountpoint"] = filesystem.get("mountpoint")
            disk_copy["filesystem_type"] = filesystem.get("type")
            disk_copy["filesystem_uuid"] = _normalize_identifier(filesystem.get("uuid"))

        disk_copy["disk_id"] = _stable_disk_identifier(disk_copy)

        disk_copy["size_bytes"] = size_bytes
        disk_copy["available_bytes"] = available_bytes
        if size_bytes is not None and available_bytes is not None:
            disk_copy["used_bytes"] = max(size_bytes - available_bytes, 0)

        merged.append(disk_copy)

    return merged


def _find_matching_filesystem(
    disk: Dict[str, Any], filesystems: Iterable[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Match filesystem entry by devicename or canonical device file (exact)."""
    disk_devicename = disk.get("devicename")
    disk_canonical = disk.get("canonicaldevicefile")
    if not disk_devicename and not disk_canonical:
        return None

    for fs in filesystems:
        if disk_devicename and fs.get("devicename") == disk_devicename:
            return fs
        if disk_canonical and fs.get("canonicaldevicefile") == disk_canonical:
            return fs
    return None


def _filesystem_available(fs: Dict[str, Any]) -> Optional[int]:
    if not fs:
        return None
    for candidate in ("available", "available_bytes", "free", "free_bytes"):
        if candidate in fs:
            value = to_int(fs.get(candidate))
            if value is not None:
                return value
    return None


def _stable_disk_identifier(disk: Dict[str, Any]) -> str:
    candidates = [
        disk.get("filesystem_uuid"),
        disk.get("uuid"),
        disk.get("serialnumber"),
        disk.get("serial"),
        disk.get("wwn"),
        disk.get("devicefile"),
        disk.get("devicename"),
    ]
    for candidate in candidates:
        normalized = _normalize_identifier(candidate)
        if normalized:
            return normalized
    return ""


def _normalize_identifier(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    if normalized.startswith("/dev/"):
        normalized = normalized.replace("/dev/", "", 1)
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_-]", "_", normalized)
    return normalized
