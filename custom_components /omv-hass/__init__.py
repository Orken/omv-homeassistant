from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import aiohttp
import async_timeout
from .const import DOMAIN, PLATFORMS, DEFAULT_SCAN_INTERVAL

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    session = aiohttp.ClientSession()
    coordinator = OMVCoordinator(hass, session, entry.data)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

class OMVCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, config):
        super().__init__(
            hass,
            hass.logger,
            name="OpenMediaVault",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.session = session
        self.host = config["host"]
        self.username = config["username"]
        self.password = config["password"]
        self.base_url = f"http://{self.host}/rpc.php"
        self.token = None

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(10):
                if not self.token:
                    await self._login()
                return await self._get_disks()
        except Exception as err:
            raise UpdateFailed(f"Erreur de mise à jour : {err}")

    async def _login(self):
        payload = {"service": "Session", "method": "login", "params": {"username": self.username, "password": self.password}}
        async with self.session.post(self.base_url, json=payload) as resp:
            data = await resp.json()
            if not data.get("response", False):
                raise Exception("Authentification OMV échouée")
            self.token = resp.cookies.get("PHPSESSID").value

    async def _get_disks(self):
        headers = {"Cookie": f"PHPSESSID={self.token}"}
        payload = {"service": "DiskMgmt", "method": "getList", "params": {}}
        async with self.session.post(self.base_url, json=payload, headers=headers) as resp:
            data = await resp.json()
            return data.get("data", [])
