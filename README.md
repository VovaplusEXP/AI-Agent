# 🤖 AI Agent - ReAct агент с автономным рассуждением



[![Version](https://img.shields.io/badge/version-0.0.1--alpha-blue.svg)](CHANGELOG.md)[![Version](## 📖 Документация

[![Status](https://img.shields.io/badge/status-alpha-yellow.svg)](ROADMAP.md)

[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)- **[CHANGELOG.md](CHANGELOG.md)** - История изменений

[![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)- **[ROADMAP.md](ROADMAP.md)** - Планы развития

- **[ALPHA_RELEASE.md](ALPHA_RELEASE.md)** - Анонс релиза Alpha v0.0.1

**Автономный AI-агент на базе Gemma-3n-E4B** с поддержкой ReAct цикла (Reason → Action → Observation), долговременной памятью и адаптивным управлением контекстом.- **[doc/](doc/)** - Техническая документация

  - [DOCUMENTATION.md](doc/DOCUMENTATION.md) - Детальная документация

> **⚠️ Alpha версия:** Проект находится в активной разработке. Основной функционал работает, но возможны изменения API и поведения. См. [ROADMAP.md](ROADMAP.md) для планов развития.  - [PATCH_v3.3.1_SUMMARY.md](doc/PATCH_v3.3.1_SUMMARY.md) - Последний патч

  - [PATCH_v3.3.1_TEST_RESULTS.md](doc/PATCH_v3.3.1_TEST_RESULTS.md) - Результаты тестов/img.shields.io/badge/version-0.0.1--alpha-blue.svg)](CHANGELOG.md)

---[![Status](https://img.shields.io/badge/status-alpha-yellow.svg)](ROADMAP.md)

[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)

## 🎯 Что это?[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)



**AI Agent** - это автономная система, которая может:**Автономный AI-агент на базе Gemma-3n-E4B** с поддержкой ReAct цикла (Reason → Action → Observation), долговременной памятью и адаптивным управлением контекстом.

- 🧠 **Рассуждать** о задачах и планировать решения

- 🔧 **Выполнять действия** через набор из 19 инструментов> **⚠️ Alpha версия:** Проект находится в активной разработке. Основной функционал работает, но возможны изменения API и поведения. См. [ROADMAP.md](ROADMAP.md) для планов развития.

- 💾 **Запоминать** контекст и важные факты (3-уровневая память)

- 📊 **Анализировать** код, файлы, веб-страницы---

- 🔄 **Адаптироваться** к размеру контекста (интеллектуальное сжатие)

- 🌐 **Искать** информацию в интернете и обрабатывать её## 🎯 Что это?



---**AI Agent** - это автономная система, которая может:

- 🧠 **Рассуждать** о задачах и планировать решения

## ✨ Основные возможности (v0.0.1-alpha)- 🔧 **Выполнять действия** через набор из 19 инструментов

- 💾 **Запоминать** контекст и важные факты (3-уровневая память)

### 🎯 ReAct цикл- 📊 **Анализировать** код, файлы, веб-страницы

- **Автономное рассуждение:** Thought → Action → Observation- 🔄 **Адаптироваться** к размеру контекста (интеллектуальное сжатие)

- **Флаговый формат:** 100% успешность парсинга (без JSON escaping)- 🌐 **Искать** информацию в интернете и обрабатывать её

- **50 циклов на задачу:** Достаточно для сложных многошаговых задач

- **Self-reflection:** Автоматический анализ ошибок и их исправление---



### 💾 Трёхуровневая память## ✨ Основные возможности (v0.0.1-alpha)

- **L1 (Scratchpad):** Текущая цель, план, последний результат

- **L2 (История):** Интеллектуальное сжатие (80-85% экономии)### 🎯 ReAct цикл

- **L3 (Векторная):** FAISS + SentenceTransformer- **Автономное рассуждение:** Thought → Action → Observation

  - Глобальная память (shared)- **Флаговый формат:** 100% успешность парсинга (без JSON escaping)

  - Проектная память (per-chat)- **50 циклов на задачу:** Достаточно для сложных многошаговых задач

- **Self-reflection:** Автоматический анализ ошибок и их исправление

### 🧠 Интеллектуальное сжатие

- **LLM-based:** Сжатие длинных результатов через LLM### 💾 Трёхуровневая память

- **Извлечение фактов:** URLs, файлы, версии, технологии- **L1 (Scratchpad):** Текущая цель, план, последний результат

- **Автоматическое:** Срабатывает при >80% утилизации контекста- **L2 (История):** Интеллектуальное сжатие (80-85% экономии)

- **Невидимое:** Пользователь не замечает процесс- **L3 (Векторная):** FAISS + SentenceTransformer

  - Глобальная память (shared)

### 🔧 19 инструментов  - Проектная память (per-chat)

- **Файлы:** read, write, create, edit, replace, list

- **Анализ:** analyze_code### 🧠 Интеллектуальное сжатие

- **Shell:** run_shell_command- **LLM-based:** Сжатие длинных результатов через LLM

- **Веб:** internet_search, web_fetch, web_search_in_page, web_get_structure- **Извлечение фактов:** URLs, файлы, версии, технологии

- **Память:** list, add, delete- **Автоматическое:** Срабатывает при >80% утилизации контекста

- **Завершение:** finish- **Невидимое:** Пользователь не замечает процесс



### 🛡️ Защита от зацикливания### � 19 инструментов

- **Валидация дубликатов:** Блокирует повторные web_fetch/internet_search- **Файлы:** read, write, create, edit, replace, list

- **Явный паттерн:** internet_search → web_fetch → web_search_in_page → create_file- **Анализ:** analyze_code

- **Умные подсказки:** Агент получает инструкции при попытке дубликата- **Shell:** run_shell_command

- **Веб:** internet_search, web_fetch, web_search_in_page, web_get_structure

### 🚀 Производительность- **Память:** list, add, delete

- **Контекст:** 24k токенов (n_ctx=24576)- **Завершение:** finish

- **GPU:** Полная поддержка (RTX 4060: ~72% VRAM)

- **Утилизация:** 95% GPU (стабильно)### 🛡️ Защита от зацикливания

- **Скорость:** ~7-10 секунд на цикл- **Валидация дубликатов:** Блокирует повторные web_fetch/internet_search

- **Явный паттерн:** internet_search → web_fetch → web_search_in_page → create_file

---- **Умные подсказки:** Агент получает инструкции при попытке дубликата



## 📖 Документация### 🚀 Производительность

- **Контекст:** 24k токенов (n_ctx=24576)

- **[CHANGELOG.md](CHANGELOG.md)** - История изменений- **GPU:** Полная поддержка (RTX 4060: ~72% VRAM)

- **[ROADMAP.md](ROADMAP.md)** - Планы развития- **Утилизация:** 95% GPU (стабильно)

- **[ALPHA_RELEASE.md](ALPHA_RELEASE.md)** - Анонс релиза Alpha v0.0.1- **Скорость:** ~7-10 секунд на цикл

- **[doc/](doc/)** - Техническая документация

  - [DOCUMENTATION.md](doc/DOCUMENTATION.md) - Детальная документация---

  - [PATCH_v3.3.1_SUMMARY.md](doc/PATCH_v3.3.1_SUMMARY.md) - Последний патч

  - [PATCH_v3.3.1_TEST_RESULTS.md](doc/PATCH_v3.3.1_TEST_RESULTS.md) - Результаты тестов## � Документация



---- **[CHANGELOG.md](CHANGELOG.md)** - История изменений

- **[ROADMAP.md](ROADMAP.md)** - Планы развития

## 🚀 Быстрый старт- **[DOCS.md](DOCS.md)** - Детальная документация

- **[PATCH_v3.3.1_SUMMARY.md](PATCH_v3.3.1_SUMMARY.md)** - Последний патч

### 1. Требования- **[PATCH_v3.3.1_TEST_RESULTS.md](PATCH_v3.3.1_TEST_RESULTS.md)** - Результаты тестов



- **Python:** 3.11 или выше---

- **GPU:** NVIDIA с поддержкой CUDA (рекомендуется 8+ GB VRAM)

- **RAM:** 16+ GB (рекомендуется)## 🚀 Быстрый старт

- **Диск:** ~10 GB свободного места

### 1. Установка зависимостей

### 2. Скачайте модель Gemma

```bash

Модель **НЕ включена** в репозиторий. Скачайте самостоятельно:pip install -r requirements.txt

```

```bash

# Создайте директорию для модели### 2. Запуск агента

mkdir -p ai/

```bash

# Скачайте Gemma-3n-E4B-it-IQ4_XS (около 3.5 GB)python cli.py

wget -O ai/gemma-3n-E4B-it-IQ4_XS.gguf \```

  https://huggingface.co/grapevine-AI/gemma-3n-E4B-it-gguf/resolve/main/gemma-3n-E4B-it-IQ4_XS.gguf

```### 3. Первая задача



> **📝 Примечание:** Модель Gemma лицензирована под [Gemma Terms of Use](https://www.kaggle.com/models/google/gemma/license/consent). Код проекта лицензирован под AGPL-3.0.```

👤 Введите задачу: Создай файл hello.py с функцией приветствия

### 3. Установка зависимостей

🤖 Агент:

```bash<THOUGHT>

# Клонируйте репозиторийСоздам простой Python файл с функцией для приветствия

git clone https://github.com/YOUR_USERNAME/ai-react-agent.git<TOOL>

cd ai-react-agentwrite_file

<PARAMS>

# Создайте виртуальное окружение{"file_path": "hello.py"}

python -m venv venv<CONTENT>

source venv/bin/activate  # Linux/Macdef greet(name):

# или: venv\Scripts\activate  # Windows    print(f"Привет, {name}!")



# Установите зависимостиif __name__ == "__main__":

pip install -r requirements.txt    greet("Мир")

```<END>



### 4. Настройка окружения✅ Файл hello.py создан!

```

```bash

# Скопируйте пример конфигурации---

cp .env.example .env

## 📦 Возможности

# Отредактируйте .env (опционально)

# Добавьте Google API ключи для internet_search### 🔧 Инструменты (15+)

nano .env

```**Работа с файлами:**

- `read_file` - чтение файлов

### 5. Запуск агента- `write_file` / `create_file` - создание файлов  

- `edit_file_at_line` - редактирование по номерам строк

```bash- `replace_in_file` - замена текста

python cli.py- `list_directory` - просмотр содержимого

```

**Анализ кода:**

### 6. Первая задача- `analyze_code` - AST анализ Python файлов

- `run_shell_command` - выполнение команд

```

👤 Введите задачу: Создай файл hello.py с функцией приветствия**Поиск информации:**

- `internet_search` - поиск в интернете

🤖 Агент:- `web_fetch` - получение содержимого веб-страниц

<THOUGHT>

Создам простой Python файл с функцией для приветствия**Память:**

<TOOL>- `add_memory` - сохранение в долговременную память

create_file- `list_memories` - просмотр сохраненных фактов

<PARAMS>- `delete_memory` - удаление из памяти

{"file_path": "hello.py"}

<CONTENT>📖 [Полный список инструментов](doc/MASTER_DOCUMENTATION.md#инструменты)

def greet(name):

    print(f"Привет, {name}!")### 💾 Трехуровневая система памяти



if __name__ == "__main__":- **L1 (Рабочая):** Текущий контекст и история

    greet("Мир")- **L2 (Краткосрочная):** Важные факты из текущей сессии (FAISS)

<END>- **L3 (Долговременная):** Глобальные знания (FAISS, персистентность)



✅ Файл hello.py создан!📖 [Подробнее о памяти](doc/MASTER_DOCUMENTATION.md#система-памяти)

```

### 🎯 Adaptive Context Manager v2.2.0

---

Умное управление контекстом в пределах 20K токенов:

## 🛠️ Технологии

- **Динамическое перераспределение** бюджета токенов

- **LLM:** [Gemma-3n-E4B](https://huggingface.co/grapevine-AI/gemma-3n-E4B-it-gguf) (IQ4_XS, 3B параметров)- **Приоритизация** критичного контекста

- **Фреймворк:** [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)- **Автоматическое сжатие** истории при нехватке места

- **Память:** [FAISS](https://github.com/facebookresearch/faiss) (vector search)- **RAG для памяти** - только релевантные факты

- **Эмбеддинги:** [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (Sentence Transformers)

- **Python:** 3.11+📖 [Документация Context Manager](doc/versions/v2.2.0/ADAPTIVE_CONTEXT_MANAGER.md)



------



## 📊 Тестирование (v3.3.1)## 🏗️ Архитектура



**Запрос:** "Найди информацию о Python 3.13"```

┌─────────────────────────────────────────────────┐

**Результаты:**│              User Input (Задача)                │

- ✅ **13 циклов** выполнения└────────────────────┬────────────────────────────┘

- ✅ **0 дубликатов** (валидация работает!)                     │

- ✅ **3 компрессии** истории┌────────────────────▼────────────────────────────┐

- ✅ **100% корректный паттерн:**│          ReAct Cycle (Agent.run_cycle)          │

  ```│  ┌─────────────────────────────────────────┐   │

  internet_search → web_fetch → web_search_in_page → create_file│  │  1. REASON (думаю, планирую)            │   │

  ```│  │  2. ACTION (выбираю инструмент)         │   │

- ✅ Файл `python_3.13_info.md` создан успешно│  │  3. OBSERVATION (получаю результат)     │   │

- ✅ **GPU:** 95% утилизация, стабильно│  └─────────────────────────────────────────┘   │

- ✅ **VRAM:** 72% (5566 MB), headroom 2.6GB└────────────────────┬────────────────────────────┘

                     │

📄 См. [doc/PATCH_v3.3.1_TEST_RESULTS.md](doc/PATCH_v3.3.1_TEST_RESULTS.md) для полного отчёта.┌────────────────────▼────────────────────────────┐

│         Parser v3.0.0 (Флаговый формат)         │

---│  ┌──────────────────┐   ┌──────────────────┐   │

│  │  Флаги <THOUGHT> │ → │  JSON (fallback) │   │

## 📊 Версионирование│  │  <TOOL><PARAMS>  │   │                  │   │

│  │  <CONTENT><END>  │   │                  │   │

Проект использует [Semantic Versioning](https://semver.org/):│  └──────────────────┘   └──────────────────┘   │

- **MAJOR.MINOR.PATCH-stage**└────────────────────┬────────────────────────────┘

- **Stage:** `alpha` → `beta` → `rc` → `stable`                     │

┌────────────────────▼────────────────────────────┐

### Текущий этап: Alpha (v0.0.1)│              Tool Execution                      │

- ✅ Основной функционал работает│  ┌─────────────────────────────────────────┐   │

- ⚠️ Возможны breaking changes│  │  15+ инструментов (файлы, код, web...)  │   │

- 🔬 Экспериментальные фичи│  └─────────────────────────────────────────┘   │

└────────────────────┬────────────────────────────┘

### Планы:                     │

- **Beta (v0.1.0):** Стабилизация, Web UI, новые инструменты (Q1 2025)┌────────────────────▼────────────────────────────┐

- **RC (v0.9.0):** Подготовка к релизу, финальное тестирование (Q2 2025)│        Memory & Context Management               │

- **Stable (v1.0.0+):** Production-ready, обратная совместимость (Q3-Q4 2025)│  ┌────────────┐  ┌──────────────────────────┐  │

│  │ L1: Рабочая│  │  Adaptive Context Mgr    │  │

📄 См. [ROADMAP.md](ROADMAP.md) для детальных планов развития.│  │ L2: FAISS  │→ │  (20K tokens, приоритеты)│  │

│  │ L3: Global │  └──────────────────────────┘  │

---│  └────────────┘                                 │

└─────────────────────────────────────────────────┘

## 🤝 Вклад в проект```



Приветствуются:📖 [Детальная архитектура](doc/MASTER_DOCUMENTATION.md#архитектура)

- 🐛 **Баг-репорты** - нашли проблему? Создайте issue

- ✨ **Идеи новых функций** - предложите улучшения---

- 📝 **Улучшение документации** - опечатки, неясности, примеры

- 🔧 **Pull requests** - новые инструменты, фиксы, тесты## 📚 Документация



**Как начать:**### Главные документы

1. Fork репозитория

2. Создайте ветку для вашей фичи (`git checkout -b feature/amazing-feature`)- **[DOCS.md](DOCS.md)** - навигация по всей документации

3. Commit изменения (`git commit -m 'Add amazing feature'`)- **[doc/MASTER_DOCUMENTATION.md](doc/MASTER_DOCUMENTATION.md)** - полная документация (800+ строк)

4. Push в ветку (`git push origin feature/amazing-feature`)- **[doc/INDEX.md](doc/INDEX.md)** - структурированный указатель

5. Создайте Pull Request- **[doc/CHANGELOG.md](doc/CHANGELOG.md)** - история изменений



> **⚠️ Важно:** Проект лицензирован под AGPL-3.0. Любые модификации, используемые в сетевых сервисах, должны быть открыты.### Версии



---- **[v3.0.0 - Флаговый формат](doc/versions/v3.0.0/)** ← текущая

- [v2.2.0 - Adaptive Context](doc/versions/v2.2.0/)

## 📝 Лицензия- [v2.1.2 - Hotfix escaping](doc/versions/v2.1.2/)

- [v2.1.0 - Новые инструменты](doc/versions/v2.1.0/)

**Код проекта:** GNU Affero General Public License v3.0 (AGPL-3.0) - см. [LICENSE](LICENSE)

### Быстрые ссылки

**Модель Gemma:** [Gemma Terms of Use](https://www.kaggle.com/models/google/gemma/license/consent) (Google)

- 🚀 [Quick Start Guide](doc/README.md#быстрый-старт)

> **📌 Примечание:** AGPL-3.0 требует открытия исходного кода при использовании в сетевых сервисах. Это гарантирует, что улучшения проекта останутся открытыми. Если вам нужна коммерческая лицензия, свяжитесь с автором.- 🔧 [Список инструментов](doc/MASTER_DOCUMENTATION.md#инструменты)

- 💾 [Система памяти](doc/MASTER_DOCUMENTATION.md#система-памяти)

---- 🐛 [Troubleshooting](doc/MASTER_DOCUMENTATION.md#troubleshooting)

- 📊 [API Reference](doc/MASTER_DOCUMENTATION.md#api-reference)

## 🙏 Благодарности

---

- **Google** - [Gemma](https://ai.google.dev/gemma) модели

- **[llama-cpp-python](https://github.com/abetlen/llama-cpp-python)** - отличная производительность и стабильность## 🛠️ Технологии

- **[FAISS](https://github.com/facebookresearch/faiss)** (Meta) - быстрый векторный поиск

- **[SentenceTransformers](https://www.sbert.net/)** - эффективные эмбеддинги- **LLM:** Gemma-3n-E4B (IQ4_XS, 32K context, мультимодальная)

- **[HuggingFace](https://huggingface.co/)** - экосистема и инструменты- **Фреймворк:** llama-cpp-python

- **Память:** FAISS (vector search)

---- **Эмбеддинги:** all-MiniLM-L6-v2 (Sentence Transformers)

- **Python:** 3.11+

<div align="center">

---

**Создано с ❤️ для автономного AI**

## 📊 Метрики производительности

[Документация](doc/DOCUMENTATION.md) • [Changelog](CHANGELOG.md) • [Roadmap](ROADMAP.md)

| Метрика | v2.1.2 | v3.0.0 | Улучшение |

**v0.0.1-alpha** | 13 октября 2025|---------|--------|--------|-----------|

| **Успешность парсинга** | ~90% | 100% | +10% |

</div>| **Скорость парсинга** | 15ms | 10ms | +33% |

| **Regex поддержка** | ❌ | ✅ | Решено |
| **VRAM** | 6 ГБ | 6 ГБ | = |
| **Context window** | 20K | 20K | = |

---

## 🧪 Тестирование

```bash
# Unit-тесты парсеров
pytest tests/test_flag_parser.py -v

# Integration тест
python test_v3_integration.py
```

**Покрытие:** 100% (15/15 тестов passed)

📄 [Отчет о тестировании v3.0.0](doc/versions/v3.0.0/TESTING_REPORT_v3.0.0.md)

---

## 📊 Версионирование

Проект использует [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH-stage**
- **Stage:** `alpha` → `beta` → `rc` → `stable`

### Текущий этап: Alpha (v0.0.1)
- ✅ Основной функционал работает
- ⚠️ Возможны breaking changes
- 🔬 Экспериментальные фичи

### Планы:
- **Beta (v0.x.0):** Стабилизация, Web UI, новые инструменты
- **RC (v1.0.0-rc.x):** Подготовка к релизу, финальное тестирование
- **Stable (v1.0.0+):** Production-ready, обратная совместимость

📄 См. [ROADMAP.md](ROADMAP.md) для детальных планов развития.

---

## 🤝 Вклад в проект

Приветствуются:
- 🐛 **Баг-репорты** - нашли проблему? Создайте issue
- ✨ **Идеи новых функций** - предложите улучшения
- 📝 **Улучшение документации** - опечатки, неясности, примеры
- 🔧 **Pull requests** - новые инструменты, фиксы, тесты

**Как начать:**
1. Fork репозитория
2. Создайте ветку для вашей фичи (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

---

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE)

---

## 🙏 Благодарности

- **Google** - Gemma модели
- **llama-cpp-python** - отличная производительность и стабильность
- **FAISS** (Facebook) - быстрый векторный поиск
- **SentenceTransformers** - эффективные эмбеддинги
- **HuggingFace** - экосистема и инструменты

---

<div align="center">

**Создано с ❤️ для автономного AI**

[Документация](doc/DOCUMENTATION.md) • [Changelog](CHANGELOG.md) • [Roadmap](ROADMAP.md)

**v0.0.1-alpha** | 2025-10-13

</div>
