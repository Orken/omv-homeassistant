"""Helpers for interacting with the OpenMediaVault RPC payloads."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


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
            disk_copy["filesystem_uuid"] = filesystem.get("uuid")

        disk_copy["disk_id"] = _stable_disk_identifier(disk_copy, filesystem)

        disk_copy["size_bytes"] = size_bytes
        disk_copy["available_bytes"] = available_bytes
        if size_bytes is not None and available_bytes is not None:
            disk_copy["used_bytes"] = max(size_bytes - available_bytes, 0)

        merged.append(disk_copy)

    return merged


def _find_matching_filesystem(
    disk: Dict[str, Any], filesystems: Iterable[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Best-effort match between a physical disk and filesystem entries."""
    disk_keys = _device_aliases(
        [
            disk.get("devicefile"),
            disk.get("canonicaldevicefile"),
            disk.get("devicename"),
        ]
    )
    if not disk_keys:
        return None

    best_match = None
    for fs in filesystems:
        fs_keys = _device_aliases(
            [fs.get("devicefile"), fs.get("canonicaldevicefile"), fs.get("uuid")]
        )
        if not fs_keys:
            continue
        if disk_keys & fs_keys:
            # Prefer the first exact/alias match
            best_match = fs
            break

        # Fallback: check if filesystem device starts with disk root (e.g. /dev/sda1 vs /dev/sda)
        fs_devicefile = fs.get("devicefile")
        if _filesystem_matches_disk_prefix(fs_devicefile, disk_keys):
            best_match = fs

    return best_match


def _device_aliases(values: Sequence[Optional[str]]) -> Set[str]:
    aliases: Set[str] = set()
    for value in values:
        if not value:
            continue
        aliases.add(value)
        aliases.add(os.path.basename(value))
        if value.startswith("/dev/"):
            aliases.add(value.replace("/dev/", "", 1))
        aliases.add(_strip_partition_suffix(os.path.basename(value)))
    return {alias for alias in aliases if alias}


def _strip_partition_suffix(name: str) -> str:
    if not name:
        return name
    # NVMe disks end with 'pX'. md arrays may end with 'pX'. Standard disks end with digits.
    name = re.sub(r"p\d+$", "", name)
    return re.sub(r"\d+$", "", name)


def _filesystem_matches_disk_prefix(devicefile: Optional[str], disk_keys: Set[str]) -> bool:
    if not devicefile:
        return False
    for key in disk_keys:
        if not key:
            continue
        if devicefile.startswith(key):
            return True
        if key.startswith("/dev/") and devicefile.startswith(key.replace("/dev/", "", 1)):
            return True
    return False


def _filesystem_available(fs: Dict[str, Any]) -> Optional[int]:
    if not fs:
        return None
    for candidate in ("available", "available_bytes", "free", "free_bytes"):
        if candidate in fs:
            value = to_int(fs.get(candidate))
            if value is not None:
                return value
    return None


def _stable_disk_identifier(
    disk: Dict[str, Any], filesystem: Optional[Dict[str, Any]]
) -> str:
    candidates = [
        filesystem.get("uuid") if filesystem else None,
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
