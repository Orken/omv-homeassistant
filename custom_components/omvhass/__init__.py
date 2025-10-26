import logging
import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, PLATFORMS, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up OMV integration from a config entry."""
    session = aiohttp.ClientSession()
    coordinator = OMVCoordinator(hass, session, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


class OMVCoordinator(DataUpdateCoordinator):
    """Manages communication and updates from OpenMediaVault."""

    def __init__(self, hass, session, config):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
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
        """Fetch data from OMV."""
        try:
            async with async_timeout.timeout(10):
                if not self.token:
                    await self._login()
                disks = await self._get_disks()
                _LOGGER.debug("OMV data retrieved: %s", disks)
                return disks
        except Exception as err:
            raise UpdateFailed(f"Erreur de mise à jour : {err}")

    async def _login(self):
        """Authenticate to OMV."""
        payload = {
            "service": "Session",
            "method": "login",
            "params": {"username": self.username, "password": self.password},
        }
        async with self.session.post(self.base_url, json=payload) as resp:
            data = await resp.json()
            if not data.get("response", False):
                raise Exception("Authentification OMV échouée")
            cookie = resp.cookies.get("PHPSESSID")
            if not cookie:
                raise Exception("Aucun cookie de session retourné")
            self.token = cookie.value
            _LOGGER.info("Connexion OMV réussie (%s)", self.host)

    async def _get_disks(self):
        """Retrieve disks status from OMV."""
        headers = {"Cookie": f"PHPSESSID={self.token}"}
        payload = {"service": "DiskMgmt", "method": "getList", "params": {}}
        async with self.session.post(self.base_url, json=payload, headers=headers) as resp:
            data = await resp.json()
            return data.get("data", [])
