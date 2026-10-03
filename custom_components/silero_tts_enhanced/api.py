"""Клиент HTTP API аддона Silero."""
import asyncio
import re

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

QUOTES = "\"'`“”„‟‘’‚«»"

# В Home Assistant украинский это uk, а у Silero ua
HA_TO_SILERO = {"uk": "ua"}
SILERO_TO_HA = {"ua": "uk"}

# Если аддон старый и не умеет отдавать список моделей
FALLBACK_MODELS = ["v5_5_ru", "v5_ru", "v4_ru", "v3_1_ru", "v3_en", "v3_de", "v3_es", "v3_fr",
                   "v4_ua", "v3_ua", "v3_tt", "v4_uz"]

STATUS_TIMEOUT = 10
VOICES_TIMEOUT = 60  # аддон может загружать модель
TTS_TIMEOUT = 180  # длинный текст на слабом процессоре


class SileroApiError(Exception):
    """Ошибка обращения к аддону; текст можно показывать пользователю."""


def clean(value) -> str:
    """Убирает пробелы и кавычки, включая типографские, которые попадают при копировании."""
    if value is None:
        return ""
    return str(value).strip().strip(QUOTES).strip()


def normalize_host(value) -> str:
    host = clean(value).rstrip("/")
    if host and "://" not in host:
        host = f"http://{host}"
    return host


def silero_language(language) -> str:
    """ru-RU, en_US, uk -> ru, en, ua."""
    code = clean(language).replace("_", "-").split("-")[0].lower()
    return HA_TO_SILERO.get(code, code)


def ha_language(language) -> str:
    code = clean(language).lower()
    return SILERO_TO_HA.get(code, code)


def sort_models(model_ids, language) -> list[str]:
    """Сначала модели языка, внутри новые вперёд: v5_5_ru, v5_ru, v4_ru, v3_1_ru."""
    def key(model_id):
        numbers = [int(n) for n in re.findall(r"\d+", model_id)][:3]
        numbers += [0] * (3 - len(numbers))
        return (not model_id.endswith(f"_{language}"), [-n for n in numbers], model_id)

    return sorted(model_ids, key=key)


def fallback_models(language) -> list[str]:
    models = sort_models(FALLBACK_MODELS, language)
    matching = [m for m in models if m.endswith(f"_{language}")]
    return matching or models


async def _error_text(response) -> str:
    try:
        detail = (await response.json(content_type=None)).get("detail")
    except Exception:  # noqa: BLE001 - тело ответа может быть чем угодно
        detail = None
    return str(detail or f"HTTP {response.status}")[:300]


class SileroApi:
    def __init__(self, hass, host):
        self._session = async_get_clientsession(hass)
        self.host = normalize_host(host)

    async def _get(self, path, timeout, params=None):
        """None, если у аддона нет такого адреса (старая версия)."""
        try:
            async with self._session.get(f"{self.host}{path}", params=params,
                                         timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 404:
                    return None
                if response.status != 200:
                    raise SileroApiError(await _error_text(response))
                return await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SileroApiError(f"нет связи с {self.host} ({type(err).__name__})") from err

    async def reachable(self) -> bool:
        try:
            await self._get("/status", STATUS_TIMEOUT)
        except SileroApiError:
            return False
        return True

    async def models(self):
        """{язык: [модели]} или None у старого аддона."""
        return await self._get("/models", STATUS_TIMEOUT)

    async def voices(self, model_id, language):
        """Список голосов или None у старого аддона."""
        data = await self._get("/voices", VOICES_TIMEOUT, {"model_id": model_id, "language": language})
        return None if data is None else list(data.get("voices", []))

    async def synthesize(self, payload) -> bytes:
        try:
            async with self._session.post(f"{self.host}/tts", json=payload,
                                          timeout=aiohttp.ClientTimeout(total=TTS_TIMEOUT)) as response:
                if response.status != 200:
                    raise SileroApiError(await _error_text(response))
                audio = await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SileroApiError(f"нет связи с {self.host} ({type(err).__name__})") from err
        if not audio:
            raise SileroApiError("аддон вернул пустой ответ")
        return audio
