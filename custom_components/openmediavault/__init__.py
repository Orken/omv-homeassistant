import logging
import aiohttp
import async_timeout
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, PLATFORMS, DEFAULT_SCAN_INTERVAL
from .omv import merge_disks_with_filesystems

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
        # Tu peux changer rpc.php → webapi/ si besoin
        self.base_url = f"http://{self.host}/rpc.php"
        self.token = None
        self.cookie_name = None

    async def _async_update_data(self):
        """Fetch data from OMV."""
        try:
            async with async_timeout.timeout(10):
                if not self.token:
                    await self._login()
                try:
                    disks = await self._get_disks()
                    filesystems = await self._get_filesystems()
                except Exception:
                    # Si la session a expiré, on réessaie une fois
                    _LOGGER.warning("Session OMV expirée, reconnexion...")
                    await self._login()
                    disks = await self._get_disks()
                    filesystems = await self._get_filesystems()

                merged = merge_disks_with_filesystems(disks, filesystems)
                _LOGGER.debug("OMV data retrieved: %s", merged)
                return merged
        except Exception as err:
            raise UpdateFailed(f"Erreur de mise à jour : {err}")

    async def _login(self):
        """Authenticate to OMV."""
        headers = {"X-Requested-With": "XMLHttpRequest"}
        payload = {
            "service": "Session",
            "method": "login",
            "params": {"username": self.username, "password": self.password},
        }

        async with self.session.post(self.base_url, json=payload, headers=headers) as resp:
            data = await resp.json()
            response = data.get("response", {})

            # Vérifie que l'auth a réussi
            if not response or not response.get("authenticated", False):
                raise Exception("Authentification OMV échouée")

            # Cherche un cookie de session
            cookies = resp.cookies
            session_cookie = (
                cookies.get("OPENMEDIAVAULT-SESSIONID")
                or cookies.get("PHPSESSID")
            )

            if not session_cookie:
                _LOGGER.error("Cookies reçus : %s", cookies)
                raise Exception("Aucun cookie de session retourné")

            self.token = session_cookie.value
            self.cookie_name = session_cookie.key
            _LOGGER.info("Connexion OMV réussie (%s, cookie=%s)", self.host, self.cookie_name)

    async def _get_disks(self):
        """Retrieve disks status from OMV."""
        if not self.token or not self.cookie_name:
            raise Exception("Session OMV non initialisée")

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": f"{self.cookie_name}={self.token}",
        }

        payload = {
            "service": "DiskMgmt",
            "method": "getList",
            "params": {
                "start": 0,
                "limit": -1,
                "sortfield": "",
                "sortdir": "asc"
            }
        }

        async with self.session.post(self.base_url, json=payload, headers=headers) as resp:
            data = await resp.json()

            # OMV 7 retourne les disques dans data["response"]["data"]
            response = data.get("response") or {}
            disks = response.get("data") or response.get("response") or []

            if not isinstance(disks, list):
                raise Exception(f"Réponse invalide OMV : {data}")

            return disks

    async def _get_filesystems(self):
        """Retrieve filesystem stats for each disk."""
        if not self.token or not self.cookie_name:
            raise Exception("Session OMV non initialisée")

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": f"{self.cookie_name}={self.token}",
        }

        payload = {
            "service": "FileSystemMgmt",
            "method": "getList",
            "params": {
                "start": 0,
                "limit": -1,
                "sortfield": "",
                "sortdir": "asc",
            },
        }

        async with self.session.post(self.base_url, json=payload, headers=headers) as resp:
            data = await resp.json()
            response = data.get("response") or {}
            filesystems = response.get("data") or response.get("response") or []

            if not isinstance(filesystems, list):
                raise Exception(f"Réponse invalide OMV (filesystem): {data}")

            return filesystems
