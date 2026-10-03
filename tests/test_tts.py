import aiohttp
import pytest
from homeassistant.components import tts
from homeassistant.components.tts.media_source import generate_media_source_id
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.silero_tts_enhanced.config_flow import DOMAIN

from .conftest import HOST, mock_addon

ENGINE = "tts.silero_tts_enhanced"


async def setup_entry(hass, language="ru", model="v5_5_ru", speaker="kseniya", **extra):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": HOST, "language": language, "model_id": model, "sample_rate": 48000,
        "speaker": speaker, "put_accent": True, "put_yo": True, **extra})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def speak(hass, message="Привет", language=None, options=None):
    # В тестах нет ffmpeg: просим wav, как и отдаёт аддон, чтобы Home Assistant не конвертировал
    options = {"preferred_format": "wav", **(options or {})}
    source = generate_media_source_id(hass, message, engine=ENGINE, language=language, options=options, cache=False)
    return await tts.async_get_media_source_audio(hass, source)


def tts_payload(addon):
    posts = [call for call in addon.mock_calls if call[0] == "POST"]
    return posts[-1][2]


async def test_default_language_uses_saved_settings(hass, addon):
    await setup_entry(hass)
    extension, data = await speak(hass, "Включи свет")
    assert extension == "wav" and data.startswith(b"RIFF")
    assert tts_payload(addon) == {
        "text": "Включи свет", "language": "ru", "voice": "kseniya", "model_id": "v5_5_ru",
        "sample_rate": 48000, "put_accent": True, "put_yo": True,
    }
    # для языка по умолчанию лишних запросов к аддону нет
    assert not [c for c in addon.mock_calls if str(c[1]).endswith("/models")]


async def test_ukrainian_is_supported_and_mapped(hass, addon):
    # главная ошибка: HA отвергал язык uk, потому что в списке был только ua
    await setup_entry(hass)
    extension, _ = await speak(hass, "Привіт", language="uk")
    assert extension == "wav"
    # модель и голос подобраны под язык, а не взяты от русского
    assert tts_payload(addon) == {
        "text": "Привіт", "language": "ua", "voice": "mykyta", "model_id": "v4_ua",
        "sample_rate": 48000, "put_accent": True, "put_yo": True,
    }


async def test_english_gets_its_own_model(hass, addon):
    await setup_entry(hass)
    await speak(hass, "Hello", language="en")
    payload = tts_payload(addon)
    assert (payload["language"], payload["model_id"], payload["voice"]) == ("en", "v3_en", "en_0")


async def test_legacy_ua_default_language_still_works(hass, addon):
    await setup_entry(hass, language="ua", model="v4_ua", speaker="mykyta")
    await speak(hass, "Привіт")
    assert tts_payload(addon)["language"] == "ua"


async def test_explicit_options_win(hass, addon):
    await setup_entry(hass)
    await speak(hass, "Привіт", language="uk", options={"model_id": "v3_ua", "voice": "random"})
    payload = tts_payload(addon)
    assert (payload["model_id"], payload["voice"]) == ("v3_ua", "random")


async def test_curly_quotes_in_call_options_are_cleaned(hass, addon):
    await setup_entry(hass)
    await speak(hass, "Привет", options={"model_id": "“v5_5_ru”", "voice": "“xenia”"})
    payload = tts_payload(addon)
    assert (payload["model_id"], payload["voice"]) == ("v5_5_ru", "xenia")


async def test_boolean_options_from_yaml_strings(hass, addon):
    await setup_entry(hass)
    await speak(hass, "Привет", options={"put_accent": "false"})
    assert tts_payload(addon)["put_accent"] is False


async def test_addon_error_text_reaches_the_user(hass, aioclient_mock, caplog):
    # раньше было безликое "Silero Error" и пустой ответ, теперь причина от аддона
    mock_addon(aioclient_mock, status=400, json={"detail": "Голос 'x' недоступен для модели 'v5_5_ru'"})
    await setup_entry(hass)
    with pytest.raises(HomeAssistantError, match="Silero TTS: Голос 'x' недоступен для модели 'v5_5_ru'"):
        await speak(hass, "Привет")
    assert "Silero TTS: Голос 'x' недоступен" in caplog.text  # и в логе Home Assistant


async def test_connection_error_is_explained(hass, aioclient_mock):
    mock_addon(aioclient_mock, exc=aiohttp.ClientConnectionError())
    await setup_entry(hass)
    with pytest.raises(HomeAssistantError, match=f"Silero TTS: нет связи с {HOST}"):
        await speak(hass, "Привет")


async def test_supported_voices_for_assist(hass, addon):
    await setup_entry(hass)
    entity = hass.data[tts.DATA_COMPONENT].get_entity(ENGINE)
    voices = entity.async_get_supported_voices("ru")
    assert [v.voice_id for v in voices] == ["aidar", "baya", "kseniya", "eugene", "xenia"]
    assert entity.async_get_supported_voices("uk") is None  # для других языков список не известен заранее


async def test_supported_languages_include_ukrainian(hass, addon):
    await setup_entry(hass)
    entity = hass.data[tts.DATA_COMPONENT].get_entity(ENGINE)
    assert "uk" in entity.supported_languages


async def test_send_wav_option_skips_home_assistant_conversion(hass, addon):
    # без ffmpeg это пройдёт только если Home Assistant не пытается конвертировать в mp3
    await setup_entry(hass, send_wav=True)
    entity = hass.data[tts.DATA_COMPONENT].get_entity(ENGINE)
    assert entity.default_options["preferred_format"] == "wav"
    source = generate_media_source_id(hass, "Привет", engine=ENGINE, cache=False)
    extension, data = await tts.async_get_media_source_audio(hass, source)
    assert extension == "wav" and data.startswith(b"RIFF")


async def test_wav_is_not_forced_by_default(hass, addon):
    await setup_entry(hass)
    entity = hass.data[tts.DATA_COMPONENT].get_entity(ENGINE)
    assert "preferred_format" not in entity.default_options
