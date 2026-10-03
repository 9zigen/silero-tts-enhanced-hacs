import logging

from homeassistant.components.tts import ATTR_VOICE, TextToSpeechEntity, Voice
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .api import (
    SileroApi,
    SileroApiError,
    clean,
    fallback_models,
    ha_language,
    silero_language,
    sort_models,
)

_LOGGER = logging.getLogger(__name__)

# uk это украинский в Home Assistant; ua оставлен для старых настроек, где он был сохранён
SUPPORTED_LANGUAGES = ["ru", "uk", "ua", "en", "de", "es", "fr", "tt", "uz"]


def _as_bool(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([SileroTTSAPIEntity(hass, config_entry)])


class SileroTTSAPIEntity(TextToSpeechEntity):
    _attr_name = "Silero TTS Enhanced"
    _attr_has_entity_name = False

    def __init__(self, hass, config_entry):
        self.hass = hass

        # Объединяем данные установки и изменённые настройки (options важнее)
        data = {**config_entry.data, **config_entry.options}

        self._api = SileroApi(hass, data.get("host", ""))
        self._lang = ha_language(data.get("language", "ru"))
        self._model_id = clean(data.get("model_id", "v5_5_ru"))
        self._sample_rate = int(data.get("sample_rate", 48000))
        self._speaker = clean(data.get("speaker"))
        self._put_accent = _as_bool(data.get("put_accent"), True)
        self._put_yo = _as_bool(data.get("put_yo"), True)
        self._send_wav = _as_bool(data.get("send_wav"), False)

        self._language_defaults = {}  # язык Silero -> (модель, голос) для языков не по умолчанию
        self._voices = {}  # язык HA -> список Voice

        self._attr_unique_id = f"{config_entry.entry_id}_tts"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        # Не задерживаем запуск, если аддон ещё не поднялся
        self.hass.async_create_task(self._async_load_voices())

    async def _async_load_voices(self):
        try:
            voices = await self._api.voices(self._model_id, silero_language(self._lang))
        except SileroApiError as err:
            _LOGGER.debug("Список голосов недоступен: %s", err)
            return
        if voices:
            self._voices[self._lang] = [Voice(voice, voice) for voice in voices]

    @property
    def supported_languages(self) -> list[str]:
        if self._lang in SUPPORTED_LANGUAGES:
            return SUPPORTED_LANGUAGES
        return [*SUPPORTED_LANGUAGES, self._lang]

    @property
    def default_language(self) -> str:
        return self._lang

    @property
    def supported_options(self) -> list[str]:
        # Разрешаем Home Assistant отправлять нам кастомные опции из скриптов
        return [ATTR_VOICE, "model_id", "put_accent", "put_yo", "sample_rate"]

    @property
    def default_options(self) -> dict:
        options = {
            ATTR_VOICE: self._speaker,
            "model_id": self._model_id,
            "put_accent": self._put_accent,
            "put_yo": self._put_yo,
            "sample_rate": self._sample_rate,
        }
        if self._send_wav:
            # По умолчанию Home Assistant конвертирует ответ в mp3 через ffmpeg; с wav конвертации нет
            options["preferred_format"] = "wav"
        return options

    @callback
    def async_get_supported_voices(self, language: str) -> list[Voice] | None:
        return self._voices.get(ha_language(language))

    async def _async_defaults_for(self, language):
        """Модель и голос для языка, отличного от языка по умолчанию, например uk или en в Assist."""
        if language in self._language_defaults:
            return self._language_defaults[language]
        try:
            models = (await self._api.models() or {}).get(language)
            candidates = sort_models(models, language) if models else fallback_models(language)
            model_id = candidates[0]
            voices = await self._api.voices(model_id, language)
        except SileroApiError as err:
            _LOGGER.debug("Не удалось подобрать модель для языка %s: %s", language, err)
            return None, None
        result = (model_id, voices[0] if voices else None)
        self._language_defaults[language] = result
        return result

    async def async_get_tts_audio(self, message: str, language: str, options: dict):
        # Если в автоматизации указали другой голос/настройки - берем их, иначе дефолтные
        silero_lang = silero_language(language)
        model_id = clean(options.get("model_id", self._model_id))
        voice = clean(options.get(ATTR_VOICE, self._speaker))

        # Модель и голос по умолчанию подходят только языку по умолчанию. Для другого языка
        # (например, Assist на украинском) подбираем их сами, если они не заданы явно
        if silero_lang != silero_language(self._lang) and model_id == self._model_id:
            default_model, default_voice = await self._async_defaults_for(silero_lang)
            if default_model:
                model_id = default_model
                if voice == self._speaker and default_voice:
                    voice = default_voice

        payload = {
            "text": message,
            "language": silero_lang,
            "voice": voice,
            "model_id": model_id,
            "sample_rate": int(options.get("sample_rate", self._sample_rate)),
            "put_accent": _as_bool(options.get("put_accent"), self._put_accent),
            "put_yo": _as_bool(options.get("put_yo"), self._put_yo),
        }

        try:
            audio = await self._api.synthesize(payload)
        except SileroApiError as err:
            raise HomeAssistantError(f"Silero TTS: {err}") from err
        return "wav", audio
