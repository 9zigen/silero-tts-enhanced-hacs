import aiohttp
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.silero_tts_enhanced.config_flow import DOMAIN

from .conftest import HOST


def field(result, name):
    for key, value in result["data_schema"].schema.items():
        if key == name:
            return value
    raise AssertionError(f"нет поля {name}")


def options_of(result, name):
    return field(result, name).config["options"]


def has_field(result, name):
    return any(key == name for key in result["data_schema"].schema)


async def test_user_flow_creates_entry(hass, addon):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"

    # адрес без http:// и украинский как uk, как в Home Assistant
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "silero.test:8014", "language": "uk"})
    assert result["step_id"] == "model"
    # модели языка вперёд, новые первыми, чужие в конце
    assert options_of(result, "model_id") == ["v4_ua", "v3_ua", "mykyta_v2"]

    # типографские кавычки из копипасты вычищаются
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model_id": "“v4_ua”", "sample_rate": "24000"})
    assert result["step_id"] == "voice"
    assert options_of(result, "speaker") == ["mykyta", "random"]
    assert not has_field(result, "put_accent")  # при установке галочек нет

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"speaker": "mykyta"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "host": HOST, "language": "uk", "model_id": "v4_ua", "sample_rate": 24000,
        "speaker": "mykyta", "put_accent": True, "put_yo": True, "send_wav": False,
    }


async def test_cannot_connect_shows_error_and_keeps_input(hass, aioclient_mock):
    aioclient_mock.get(f"{HOST}/status", exc=aiohttp.ClientConnectionError())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": HOST, "language": "ru"})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_old_addon_without_models_and_voices(hass, aioclient_mock):
    # у аддона до 1.1.1 нет /models и /voices, но он отвечает
    aioclient_mock.get(f"{HOST}/status", status=404)
    aioclient_mock.get(f"{HOST}/models", status=404)
    aioclient_mock.get(f"{HOST}/voices", status=404)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": HOST, "language": "ru"})
    assert result["step_id"] == "model"
    models = options_of(result, "model_id")
    assert models[0] == "v5_5_ru" and "v4_en" not in models and all(m.endswith("_ru") for m in models)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"model_id": "v5_5_ru", "sample_rate": "48000"})
    assert result["step_id"] == "voice"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"speaker": "kseniya"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["speaker"] == "kseniya"


async def test_options_flow_edits_all_settings(hass, addon):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": HOST, "language": "ru", "model_id": "v5_5_ru", "sample_rate": 48000,
        "speaker": "kseniya", "put_accent": True, "put_yo": True})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"host": HOST, "language": "ru"})
    assert result["step_id"] == "model"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"model_id": "v5_5_ru", "sample_rate": "24000"})
    assert result["step_id"] == "voice"
    for name in ("put_accent", "put_yo", "send_wav"):  # при редактировании галочки есть
        assert has_field(result, name)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"speaker": "baya", "put_accent": False, "put_yo": True, "send_wav": True})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "host": HOST, "language": "ru", "model_id": "v5_5_ru", "sample_rate": 24000,
        "speaker": "baya", "put_accent": False, "put_yo": True, "send_wav": True,
    }


async def test_options_flow_migrates_legacy_ua_language(hass, addon):
    # раньше язык сохранялся как ua; в форме он должен показаться как uk
    entry = MockConfigEntry(domain=DOMAIN, data={
        "host": HOST, "language": "ua", "model_id": "v4_ua", "sample_rate": 48000, "speaker": "mykyta"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    defaults = {str(k): k.default() for k in result["data_schema"].schema}
    assert defaults["language"] == "uk"
