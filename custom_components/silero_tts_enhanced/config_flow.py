import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import (
    SileroApi,
    SileroApiError,
    clean,
    fallback_models,
    ha_language,
    normalize_host,
    silero_language,
    sort_models,
)

DOMAIN = "silero_tts_enhanced"
_LOGGER = logging.getLogger(__name__)

DEFAULT_HOST = "http://homeassistant.local:8014"
LANGUAGES = ["ru", "uk", "en", "de", "es", "fr", "tt", "uz"]
SAMPLE_RATES = [
    {"value": "8000", "label": "8000 Hz"},
    {"value": "24000", "label": "24000 Hz"},
    {"value": "48000", "label": "48000 Hz"},
]


def _dropdown(options):
    # custom_value: можно ввести то, чего нет в списке, например новую модель
    return selector.SelectSelector(selector.SelectSelectorConfig(options=options, custom_value=True))


class SileroFlow:
    """Общие шаги установки и редактирования: сервер и язык, модель, голос."""

    _data: dict
    _options_mode = False

    async def _async_server_step(self, step_id, user_input):
        errors = {}
        if user_input is not None:
            host = normalize_host(user_input["host"])
            if await SileroApi(self.hass, host).reachable():
                self._data.update(host=host, language=ha_language(user_input["language"]))
                return await self.async_step_model()
            errors["base"] = "cannot_connect"

        defaults = user_input or self._data
        schema = vol.Schema({
            vol.Required("host", default=defaults.get("host", DEFAULT_HOST)): str,
            vol.Required("language", default=ha_language(defaults.get("language", "ru"))): _dropdown(LANGUAGES),
        })
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    async def async_step_model(self, user_input=None):
        if user_input is not None:
            self._data.update(model_id=clean(user_input["model_id"]), sample_rate=int(user_input["sample_rate"]))
            return await self.async_step_voice()

        language = silero_language(self._data["language"])
        try:
            models = ((await SileroApi(self.hass, self._data["host"]).models()) or {}).get(language)
        except SileroApiError:
            models = None
        options = sort_models(models, language) if models else fallback_models(language)

        current = self._data.get("model_id")
        schema = vol.Schema({
            vol.Required("model_id", default=current if current in options else options[0]): _dropdown(options),
            vol.Required("sample_rate", default=str(self._data.get("sample_rate", 48000))): selector.SelectSelector(
                selector.SelectSelectorConfig(options=SAMPLE_RATES)
            ),
        })
        return self.async_show_form(step_id="model", data_schema=schema)

    async def async_step_voice(self, user_input=None):
        if user_input is not None:
            self._data["speaker"] = clean(user_input["speaker"])
            if self._options_mode:
                self._data["put_accent"] = user_input["put_accent"]
                self._data["put_yo"] = user_input["put_yo"]
                self._data["send_wav"] = user_input["send_wav"]
            else:
                # Галочек при первой установке нет, значения по умолчанию включены
                self._data.setdefault("put_accent", True)
                self._data.setdefault("put_yo", True)
                self._data.setdefault("send_wav", False)
            return self._async_finish()

        try:
            voices = await SileroApi(self.hass, self._data["host"]).voices(
                self._data["model_id"], silero_language(self._data["language"])
            )
        except SileroApiError as err:
            _LOGGER.debug("Список голосов недоступен: %s", err)
            voices = None

        current = self._data.get("speaker")
        if voices:
            default = current if current in voices else voices[0]
            speaker = _dropdown(voices)
        else:
            default = current or "aidar"
            speaker = str
        fields = {vol.Required("speaker", default=default): speaker}

        # Эти галочки показываем только при редактировании
        if self._options_mode:
            fields[vol.Required("put_accent", default=self._data.get("put_accent", True))] = bool
            fields[vol.Required("put_yo", default=self._data.get("put_yo", True))] = bool
            fields[vol.Required("send_wav", default=self._data.get("send_wav", False))] = bool
        return self.async_show_form(step_id="voice", data_schema=vol.Schema(fields))


class SileroTTSConfigFlow(SileroFlow, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data = {}

    async def async_step_user(self, user_input=None):
        """Первый шаг установки интеграции."""
        return await self._async_server_step("user", user_input)

    def _async_finish(self):
        return self.async_create_entry(title="Silero TTS", data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SileroTTSOptionsFlowHandler()


class SileroTTSOptionsFlowHandler(SileroFlow, OptionsFlowWithReload):
    _options_mode = True

    async def async_step_init(self, user_input=None):
        """Форма редактирования настроек."""
        # Объединяем словари, чтобы не потерять host при сохранении опций
        self._data = {**self.config_entry.data, **self.config_entry.options}
        return await self._async_server_step("init", user_input)

    def _async_finish(self):
        return self.async_create_entry(title="", data=self._data)
