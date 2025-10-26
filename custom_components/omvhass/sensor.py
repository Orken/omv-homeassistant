from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [OMVDiskSensor(coordinator, disk) for disk in coordinator.data]
    async_add_entities(sensors)

class OMVDiskSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, disk):
        super().__init__(coordinator)
        self.disk = disk
        self._attr_name = f"OMV {disk['devicename']}"
        self._attr_unique_id = f"omv_disk_{disk['devicename']}"
        self._attr_unit_of_measurement = "°C"

    @property
    def native_value(self):
        temp = self.disk.get("temperature")
        return temp or None

    @property
    def extra_state_attributes(self):
        return {
            "model": self.disk.get("model"),
            "size": self.disk.get("size"),
            "status": self.disk.get("status"),
            "devicefile": self.disk.get("devicename"),
        }
