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
from homeassistant.const import CONF_PORT
from homeassistant.data_entry_flow import AbortFlow

from .const import (
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_ADDITIONAL_ACCOUNTS,
    CONF_ENCRYPTION_KEY,
    CONF_PING_INTERVAL,
    CONF_ZONES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


HUB_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORT): int,
        vol.Required(CONF_ACCOUNT): str,
        vol.Optional(CONF_ENCRYPTION_KEY): str,
        vol.Required(CONF_PING_INTERVAL, default=1): int,
        vol.Required(CONF_ZONES, default=1): int,
        vol.Optional(CONF_ADDITIONAL_ACCOUNTS, default=False): bool,
    }
)

ACCOUNT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT): str,
        vol.Optional(CONF_ENCRYPTION_KEY): str,
        vol.Required(CONF_PING_INTERVAL, default=1): int,
        vol.Required(CONF_ZONES, default=1): int,
        vol.Optional(CONF_ADDITIONAL_ACCOUNTS, default=False): bool,
    }
)


def validate_input(data: dict) -> bool:
    """Validate the input by the user."""
    SIAAccount(data[CONF_ACCOUNT], data.get(CONF_ENCRYPTION_KEY))

    try:
        ping = int(data[CONF_PING_INTERVAL])
        assert 1 <= ping <= 1440
    except AssertionError:
        raise InvalidPing
    try:
        zones = int(data[CONF_ZONES])
        assert zones > 0
    except AssertionError:
        raise InvalidZones

    return True


class SIAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for sia."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH
    data = None

    async def async_step_add_account(self, user_input: dict = None):
        """Handle the additional accounts steps."""
        errors = {}
        if user_input is not None:
            try:
                if validate_input(user_input):
                    add_data = user_input.copy()
                    add_data.pop(CONF_ADDITIONAL_ACCOUNTS)
                    self.data[CONF_ACCOUNTS].append(add_data)
                    if user_input[CONF_ADDITIONAL_ACCOUNTS]:
                        return await self.async_step_add_account()
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

        return self.async_show_form(
            step_id="user", data_schema=ACCOUNT_SCHEMA, errors=errors,
        )

    async def async_step_user(self, user_input: dict = None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                if validate_input(user_input):
                    if not self.data:
                        self.data = {
                            CONF_PORT: user_input[CONF_PORT],
                            CONF_ACCOUNTS: [
                                {
                                    CONF_ACCOUNT: user_input[CONF_ACCOUNT],
                                    CONF_ENCRYPTION_KEY: user_input.get(
                                        CONF_ENCRYPTION_KEY
                                    ),
                                    CONF_PING_INTERVAL: user_input[CONF_PING_INTERVAL],
                                    CONF_ZONES: user_input[CONF_ZONES],
                                }
                            ],
                        }
                    else:
                        add_data = user_input.copy()
                        add_data.pop(CONF_ADDITIONAL_ACCOUNTS)
                        self.data[CONF_ACCOUNTS].append(add_data)
                    await self.async_set_unique_id(f"{DOMAIN}_{self.data[CONF_PORT]}")
                    self._abort_if_unique_id_configured()

                    if not user_input[CONF_ADDITIONAL_ACCOUNTS]:
                        return self.async_create_entry(
                            title=f"SIA Alarm on port {self.data[CONF_PORT]}",
                            data=self.data,
                        )
                    return await self.async_step_add_account()
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
            except AbortFlow:
                return self.async_abort(reason="already_configured")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=HUB_SCHEMA, errors=errors
        )


class InvalidPing(exceptions.HomeAssistantError):
    """Error to indicate there is invalid ping interval."""


class InvalidZones(exceptions.HomeAssistantError):
    """Error to indicate there is invalid number of zones."""
