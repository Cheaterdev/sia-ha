"""Config flow for sia integration."""
import logging

from pysiaalarm import (
    InvalidAccountFormatError,
    InvalidAccountLengthError,
    InvalidKeyFormatError,
    InvalidKeyLengthError,
    SIAAccount,
)
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_PORT, CONF_PROTOCOL
from homeassistant.data_entry_flow import AbortFlow

from .const import (
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_ADDITIONAL_ACCOUNTS,
    CONF_ENCRYPTION_KEY,
    CONF_IGNORE_TIMESTAMPS,
    CONF_PING_INTERVAL,
    CONF_ZONES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


HUB_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORT): int,
        vol.Optional(CONF_PROTOCOL, default="TCP"): vol.In(["TCP", "UDP"]),
        vol.Required(CONF_ACCOUNT): str,
        vol.Optional(CONF_ENCRYPTION_KEY): str,
        vol.Required(CONF_PING_INTERVAL, default=1): int,
        vol.Required(CONF_ZONES, default=1): int,
        vol.Required(CONF_IGNORE_TIMESTAMPS, default=False): bool,
        vol.Optional(CONF_ADDITIONAL_ACCOUNTS, default=False): bool,
    }
)

ACCOUNT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT): str,
        vol.Optional(CONF_ENCRYPTION_KEY): str,
        vol.Required(CONF_PING_INTERVAL, default=1): int,
        vol.Required(CONF_ZONES, default=1): int,
        vol.Required(CONF_IGNORE_TIMESTAMPS, default=False): bool,
        vol.Optional(CONF_ADDITIONAL_ACCOUNTS, default=False): bool,
    }
)


def validate_input(data: dict):
    """Validate the input by the user."""
    SIAAccount.validate_account(data[CONF_ACCOUNT], data.get(CONF_ENCRYPTION_KEY))

    try:
        ping = int(data[CONF_PING_INTERVAL])
        assert 1 <= ping <= 1440
    except AssertionError as invalid_ping:
        raise InvalidPing from invalid_ping
    try:
        zones = int(data[CONF_ZONES])
        assert zones > 0
    except AssertionError as invalid_zone:
        raise InvalidZones from invalid_zone


class SIAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for sia."""

    VERSION = 2

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}

    async def async_step_add_account(self, user_input: dict = None):
        """Handle the additional accounts steps."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=ACCOUNT_SCHEMA,
                errors={},
            )

    async def async_step_user(self, user_input: dict = None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=HUB_SCHEMA, errors={}
            )
        errors = {}
        try:
            validate_input(user_input)
        except InvalidKeyFormatError:
            errors["base"] = "invalid_key_format"
        except InvalidKeyLengthError:
            errors["base"] = "invalid_key_length"
        except InvalidAccountFormatError:
            errors["base"] = "invalid_account_format"
        except InvalidAccountLengthError:
            errors["base"] = "invalid_account_length"
        except InvalidPing:
            errors["base"] = "invalid_ping"
        except InvalidZones:
            errors["base"] = "invalid_zones"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        if errors:
            return self.async_show_form(
                step_id="user", data_schema=HUB_SCHEMA, errors=errors
            )
        self.update_data(user_input)
        await self.async_set_unique_id(f"{DOMAIN}_{self._data[CONF_PORT]}")
        try:
            self._abort_if_unique_id_configured()
        except AbortFlow:
            return self.async_abort(reason="already_configured")

        if user_input[CONF_ADDITIONAL_ACCOUNTS]:
            return await self.async_step_add_account()
        return self.async_create_entry(
            title=f"SIA Alarm on port {self._data[CONF_PORT]}",
            data=self._data,
        )

    def update_data(self, user_input):
        """Parse the user_input and store in self.data."""
        if not self._data:
            self._data = {
                CONF_PORT: user_input[CONF_PORT],
                CONF_PROTOCOL: user_input[CONF_PROTOCOL],
                CONF_ACCOUNTS: [
                    {
                        CONF_ACCOUNT: user_input[CONF_ACCOUNT],
                        CONF_ENCRYPTION_KEY: user_input.get(CONF_ENCRYPTION_KEY),
                        CONF_PING_INTERVAL: user_input[CONF_PING_INTERVAL],
                        CONF_ZONES: user_input[CONF_ZONES],
                        CONF_IGNORE_TIMESTAMPS: user_input[CONF_IGNORE_TIMESTAMPS],
                    }
                ],
            }
        else:
            add_data = user_input.copy()
            add_data.pop(CONF_ADDITIONAL_ACCOUNTS)
            self._data[CONF_ACCOUNTS].append(add_data)


class InvalidPing(exceptions.HomeAssistantError):
    """Error to indicate there is invalid ping interval."""


class InvalidZones(exceptions.HomeAssistantError):
    """Error to indicate there is invalid number of zones."""
