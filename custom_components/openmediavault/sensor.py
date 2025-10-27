from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTemperature
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_BYTES_PER_GIGABYTE = 1024**3


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []
    for disk in coordinator.data or []:
        sensors.append(OMVDiskTemperatureSensor(coordinator, disk))
        if disk.get("size_bytes") is not None:
            sensors.append(
                OMVDiskStorageSensor(coordinator, disk, measurement="total")
            )
        if disk.get("available_bytes") is not None:
            sensors.append(
                OMVDiskStorageSensor(coordinator, disk, measurement="available")
            )
        if disk.get("size_bytes") is not None:
            sensors.append(OMVDiskUsageSensor(coordinator, disk))
    async_add_entities(sensors)


class OMVDiskEntity(CoordinatorEntity):
    def __init__(self, coordinator, disk):
        super().__init__(coordinator)
        self._device_name = disk["devicename"]
        display_name = disk.get("description") or self._device_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_name)},
            manufacturer=disk.get("vendor"),
            model=disk.get("model"),
            name=f"OMV Disk {display_name}",
            hw_version=disk.get("serialnumber"),
        )

    @property
    def disk(self):
        for disk in self.coordinator.data or []:
            if disk.get("devicename") == self._device_name:
                return disk
        return {}

    @property
    def extra_state_attributes(self):
        disk = self.disk
        usage_percent = _usage_percentage(disk)
        attributes = {
            "model": disk.get("model"),
            "size": disk.get("size"),
            "usage_percent": usage_percent,
            "status": disk.get("status"),
            "devicefile": disk.get("devicename"),
            "mountpoint": disk.get("mountpoint"),
            "filesystem": disk.get("filesystem_type"),
        }
        for source_key, target_key in (
            ("size_bytes", "size_gb"),
            ("available_bytes", "available_gb"),
            ("used_bytes", "used_gb"),
        ):
            gigabytes = _bytes_to_gigabytes(disk.get(source_key))
            if gigabytes is not None:
                attributes[target_key] = gigabytes

        return attributes


class OMVDiskTemperatureSensor(OMVDiskEntity, SensorEntity):
    def __init__(self, coordinator, disk):
        super().__init__(coordinator, disk)
        self._attr_name = f"OMV {disk['devicename']} Temperature"
        self._attr_unique_id = f"omv_disk_{disk['devicename']}_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        temp = self.disk.get("temperature")
        try:
            return float(temp)
        except (TypeError, ValueError):
            return None


class OMVDiskStorageSensor(OMVDiskEntity, SensorEntity):
    def __init__(self, coordinator, disk, measurement):
        super().__init__(coordinator, disk)
        label = "Total Size" if measurement == "total" else "Available Size"
        suffix = "total" if measurement == "total" else "available"
        self._measurement = measurement
        self._attr_name = f"OMV {disk['devicename']} {label}"
        self._attr_unique_id = f"omv_disk_{disk['devicename']}_{suffix}"
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
        self._attr_suggested_display_precision = 3

    @property
    def native_value(self):
        disk = self.disk
        key = "size_bytes" if self._measurement == "total" else "available_bytes"
        value = disk.get(key)
        if value is None:
            return None
        try:
            size_bytes = int(value)
        except (TypeError, ValueError):
            return None
        if size_bytes < 0:
            return 0.0
        return round(size_bytes / _BYTES_PER_GIGABYTE, 3)

    @property
    def extra_state_attributes(self):
        attributes = dict(super().extra_state_attributes)
        attributes["suggested_min_value"] = 0.0

        max_value = _bytes_to_gigabytes(self.disk.get("size_bytes"))
        if max_value is None:
            max_value = self.native_value
        if max_value is not None:
            attributes["suggested_max_value"] = max_value

        return attributes


class OMVDiskUsageSensor(OMVDiskEntity, SensorEntity):
    def __init__(self, coordinator, disk):
        super().__init__(coordinator, disk)
        self._attr_name = f"OMV {disk['devicename']} Usage"
        self._attr_unique_id = f"omv_disk_{disk['devicename']}_usage"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self):
        return _usage_percentage(self.disk)


def _bytes_to_gigabytes(value: Any) -> Optional[float]:
    try:
        bytes_value = int(value)
    except (TypeError, ValueError):
        return None
    if bytes_value < 0:
        return 0.0
    return round(bytes_value / _BYTES_PER_GIGABYTE, 3)


def _usage_percentage(disk):
    size = disk.get("size_bytes")
    try:
        size = int(size)
    except (TypeError, ValueError):
        return None
    if size <= 0:
        return None

    used = disk.get("used_bytes")
    available = disk.get("available_bytes")

    try:
        used = int(used) if used is not None else None
    except (TypeError, ValueError):
        used = None

    if used is None and available is not None:
        try:
            available = int(available)
            used = size - available
        except (TypeError, ValueError):
            return None

    if used is None:
        return None

    if used < 0:
        used = 0
    if used > size:
        used = size

    return round((used / size) * 100, 2)
