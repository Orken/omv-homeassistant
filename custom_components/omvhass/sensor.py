from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfInformation, UnitOfTemperature
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

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
        return {
            "model": disk.get("model"),
            "size": disk.get("size"),
            "size_bytes": disk.get("size_bytes"),
            "available_bytes": disk.get("available_bytes"),
            "used_bytes": disk.get("used_bytes"),
            "status": disk.get("status"),
            "devicefile": disk.get("devicename"),
            "mountpoint": disk.get("mountpoint"),
            "filesystem": disk.get("filesystem_type"),
        }

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
        self._attr_native_unit_of_measurement = UnitOfInformation.BYTES

    @property
    def native_value(self):
        disk = self.disk
        key = "size_bytes" if self._measurement == "total" else "available_bytes"
        value = disk.get(key)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
