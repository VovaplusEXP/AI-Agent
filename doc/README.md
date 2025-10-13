# 📚 Документация AI Agent# AI Agent - Документация



Коллекция технической и пользовательской документации проекта.**Версия:** 3.0.0  

**Дата:** 10.10.2025

---

Автономный программный агент на основе локальной LLM (Gemma-3n-E4B) с паттерном ReAct для выполнения задач программирования.

## 📖 Основная документация

## 🚀 Что нового в v3.0.0

### [DOCUMENTATION.md](DOCUMENTATION.md)

Детальная документация проекта:**Революционное обновление:** флаговый формат вместо JSON!

- Архитектура системы

- Описание инструментов- ✅ **100% успешность парсинга** (было ~90%)

- Примеры использования- ✅ **Regex без ошибок** - любые escape-последовательности работают

- FAQ- ✅ **Производительность +30%** - нет двухшаговой очистки

- ✅ **Обратная совместимость** - автоматический fallback на JSON

### [MASTER_DOCUMENTATION.md](MASTER_DOCUMENTATION.md)

Полная техническая документация (историческая):📄 **[Подробности релиза v3.0.0](versions/v3.0.0/README.md)**

- Развёрнутое описание всех компонентов

- Диаграммы и схемы## 📚 Документация

- Детали реализации

**[→ Полная документация](MASTER_DOCUMENTATION.md)** — подробное руководство со всеми деталями

---

**Быстрые ссылки:**

## 🔧 Технические документы- [Архитектура](MASTER_DOCUMENTATION.md#архитектура)

- [Инструменты](MASTER_DOCUMENTATION.md#инструменты)

### [PATCH_v3.3.1_SUMMARY.md](PATCH_v3.3.1_SUMMARY.md)- [Система памяти](MASTER_DOCUMENTATION.md#система-памяти)

Описание последнего патча перед Alpha релизом:- [API Reference](MASTER_DOCUMENTATION.md#api-reference)

- Исправление бесконечных циклов web_fetch- [Troubleshooting](MASTER_DOCUMENTATION.md#troubleshooting)

- Апгрейд контекста до 24k токенов- [История изменений](MASTER_DOCUMENTATION.md#история-изменений)

- Валидация дубликатов инструментов

- Улучшенный системный промпт---



### [PATCH_v3.3.1_TEST_RESULTS.md](PATCH_v3.3.1_TEST_RESULTS.md)## Быстрый старт

Результаты тестирования v3.3.1:

- Метрики производительности### Установка

- Анализ циклов и сжатия

- Обоснование апгрейда до 24k```bash

- Выявленные проблемы и решения# 1. Создание окружения

python3.11 -m venv venv

---source venv/bin/activate



## 🗂️ Навигация# 2. Установка зависимостей

pip install -r requirements.txt

### Для пользователей

1. Начните с [README.md](../README.md) в корне проекта# 3. Настройка (опционально)

2. Прочитайте [DOCUMENTATION.md](DOCUMENTATION.md) для деталейcp .env.example .env

3. Изучите [CHANGELOG.md](../CHANGELOG.md) для истории изменений# Добавить GOOGLE_API_KEY и GOOGLE_CSE_ID для интернет-поиска

4. Посмотрите [ROADMAP.md](../ROADMAP.md) для планов развития

# 4. Поместить GGUF модель в ai/

### Для разработчиков# Скачать: https://huggingface.co/...

1. Изучите [MASTER_DOCUMENTATION.md](MASTER_DOCUMENTATION.md) для архитектуры```

2. Прочитайте технические патчи для понимания эволюции

3. Смотрите тесты в `../tests/` для примеров кода### Запуск



---```bash

source venv/bin/activate

## 📝 Структура проектаpython cli.py

```

```

AI/## Основные возможности

├── README.md                  # Главный README

├── CHANGELOG.md               # История изменений### 🤖 ReAct Агент

├── ROADMAP.md                 # Планы развития- Автономное планирование и выполнение задач

├── doc/                       # Вся документация (эта папка)- Цикл: Thought → Action → Observation

│   ├── README.md              # Этот файл- План-и-выполнение с самокоррекцией через **Self-Reflection** (v2.1.0+)

│   ├── DOCUMENTATION.md       # Основная документация- Контекстное окно: **20,480 токенов** (v2.1.0+)

│   ├── MASTER_DOCUMENTATION.md # Полная техническая

│   ├── PATCH_*.md             # Технические патчи### 🧠 Многоуровневая память

│   └── *_TEST_RESULTS.md      # Результаты тестов- **L1 (Рабочая):** scratchpad с планом и целью

├── agent.py                   # Главный файл агента- **L2 (Эпизодическая):** история диалога (адаптивно 30-70%)

├── compression.py             # Интеллектуальное сжатие- **L3 (Долгосрочная):** векторная память FAISS + SentenceTransformer (адаптивно 10-30%)

├── context_manager.py         # Управление контекстом- **Двухуровневая архитектура:** глобальная + проектная память

├── memory.py                  # Векторная память

├── tools.py                   # 19 инструментов### ⚡ Адаптивное управление контекстом (v2.2.0)

├── parsers.py                 # Флаговый парсер- Гибкие приоритеты вместо жёстких лимитов

└── tests/                     # Тесты- Утилизация контекста: **85-95%** (было ~75%)

```- Динамическое перераспределение токенов

- Подробная статистика использования

---

### 💬 Система чатов

**Версия документации:** 0.0.1-alpha  - Множественные независимые чаты

**Обновлено:** 2025-10-13- Сохранение на диск (история + scratchpad + память)

- Быстрое переключение между чатами
- Проектные контексты с изолированной памятью

### 🖥️ Интерактивный TUI
- Режим чата: взаимодействие с агентом
- Режим shell (Ctrl+O): выполнение команд оболочки
- Rich UI с панелями и markdown
- История команд

### 🛠️ Инструменты

**Файловая система:**
- `list_directory` — список файлов
- `read_file` — чтение файла
- `write_file` — создание/перезапись
- `replace_in_file` — точечная замена
- `analyze_code` — статический анализ Python (v2.1.0+)
- `edit_file_at_line` — точечное редактирование по номерам строк (v2.1.0+)

**Выполнение команд:**
- `run_shell_command` — shell команды с timeout

**Интернет:**
- `internet_search` — Google поиск
- `web_fetch` — парсинг веб-страниц

**Память:**
- `remember` — сохранить информацию с важностью
- `recall` — поиск в памяти
- `finish` — завершение задачи

## Что нового

### 🔮 v3.0.0 - Система флагов (в разработке)
- **Предложение:** Миграция на формат с флагами для решения JSON проблем
- Разделение метаданных (JSON) и сырого контента
- Полное избавление от escape-последовательностей
- → [Подробный план](PROPOSAL_FLAG_BASED_FORMAT.md)

### v2.2.0 - Адаптивный Context Manager ✨
- **Гибкое распределение токенов** с приоритетами
- Утилизация 85-95% вместо 75%
- Динамический k для памяти (k=2→5 global, k=3→7 project)
- Подробная статистика и отладка

### v2.1.2 - Критические исправления 🔥
- **JSON парсинг исправлен:** двухшаговая очистка escape-последовательностей
- **Пути исправлены:** директории создаются в `/home/vova/AI`, а не в CWD
- **Быстрая загрузка:** модель эмбеддингов из локального кэша (<1 сек)

### v2.1.0 - Новые инструменты 🚀
- `analyze_code()` — AST анализ Python с номерами строк
- `edit_file_at_line()` — точечное редактирование
- Self-Reflection при ошибках инструментов
- Flash Attention + KV-кэш FP16
- Контекст увеличен до 20k токенов

→ [Полный CHANGELOG](MASTER_DOCUMENTATION.md#история-изменений)

## Команды CLI

### Управление чатами
```
/new <имя> [описание]   - Создать новый чат
/switch <имя>           - Переключиться на чат
/list                   - Активные чаты в памяти
```

### Сохранение/загрузка
```
/save [описание]        - Сохранить на диск
/load <имя>             - Загрузить с диска
/saved                  - Список сохраненных
/delete <имя>           - Удалить чат
```

### Прочее
```
/memory                 - Статистика памяти
/help                   - Справка
Ctrl+O                  - Переключить режим чат/shell
exit, quit              - Выход
```

## Примеры использования

### Пример 1: Создание скрипта

```
Вы: Создай Python скрипт calculator.py с функциями add, subtract, multiply, divide

Агент:
💭 Мысль: Нужно создать файл calculator.py с четырьмя математическими функциями
🔧 Действие: create_file(file_path="calculator.py", content="...")
✅ Observation: Файл успешно создан

💭 Мысль: Теперь нужно добавить тесты
🔧 Действие: create_file(file_path="test_calculator.py", content="...")
✅ Observation: Файл успешно создан

💭 Мысль: Задача выполнена
🏁 Действие: finish(final_answer="Создан calculator.py с функциями и test_calculator.py")
```

### Пример 2: Работа с памятью

```
Вы: Запомни, что в этом проекте мы используем FastAPI и PostgreSQL

Агент:
💭 Мысль: Нужно сохранить эту информацию в проектную память
🔧 Действие: add_memory(text="Проект использует FastAPI и PostgreSQL")
✅ Observation: Запись добавлена в память

[В следующем запросе агент автоматически найдет эту информацию]

Вы: Создай файл requirements.txt

Агент:
💭 Мысль: Из памяти знаю, что проект использует FastAPI и PostgreSQL
🔧 Действие: create_file(file_path="requirements.txt", content="fastapi>=0.100.0\npsycopg2-binary>=2.9.0\n...")
```

### Пример 3: Shell-режим

```
[chat] Вы: Ctrl+O
[Оболочка] /home/vova/AI $ ls
agent.py  cli.py  tools.py  memory.py  ...

[Оболочка] /home/vova/AI $ git status
On branch main...

[Оболочка] /home/vova/AI $ exit
[chat] Вы: Создай .gitignore для Python проекта
```

## Архитектура

```
Agent (agent.py)
├── LLM (llama-cpp-python + Gemma-3n GGUF)
├── MemoryManager (memory.py)
│   ├── GlobalMemory (векторная БД, общая для всех чатов)
│   └── ProjectMemories (векторная БД для каждого чата)
├── ChatManager (chat_manager.py)
│   └── Персистентность (metadata + history + scratchpad + memory)
├── ContextManager (context_manager.py)
│   └── Оптимизация промпта (L1/L2/L3 приоритизация)
└── Tools (tools.py)
    └── Набор инструментов для агента
```

## Структура проекта

```
/home/vova/AI/
├── agent.py              # Ядро агента (ReAct)
├── cli.py                # TUI интерфейс
├── tools.py              # Инструменты
├── memory.py             # Векторная память
├── context_manager.py    # Управление контекстом
├── chat_manager.py       # Управление чатами
├── requirements.txt      # Зависимости
├── .env                  # Переменные окружения
├── logs/                 # Логи
├── memory/
│   └── global/          # Глобальная память
├── chats/               # Сохраненные чаты
│   └── <name>/
│       ├── metadata.json
│       ├── history.json
│       ├── scratchpad.json
│       └── memory/      # Проектная память
└── tests/
    └── test_tools.py
```

## Технологии

- **LLM:** llama-cpp-python + Gemma-3n (GGUF)
- **Vector DB:** FAISS IndexFlatL2
- **Embeddings:** SentenceTransformer (all-MiniLM-L6-v2)
- **UI:** Rich + prompt_toolkit
- **Web:** requests + BeautifulSoup4
- **Testing:** pytest

## Конфигурация

### Параметры модели (agent.py)
```python
Llama(
    model_path="ai/gemma-3n-E4B-it-IQ4_XS.gguf",
    n_ctx=16384,        # Размер контекста
    n_threads=8,        # CPU потоки
    n_gpu_layers=-1,    # -1 = все на GPU
    chat_format="gemma",
    temperature=0.5
)
```

### Бюджет токенов (context_manager.py)
```python
{
    'system_prompt': 0.15,  # 15%
    'l1_scratchpad': 0.10,  # 10%
    'l3_memory': 0.20,      # 20%
    'l2_history': 0.50,     # 50%
    'reserve': 0.05         # 5%
}
```

## GPU ускорение

### NVIDIA CUDA
```bash
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### AMD ROCm
```bash
CMAKE_ARGS="-DLLAMA_HIPBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### Apple Metal (M1/M2/M3)
```bash
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

## Тестирование

```bash
# Запуск всех тестов
pytest tests/

# С подробностями
pytest tests/ -v

# Конкретный тест
pytest tests/test_tools.py::test_list_directory -v
```

## Логирование

Логи сохраняются в `logs/agent_YYYY-MM-DD_HH-MM-SS.log`

```bash
# Просмотр последнего лога
tail -f logs/agent_*.log | tail -n 1

# Поиск ошибок
grep ERROR logs/agent_*.log
```

## Известные проблемы

### ✅ Исправлено в v2.0.1
1. FAISS save error — директория не создавалась
2. Повторная загрузка SentenceTransformer
3. JSON parsing errors (невалидные escape)
4. Crash on exit при сохранении
5. Relative paths bug (cd в shell меняло пути)

### Текущие ограничения
- Контекст 16K токенов → большие проекты требуют фильтрации
- CPU inference медленный (рекомендуется GPU)
- Shell команды с интерактивным вводом зависнут (timeout 30s)

## Troubleshooting

### Медленная работа
1. Включить GPU (см. секцию GPU ускорение)
2. Уменьшить `max_tokens` в `create_chat_completion`
3. Использовать более легкую квантизацию

### JSON парсинг ошибки
1. Проверить temperature (0.3-0.7 оптимально)
2. Улучшить системный промпт
3. Проверить логи: `tail -f logs/agent_*.log`

### Модель не загружается
1. Проверить путь к GGUF файлу
2. Проверить совместимость версии llama-cpp-python
3. Уменьшить `n_gpu_layers` (0 для CPU)

## Документация

- **[TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)** — полная техническая документация
- **[BUGFIXES_v2.0.1.md](BUGFIXES_v2.0.1.md)** — описание исправленных багов
- **[IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md)** — план развития проекта
- **[CLEANUP_PATHS.md](CLEANUP_PATHS.md)** — очистка неправильных путей

## Производительность

### С GPU (RTX 3060 12GB)
- Prompt eval: ~200 tokens/sec
- Generation: ~40-60 tokens/sec
- Типичный ответ (150 tokens): ~3-5 сек

### CPU only (Intel i7-11700K)
- Prompt eval: ~20 tokens/sec
- Generation: ~5-8 tokens/sec
- Типичный ответ: ~20-30 сек

## Лицензия

[Указать лицензию]

## Авторы

[Указать авторов]

## Благодарности

- **llama.cpp** — GGUF inference
- **FAISS** — векторный поиск
- **SentenceTransformers** — эмбеддинги
- **Google Gemma** — базовая модель
