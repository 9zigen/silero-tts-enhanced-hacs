# Silero TTS Enhanced - Home Assistant Integration

A UI-configurable Home Assistant integration for Silero TTS. No more YAML editing!

It connects to the **[Silero TTS Enhanced Engine add-on](https://github.com/9zigen/silero-tts-enhanced-addon)** and exposes it as a native TTS provider for media players and the Assist voice assistant. Requires Home Assistant 2025.8 or newer.

## Features
- ⚙️ **Setup in the UI, three short steps:** server and language, then model, then voice. Model and voice lists come straight from the add-on, and the connection is checked before anything is saved. You can still type a value that is not in a list.
- 🗣️ **Assist ready, in several languages:** Russian, Ukrainian (`uk`), English and more. For a language other than your default one, the integration picks a suitable model and voice by itself, so an Ukrainian or English Assist pipeline works without extra options.
- 🎙️ **Voice list for Assist** pipelines, loaded from the add-on.
- 💬 **Clear errors:** when something is wrong (unknown voice, add-on not reachable), Home Assistant shows the add-on's own reason instead of a silent failure.
- 🧹 **Copy-paste proof:** typographic quotes (`“ ”`) that sneak into fields are stripped.
- 🚀 **Asynchronous:** non-blocking HTTP requests, the system never freezes.

## Installation via HACS
1. Install and start the companion [Silero add-on](https://github.com/9zigen/silero-tts-enhanced-addon) (version 1.2.0 or newer of this fork gives you the model and voice lists; with an older add-on the lists fall back to built-in defaults).
2. Open **HACS** -> **Integrations**.
3. Click the three dots (top right) -> **Custom repositories**.
4. Add this repository URL as an **Integration**.
5. Click **Download**, then **Restart Home Assistant**.

## Setup
1. Go to **Settings** -> **Devices & services**.
2. Click **+ Add Integration** and search for `Silero TTS Enhanced`.
3. Enter the add-on address (for example `http://homeassistant.local:8014`) and your default language.
4. Pick the model, then the voice. Done!
5. Later you can change everything under **Configure**. There you also find the auto-accent and `Ё` switches, and **Send WAV directly** (see below).

### Speed tip: Send WAV directly
By default Home Assistant converts the add-on's WAV to MP3 with ffmpeg for every phrase. If your speaker plays WAV, turn on **Send WAV directly** in the settings: Home Assistant then skips the conversion. You can also try it for a single call with `preferred_format: wav` (see the example below).

### Languages
Use the Home Assistant language code: `ru`, `uk`, `en`, `de`, `es`, `fr`, `tt`, `uz`. When a phrase is requested in a language different from your default one, the newest model and its first voice for that language are used unless you pass `model_id` and `voice` yourself.

> If you use several languages, raise **Models kept in RAM** in the add-on settings to the number of languages, so switching between them does not reload models.

### Available Models and Speakers

| Language | Model Version | Speaker Names |
| :--- | :--- | :--- |
| **Russian** | `v5_5_ru`, `v5_ru` | aidar, baya, kseniya, xenia, eugene |
| **Ukrainian** | `v4_ua` | mykyta, random |
| **Uzbek** | `v4_uz` | dilnavoz |
| **English** | `v3_en` | en_0, en_1, ..., en_117, random |
| **Spanish** | `v3_es` | es_0, es_1, es_2 |
| **French** | `v3_fr` | fr_0, fr_1, fr_2, fr_3, fr_4, fr_5 |
| **German** | `v3_de` | bernd_ungerer, eva_k, friedrich, hokuspokus, karlsson |
| **Tatar** | `v3_tt` | dilyara |

and more, see [Silero Models](https://github.com/snakers4/silero-models/blob/master/models.yml). The exact lists for your add-on are offered in the setup dialog.

## Usage in Automations
Use plain straight quotes in YAML; typographic quotes `“ ”` are not YAML quotes.

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: "Hello world, the smart home is ready."
  language: en
  options:
    preferred_format: wav
```

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: "Привіт, у домі все гаразд."
  language: uk
  options:
    model_id: v4_ua
    voice: mykyta
```

## Development
Tests run against the real Home Assistant test harness:

```bash
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt mutagen ha-ffmpeg
pytest
```

## 📝 Acknowledgements & License
This project is an unofficial wrapper/integration. The core Text-to-Speech neural models are developed and owned by the [Silero Team](https://github.com/snakers4/silero-models).
The models are published under the **CC BY-NC** (Non-Commercial) license. Please respect the authors' rights and use this integration strictly for personal, non-commercial purposes.

-----------------------------------------------------------------------
# Silero TTS Enhanced — интеграция с Home Assistant

Интеграция Silero TTS с Home Assistant с настройкой через интерфейс. Больше не нужно редактировать YAML!

Она подключается к **[дополнению Silero TTS Enhanced Engine](https://github.com/9zigen/silero-tts-enhanced-addon)** и предоставляет его как встроенный TTS для медиаплееров и голосового помощника Assist. Нужен Home Assistant 2025.8 или новее.

## Особенности
- ⚙️ **Настройка через интерфейс, три коротких шага:** сервер и язык, затем модель, затем голос. Списки моделей и голосов берутся из дополнения, а связь с ним проверяется до сохранения. Значение, которого нет в списке, всё равно можно ввести вручную.
- 🗣️ **Готово для Assist на нескольких языках:** русский, украинский (`uk`), английский и другие. Для языка, отличного от языка по умолчанию, интеграция сама подбирает модель и голос, поэтому Assist на украинском или английском работает без дополнительных опций.
- 🎙️ **Список голосов для конвейеров Assist** из дополнения.
- 💬 **Понятные ошибки:** если что-то не так (неизвестный голос, дополнение недоступно), Home Assistant показывает причину от самого дополнения, а не молчит.
- 🧹 **Защита от копипасты:** типографские кавычки (`“ ”`), попавшие в поля, удаляются.
- 🚀 **Асинхронность:** неблокирующие HTTP-запросы, система не зависает.

## Установка через HACS
1. Установите и запустите сопутствующее [дополнение Silero](https://github.com/9zigen/silero-tts-enhanced-addon) (версия 1.2.0 или новее этого форка даёт списки моделей и голосов; со старым дополнением списки берутся из встроенных значений).
2. Откройте **HACS** -> **Интеграции**.
3. Нажмите на три точки (вверху справа) -> **Пользовательские репозитории**.
4. Добавьте URL этого репозитория в качестве **Интеграции**.
5. Нажмите **Скачать**, затем **Перезапустить Home Assistant**.

## Настройка
1. Перейдите в **Настройки** -> **Устройства и службы**.
2. Нажмите **+ Добавить интеграцию** и найдите `Silero TTS Enhanced`.
3. Введите адрес дополнения (например, `http://homeassistant.local:8014`) и язык по умолчанию.
4. Выберите модель, затем голос. Готово!
5. Позже всё можно изменить через **Настроить**. Там же переключатели автоударений и `Ё` и **Отдавать WAV напрямую** (см. ниже).

### Совет по скорости: отдавать WAV напрямую
По умолчанию Home Assistant конвертирует WAV из дополнения в MP3 через ffmpeg для каждой фразы. Если ваша колонка играет WAV, включите **Отдавать WAV напрямую** в настройках: тогда конвертации не будет. Для одного вызова то же даёт `preferred_format: wav` (пример ниже).

### Языки
Используйте код языка Home Assistant: `ru`, `uk`, `en`, `de`, `es`, `fr`, `tt`, `uz`. Если фраза запрошена на языке, отличном от языка по умолчанию, берутся новейшая модель и её первый голос для этого языка, пока вы сами не передали `model_id` и `voice`.

> Если вы используете несколько языков, увеличьте **Моделей в оперативной памяти** в настройках дополнения до числа языков, чтобы переключение между ними не перезагружало модели.

### Модели и голоса

| Язык | Версия модели | Голоса |
| :--- | :--- | :--- |
| **Русский** | `v5_5_ru`, `v5_ru` | aidar, baya, kseniya, xenia, eugene |
| **Украинский** | `v4_ua` | mykyta, random |
| **Узбекский** | `v4_uz` | dilnavoz |
| **Английский** | `v3_en` | en_0, en_1, ..., en_117, random |
| **Испанский** | `v3_es` | es_0, es_1, es_2 |
| **Французский** | `v3_fr` | fr_0, fr_1, fr_2, fr_3, fr_4, fr_5 |
| **Немецкий** | `v3_de` | bernd_ungerer, eva_k, friedrich, hokuspokus, karlsson |
| **Татарский** | `v3_tt` | dilyara |

и другие, смотрите [Silero Models](https://github.com/snakers4/silero-models/blob/master/models.yml). Точные списки для вашего дополнения предлагаются в окне настройки.

## Использование в автоматизациях
Используйте в YAML обычные прямые кавычки; типографские `“ ”` кавычками YAML не являются.

```yaml
action: tts.speak
target:
  entity_id: tts.silero_tts_enhanced
data:
  media_player_entity_id: media_player.living_room
  message: "Внимание. Температура процессора достигла 80 градусов."
  options:
    model_id: v5_5_ru
    voice: xenia
    put_accent: true
    preferred_format: wav
```

## Разработка
Тесты запускаются на настоящем тестовом окружении Home Assistant:

```bash
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt mutagen ha-ffmpeg
pytest
```

## 📝 Лицензия и Авторы
Этот проект является неофициальной интеграцией-оберткой. Сами нейросетевые модели синтеза речи разработаны и принадлежат команде [Silero Team](https://github.com/snakers4/silero-models).
Модели распространяются под некоммерческой лицензией **CC BY-NC**. Пожалуйста, уважайте труд авторов и используйте этот проект только в некоммерческих и личных целях.
