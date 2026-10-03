import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

HOST = "http://silero.test:8014"

MODELS = {
    "ru": ["v5_turkic", "v3_1_ru", "v5_ru", "v5_5_ru", "v4_ru", "v5_4_ru"],
    "ua": ["mykyta_v2", "v3_ua", "v4_ua"],
    "en": ["v3_en_indic", "v3_en"],
}
VOICES = {
    ("v5_5_ru", "ru"): ["aidar", "baya", "kseniya", "eugene", "xenia"],
    ("v4_ua", "ua"): ["mykyta", "random"],
    ("v3_en", "en"): ["en_0", "en_1"],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def mock_addon(aioclient_mock, **tts_response):
    """Подставной аддон: те же адреса, что у настоящего. Ответ /tts можно задать."""
    aioclient_mock.get(f"{HOST}/status", json={"cache_size": 2, "torch_threads": 1, "cached_models": []})
    aioclient_mock.get(f"{HOST}/models", json=MODELS)
    for (model, language), names in VOICES.items():
        aioclient_mock.get(f"{HOST}/voices?model_id={model}&language={language}",
                           json={"model_id": model, "language": language, "voices": names})
    aioclient_mock.post(f"{HOST}/tts", **(tts_response or {"content": b"RIFF....WAVEfake"}))
    return aioclient_mock


@pytest.fixture
def addon(aioclient_mock):
    return mock_addon(aioclient_mock)
