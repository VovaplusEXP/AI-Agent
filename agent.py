import json
import inspect
import logging
import re
from pathlib import Path
from datetime import datetime
from llama_cpp import Llama
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Локальные импорты
import tools
from context_manager import ContextManager
from memory import MemoryManager
from chat_manager import ChatManager
from parsers import parse_response_with_fallback  # v3.0.0: новый парсер с fallback
from compression import compress_history_smart  # v3.3.0: интеллектуальное сжатие контекста

# Версия проекта
__version__ = "0.0.3-p3-alpha"

# Глобальный logger (будет настроен в __init__ с правильными путями)
logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, model_path, chats_dir="chats", **kwargs):
        # Сохраняем абсолютный путь к рабочей директории проекта
        # ИСПРАВЛЕНО: используем __file__ вместо cwd() для правильного определения корня
        self.project_root = Path(__file__).parent.resolve()
        
        # Настройка логирования С ПРАВИЛЬНЫМИ ПУТЯМИ
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_filename = logs_dir / f"agent_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        
        # Настраиваем handler для файла (если ещё не настроен)
        if not logger.handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                filename=log_filename,
                filemode='w'
            )
        
        # v3.3.1: Отключаем DEBUG логи от markdown_it (засоряют логи)
        logging.getLogger("markdown_it").setLevel(logging.WARNING)
        
        logger.info("Инициализация агента...")
        logger.info(f"Корневая директория проекта: {self.project_root}")
        
        # Инициализация системы памяти (глобальная + проектные)
        # Используем абсолютные пути
        global_memory_path = self.project_root / "memory" / "global"
        chats_abs_path = self.project_root / chats_dir
        
        self.memory_manager = MemoryManager(
            global_memory_dir=str(global_memory_path),
            chats_base_dir=str(chats_abs_path)
        )
        
        logger.info("Загрузка GGUF модели...")
        
        # Параметры LLM с возможностью переопределения через .env
        import os
        # v3.3.1: Увеличено с 20480 до 24576 (RTX 4060 8GB: 61% VRAM → ~72%, безопасно)
        self.n_ctx = int(os.getenv("LLM_N_CTX", "24576"))
        n_threads = int(os.getenv("LLM_N_THREADS", "8"))
        n_gpu_layers = int(os.getenv("LLM_N_GPU_LAYERS", "-1"))
        flash_attn = os.getenv("LLM_FLASH_ATTN", "true").lower() == "true"
        verbose = os.getenv("LLM_VERBOSE", "false").lower() == "true"
        
        logger.info(f"Параметры LLM: n_ctx={self.n_ctx}, n_threads={n_threads}, n_gpu_layers={n_gpu_layers}, flash_attn={flash_attn}, offload_kqv=True")
        
        # ИСПРАВЛЕНО: Добавлен параметр offload_kqv=True для размещения KV-кэша в VRAM
        # offload_kqv=True обеспечивает выполнение операций KV-кэша на GPU, а не на CPU
        # type_k=1, type_v=1 определяют формат данных (FP16), а не расположение памяти
        self.llm = Llama(
            model_path=model_path, 
            n_ctx=self.n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers, 
            flash_attn=flash_attn,
            offload_kqv=True,   # Выгрузка KV-кэша на GPU (критично для VRAM!)
            type_k=1,           # FP16 для ключей KV-кэша
            type_v=1,           # FP16 для значений KV-кэша
            verbose=verbose, 
            chat_format="gemma", 
            **kwargs
        )
        
        # Инициализация менеджеров с абсолютными путями
        chats_abs_path = self.project_root / chats_dir
        self.chat_manager = ChatManager(chats_dir=str(chats_abs_path))
        self.context_manager = ContextManager(
            self.llm,
            global_memory=self.memory_manager.global_memory,
            project_memory=None  # Будет установлена при переключении чата
        )
        
        logger.info("Модель успешно загружена!")

        self.chats_dir = chats_abs_path
        self.chats_dir.mkdir(exist_ok=True)
        self.current_chat = "default"
        
        self.scratchpads = {"default": self._create_new_scratchpad()}
        self.histories = {"default": []}

        self._load_tools()
        self.system_prompt = self._get_system_prompt()

    def _create_new_scratchpad(self):
        return {"main_goal": "", "plan": None, "last_action_result": None}

    def _load_tools(self):
        self.tools = {}
        # Инструменты, результаты которых нужно запоминать в векторной памяти
        self.tools_to_remember = [
            'read_file', 'list_directory', 'run_shell_command', 
            'web_fetch', 'replace_in_file', 'create_file', 
            'analyze_code', 'edit_file_at_line',  # Новые инструменты
            'internet_search', 'web_search_in_page'  # v3.2.5: Запоминаем результаты веб-поиска
        ]
        
        for name, func in inspect.getmembers(tools, inspect.isfunction):
            # Инструменты для памяти обрабатываются отдельно
            if func.__module__ == tools.__name__ and name not in ['finish', 'list_memories', 'delete_memory', 'add_memory']:
                self.tools[name] = func
        
        self.tool_descriptions = "\n".join([
            f"- {name}{inspect.signature(func)}: {inspect.getdoc(func)}" 
            for name, func in inspect.getmembers(tools, inspect.isfunction) 
            if func.__module__ == tools.__name__
        ])
        logger.info(f"Загружены инструменты: {', '.join(list(self.tools.keys()) + ['list_memories', 'delete_memory', 'add_memory'])}")

    def _get_system_prompt(self):
        tool_list = self.tool_descriptions
        current_date = datetime.now().strftime('%d.%m.%Y')
        return f"""Дата: {current_date}

Ты — ReAct-агент (Thought → Action → Observation цикл).

ФОРМАТ ОТВЕТА — СТРОГО ОБЯЗАТЕЛЬНЫЙ:
<THOUGHT>твои рассуждения<TOOL>имя_инструмента<PARAMS>{{"param": "value"}}<END>

ПРАВИЛА:
1. КАЖДЫЙ ответ только в формате: <THOUGHT>...<TOOL>...<PARAMS>...<END>
2. <PARAMS> — валидный JSON с параметрами
3. Для завершения: <TOOL>finish<PARAMS>{{"final_answer": "ответ"}}<END>
4. НЕ пиши текстовые ответы вне формата — это ошибка!

⚠️ КРИТИЧНО - ПАТТЕРН РАБОТЫ С ПОИСКОМ:
1. internet_search → получаешь список URL
2. web_fetch → скачиваешь HTML страницы (ОГРОМНЫЙ текст!)
3. web_search_in_page → ОБЯЗАТЕЛЬНО извлекаешь нужную информацию из HTML
4. create_file → сохраняешь найденную информацию
5. finish → завершаешь задачу

❌ ЗАПРЕЩЕНО: 
   - Повторять web_fetch на том же URL (уже скачан!)
   - Думать что web_fetch = анализ (это просто HTML!)
   - Пропускать web_search_in_page после web_fetch

✅ ПРАВИЛЬНО: 
   internet_search → web_fetch(url) → web_search_in_page(url, query) → create_file → finish

ПРИМЕР ФОРМАТА:

<THOUGHT>твои рассуждения о следующем шаге<TOOL>имя_инструмента<PARAMS>{{"param": "value"}}<END>

ДОСТУПНЫЕ ИНСТРУМЕНТЫ:
{tool_list}

⚠️ КРИТИЧНО: Любой ответ без флагов <THOUGHT><TOOL><PARAMS><END> будет отклонён!"""

    def run_cycle(self, user_input: str):
        logger.info(f"Запуск цикла ReAct для задачи: '{user_input}'")
        
        history = self.histories[self.current_chat]
        scratchpad = self.scratchpads[self.current_chat]

        # ВАЖНО: Gemma НЕ ПОДДЕРЖИВАЕТ role='system'!
        # Системный промпт будет добавляться в первое user сообщение
        # if not history:
        #     history.append({"role": "system", "content": self.system_prompt})

        try:
            scratchpad["main_goal"] = user_input
            scratchpad["plan"] = None

            max_cycles = 50  # v3.3.1: Увеличено с 10 до 50 (защита от дубликатов предотвращает зацикливание)
            for cycle in range(max_cycles):
                logger.debug(f"--- Начало цикла {cycle+1}/{max_cycles} ---")

                if cycle == 0:
                    logger.info("Генерирую план...")
                    # ВАЖНО: Для Gemma системный промпт включается в user сообщение
                    plan_system_prompt = """Ты - ассистент по планированию. Твоя задача - создать краткий пошаговый план.
Отвечай ТОЛЬКО нумерованным списком шагов. Без дополнительных комментариев."""
                    plan_prompt = f"{plan_system_prompt}\n\nСоздай краткий пошаговый план для решения задачи: '{scratchpad['main_goal']}'"
                    plan_messages = [
                        {"role": "user", "content": plan_prompt}  # Системный промпт в user сообщении!
                    ]
                    output = self.llm.create_chat_completion(
                        messages=plan_messages, 
                        max_tokens=1024,  # v3.1.0: Увеличено для более детальных планов
                        temperature=0.5
                    )
                    plan = output['choices'][0]['message']['content'].strip()
                    scratchpad['plan'] = plan
                    logger.info(f"Сгенерирован план:\n{plan}")

                # Получаем проектную память для текущего чата
                project_memory = self.memory_manager.get_project_memory(self.current_chat)
                
                # Обновляем context_manager с текущей проектной памятью
                self.context_manager.project_memory = project_memory
                
                # Используем ContextManager для сборки контекста
                optimized_history, context_info, enhanced_prompt = self.context_manager.build_context(
                    system_prompt=self.system_prompt,
                    scratchpad=scratchpad,
                    history=history,
                    current_query=user_input
                )
                
                logger.info(f"Контекст оптимизирован: {context_info}")
                
                # v3.1.0: Добавляем напоминание о формате после 3 циклов
                format_reminder = ""
                if cycle >= 3:
                    format_reminder = "\n\n⚠️ НАПОМИНАНИЕ: Ответ СТРОГО <THOUGHT><TOOL><PARAMS><END>!"
                
                # КРИТИЧНО: Добавляем улучшенный системный промпт в первое user сообщение для Gemma
                full_user_prompt = f"""{enhanced_prompt}{format_reminder}

---

ЗАДАЧА: {user_input}"""
                history.append({"role": "user", "content": full_user_prompt})

                # Вычисляем динамический max_tokens с учётом использованного контекста
                used_tokens = context_info.get("total_tokens", 0)
                # Оставляем буфер 3072 токенов для chat format overhead и безопасности
                # При >80% использования chat format может добавить 2000-5000 токенов!
                buffer_tokens = 3072
                available_for_generation = self.n_ctx - used_tokens - buffer_tokens
                
                # v3.3.0: Интеллектуальное сжатие при >80% использования
                utilization = (used_tokens / self.n_ctx) * 100
                if utilization > 80:
                    logger.warning(f"⚠️ Контекст переполнен на {utilization:.1f}%! Интеллектуальное сжатие...")
                    
                    # НОВОЕ: Интеллектуальное сжатие вместо тупой обрезки
                    history = compress_history_smart(
                        history=history,
                        scratchpad=scratchpad,
                        llm=self.llm,
                        memory_manager=self.memory_manager,
                        current_chat=self.current_chat
                    )
                    
                    # Пересчитываем токены после сжатия
                    compressed_tokens = sum(self.count_tokens(msg.get('content', '')) for msg in history)
                    available_for_generation = max(512, self.n_ctx - compressed_tokens - buffer_tokens)
                    
                    reduction = ((used_tokens - compressed_tokens) / used_tokens * 100) if used_tokens > 0 else 0
                    logger.info(f"✅ Сжатие завершено: {used_tokens} → {compressed_tokens} токенов ({reduction:.1f}% экономии)")
                    logger.info(f"💡 Доступно для генерации: {available_for_generation} токенов")
                    
                elif available_for_generation < 512:
                    # Критическая ситуация - обрезаем до 50%
                    logger.error(f"❌ КРИТИЧЕСКОЕ переполнение! Использовано {used_tokens}/{self.n_ctx}")
                    history_len = len(history)
                    keep_messages = max(2, history_len // 2)
                    history = history[:1] + history[-keep_messages+1:]
                    logger.error(f"❌ Экстренная обрезка истории с {history_len} до {len(history)} сообщений")
                    available_for_generation = 512
                
                # Ограничиваем сверху 4096, снизу 256
                dynamic_max_tokens = max(256, min(4096, available_for_generation))
                logger.debug(f"🔢 Динамический max_tokens: {dynamic_max_tokens} (использовано {used_tokens}/{self.n_ctx} = {utilization:.1f}%, буфер {buffer_tokens}, доступно {available_for_generation})")
                
                output = self.llm.create_chat_completion(messages=history, max_tokens=dynamic_max_tokens, temperature=0.5)
                raw_response = output['choices'][0]['message']['content'].strip()
                logger.debug(f"Сырой ответ от LLM: {raw_response}")

                try:
                    # v3.0.0: Используем новый парсер с поддержкой флагов и fallback на JSON
                    parsed = parse_response_with_fallback(raw_response)
                    
                    # ✅ v3.1.0: ПОСЛЕ успешного парсинга добавляем в историю
                    history.append({"role": "user", "content": raw_response})
                    
                    thought = parsed['thought']
                    tool_name = parsed['tool_name']
                    parameters = parsed['parameters']
                    
                    logger.debug(f"Распарсенная мысль: {thought}")
                    logger.debug(f"Распарсенное действие: tool={tool_name}, params={parameters}")

                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Ошибка парсинга (цикл {cycle+1}): {e}")
                    logger.error(f"Сырой ответ: {raw_response}")
                    
                    # ❌ НЕ добавляем сырой ответ в историю при ошибке парсинга
                    
                    # v3.1.0: Снижен лимит с 5 до 3 циклов для быстрого прерывания
                    if cycle >= 3:
                        error_msg = f"""Observation: ❌ КРИТИЧЕСКАЯ ОШИБКА ФОРМАТА!

После {cycle+1} попыток модель не может генерировать правильный формат.
Прерываю выполнение. Переформулируй запрос или упрости задачу."""
                        history.append({"role": "user", "content": error_msg})
                        logger.error("Достигнут лимит ошибок парсинга")
                        yield {"thought": f"Критическая ошибка парсинга после {cycle+1} попыток", "action": {"tool_name": "finish", "parameters": {"final_answer": "Ошибка: не удалось выполнить задачу из-за проблем с генерацией команд"}}}
                        return
                    
                    # v3.1.0: Убрано упоминание JSON формата - только флаги!
                    error_msg = f"""Observation: ⚠️ ОШИБКА ФОРМАТА! (Цикл {cycle+1}/{max_cycles})

ТРЕБУЕМЫЙ ФОРМАТ:
<THOUGHT>твои рассуждения<TOOL>имя_инструмента<PARAMS>{{"param": "value"}}<END>

ПРИМЕР:
<THOUGHT>Нужно прочитать файл test.py<TOOL>read_file<PARAMS>{{"file_path": "test.py"}}<END>

Твой ответ НЕ соответствует формату. Исправь НЕМЕДЛЕННО!"""
                    history.append({"role": "user", "content": error_msg})
                    yield {"thought": f"Ошибка парсинга: {str(e)[:100]}. Попробую снова с правильным форматом.", "action": {}}
                    continue

                should_execute = yield {
                    "thought": thought, 
                    "action": {
                        "tool_name": tool_name,
                        "parameters": parameters
                    }
                }

                if not should_execute:
                    logger.warning(f"Выполнение действия '{tool_name}' отменено пользователем.")
                    history.append({"role": "user", "content": f"Observation: Действие '{tool_name}' было отменено пользователем. Результата нет."})
                    continue

                # --- ОБРАБОТКА ИНСТРУМЕНТОВ ---
                result = ""
                if tool_name in self.tools:
                    # v3.3.0: Проверка на дублирование web_fetch
                    if tool_name == "web_fetch" and parameters.get("url"):
                        url_to_fetch = parameters["url"]
                        
                        # Проверяем историю на повторный вызов
                        fetch_count = sum(1 for msg in history 
                                        if msg.get("role") == "assistant" 
                                        and f'"url": "{url_to_fetch}"' in msg.get("content", ""))
                        
                        if fetch_count >= 1:
                            logger.warning(f"⚠️ Попытка повторного web_fetch на {url_to_fetch} (уже вызван {fetch_count} раз)")
                            result = f"""❌ ОШИБКА: URL '{url_to_fetch}' уже был загружен ранее!

ОБЯЗАТЕЛЬНО используй web_search_in_page для поиска информации в уже загруженной странице:
<TOOL>web_search_in_page<PARAMS>{{"url": "{url_to_fetch}", "query": "твой поисковый запрос"}}<END>

❌ НЕ повторяй web_fetch на том же URL!
✅ Используй web_search_in_page для извлечения данных из HTML."""
                            history.append({"role": "assistant", "content": raw_response})
                            history.append({"role": "user", "content": f"Observation: {result}"})
                            cycle += 1
                            continue
                    
                    # v3.3.0: Проверка на дублирование internet_search
                    if tool_name == "internet_search" and parameters.get("query"):
                        search_query = parameters["query"].lower().strip()
                        
                        # Проверяем историю на похожий запрос
                        search_count = sum(1 for msg in history 
                                         if msg.get("role") == "assistant" 
                                         and "internet_search" in msg.get("content", "")
                                         and search_query in msg.get("content", "").lower())
                        
                        if search_count >= 1:
                            logger.warning(f"⚠️ Попытка повторного internet_search с запросом '{search_query}' (уже вызван {search_count} раз)")
                            result = f"""❌ ОШИБКА: Поисковый запрос '{parameters["query"]}' уже был выполнен ранее!

Ты УЖЕ получил список URL из internet_search. Используй их:
1. web_fetch(url) → загрузи страницу
2. web_search_in_page(url, query) → найди нужную информацию
3. create_file → сохрани результат

❌ НЕ повторяй internet_search с тем же запросом!
✅ Используй уже найденные URL для анализа."""
                            history.append({"role": "assistant", "content": raw_response})
                            history.append({"role": "user", "content": f"Observation: {result}"})
                            cycle += 1
                            continue
                    
                    logger.info(f"Выполнение инструмента: {tool_name} с параметрами {parameters}")
                    logger.debug(f"Тип parameters: {type(parameters)}, содержимое: {repr(parameters)}")
                    try:
                        result = self.tools[tool_name](**parameters)
                        if tool_name in self.tools_to_remember and "Ошибка" not in result:
                            # v3.3.0: Сохраняем в память с умным извлечением фактов
                            from compression import _extract_key_facts
                            
                            project_memory = self.memory_manager.get_project_memory(self.current_chat)
                            
                            # Извлекаем ключевые факты вместо тупой обрезки
                            facts = _extract_key_facts(result)
                            
                            # Сохраняем только если есть полезная информация
                            if facts and len(facts) > 20:
                                memory_entry = f"[{tool_name}] {facts}"
                                project_memory.add(memory_entry, metadata={'tool': tool_name, 'chat': self.current_chat})
                                logger.debug(f"💾 Сохранён факт в память: {facts[:80]}...")
                            
                            # Если это важное общее знание, добавляем и в глобальную память
                            if tool_name in ['read_file', 'web_fetch'] and facts:
                                global_entry = f"[{tool_name}] {facts[:200]}"
                                self.memory_manager.global_memory.add(global_entry, metadata={'tool': tool_name})
                                
                    except TypeError as type_error:
                        # v3.1.0: Специальная обработка ошибок типов параметров
                        logger.error(f"TypeError в '{tool_name}': {type_error}", exc_info=True)
                        logger.error(f"Переданные параметры (тип: {type(parameters)}): {repr(parameters)}")
                        
                        # Получаем сигнатуру функции для подсказки
                        import inspect
                        sig = inspect.signature(self.tools[tool_name])
                        params_info = []
                        for name, param in sig.parameters.items():
                            if param.default == inspect.Parameter.empty:
                                params_info.append(f"  - {name} (обязательный)")
                            else:
                                params_info.append(f"  - {name} (опционально, по умолчанию: {param.default})")
                        
                        result = f"""❌ Ошибка типов параметров для инструмента '{tool_name}':
{type_error}

Ожидаемые параметры:
{chr(10).join(params_info)}

Переданные параметры: {parameters}

Проверь:
- Наличие всех обязательных параметров
- Правильность названий параметров (возможно опечатка)
- Типы данных (строка, число, список)

Попробуй исправить и повтори вызов."""
                        
                    except Exception as e:
                        logger.error(f"Ошибка при выполнении '{tool_name}': {e}", exc_info=True)
                        error_msg = str(e)
                        
                        # --- SELF-REFLECTION: анализ ошибки и попытка исправления ---
                        if cycle < max_cycles - 1:  # Оставляем запас циклов для исправления
                            logger.info("Запуск self-reflection для анализа ошибки...")
                            reflection_prompt = f"""Инструмент '{tool_name}' завершился с ошибкой: {error_msg}

Параметры вызова: {parameters}

Проанализируй и предложи решение в ФЛАГОВОМ ФОРМАТЕ:

<THOUGHT>
Кратко: в чём причина ошибки?
<CAN_RETRY>
yes или no (можно ли исправить параметры?)
<SOLUTION>
Если yes: конкретные исправленные параметры
Если no: альтернативный подход
<END>

ПРИМЕРЫ:

Пример 1 (можно исправить):
<THOUGHT>
Файл не найден, вероятно путь неверный или относительный
<CAN_RETRY>
yes
<SOLUTION>
Попробуй с абсолютным путём: file_path="/home/user/file.py"
Или сначала используй list_directory(".") чтобы увидеть доступные файлы
<END>

Пример 2 (нельзя исправить):
<THOUGHT>
Файл удалён пользователем и недоступен
<CAN_RETRY>
no
<SOLUTION>
Используй internet_search для поиска информации по теме
Или спроси пользователя предоставить файл заново
<END>"""

                            reflection_messages = [{"role": "user", "content": reflection_prompt}]
                            try:
                                reflection_output = self.llm.create_chat_completion(
                                    messages=reflection_messages, 
                                    max_tokens=768,  # v3.1.0: Увеличено с 512 для детального анализа
                                    temperature=0.3
                                )
                                reflection_text = reflection_output['choices'][0]['message']['content'].strip()
                                logger.debug(f"Self-reflection: {reflection_text}")
                                
                                # v3.1.0: Парсим флаговый формат
                                thought_match = re.search(
                                    r'<THOUGHT>\s*(.+?)\s*<CAN_RETRY>', 
                                    reflection_text, 
                                    re.DOTALL | re.IGNORECASE
                                )
                                can_retry_match = re.search(
                                    r'<CAN_RETRY>\s*(.+?)\s*<SOLUTION>', 
                                    reflection_text, 
                                    re.DOTALL | re.IGNORECASE
                                )
                                solution_match = re.search(
                                    r'<SOLUTION>\s*(.+?)\s*<END>', 
                                    reflection_text, 
                                    re.DOTALL | re.IGNORECASE
                                )
                                
                                if thought_match and can_retry_match and solution_match:
                                    thought = thought_match.group(1).strip()
                                    can_retry = can_retry_match.group(1).strip().lower() in ['yes', 'да', 'true', 'y']
                                    solution = solution_match.group(1).strip()
                                    
                                    # Формируем структурированное сообщение для агента
                                    if can_retry:
                                        result = f"""❌ Ошибка: {error_msg}

🤔 Причина: {thought}

✅ Можно исправить:
{solution}

Попробуй снова с исправленными параметрами."""
                                    else:
                                        result = f"""❌ Ошибка: {error_msg}

🤔 Причина: {thought}

🔄 Альтернативный подход:
{solution}

Выбери другой инструмент или способ решения задачи."""
                                else:
                                    # Fallback если формат нарушен
                                    logger.warning("Self-reflection не в флаговом формате, используем как есть")
                                    result = f"❌ Ошибка: {error_msg}\n\n🤔 Анализ:\n{reflection_text}\n\nПопробуй исправить или выбери другой подход."
                                    
                            except Exception as ref_error:
                                logger.error(f"Ошибка в self-reflection: {ref_error}")
                                result = f"Ошибка: {error_msg}"
                        else:
                            result = f"Ошибка: {error_msg}"
                
                # --- ОБРАБОТКА ИНСТРУМЕНТОВ ПАМЯТИ ---
                elif tool_name == "list_memories":
                    # Показываем обе памяти
                    global_list = self.memory_manager.global_memory.list_entries()
                    project_memory = self.memory_manager.get_project_memory(self.current_chat)
                    project_list = project_memory.list_entries()
                    result = f"📚 ГЛОБАЛЬНАЯ ПАМЯТЬ:\n{global_list}\n\n🔬 ПРОЕКТНАЯ ПАМЯТЬ ({self.current_chat}):\n{project_list}"
                elif tool_name == "delete_memory":
                    # Удаляем из проектной памяти по умолчанию
                    project_memory = self.memory_manager.get_project_memory(self.current_chat)
                    result = project_memory.delete(**parameters)
                elif tool_name == "add_memory":
                    # Добавляем в проектную память по умолчанию
                    project_memory = self.memory_manager.get_project_memory(self.current_chat)
                    project_memory.add(parameters['text'])
                    result = f"Запись успешно добавлена в проектную память '{self.current_chat}'."

                elif tool_name == "finish":
                    logger.info("Агент завершил работу.")
                    # Автосохранение чата при завершении
                    self.chat_manager.auto_save_chat(
                        self.current_chat,
                        history,
                        scratchpad
                    )
                    yield {
                        "thought": thought, 
                        "action": {
                            "tool_name": tool_name,
                            "parameters": parameters
                        }
                    }
                    return
                else:
                    logger.warning(f"Неизвестный инструмент: '{tool_name}'")
                    result = f"Ошибка: неизвестный инструмент '{tool_name}'."

                # Формируем Observation для LLM
                observation_for_llm = f"Observation: Результат выполнения инструмента '{tool_name}':\n{result}"
                history.append({"role": "user", "content": observation_for_llm})
            
            logger.warning("Достигнут лимит циклов.")
            
        except GeneratorExit:
            logger.warning("Генератор прерван пользователем (GeneratorExit)")
            raise
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка в цикле ReAct: {e}", exc_info=True)
            raise
            
        finally:
            # v3.1.0: Cleanup - всегда сохраняем память при выходе
            try:
                project_memory = self.memory_manager.get_project_memory(self.current_chat)
                project_memory.save()
                logger.info(f"✅ Память проекта '{self.current_chat}' сохранена (cleanup)")
            except Exception as save_error:
                logger.error(f"❌ Ошибка сохранения памяти в cleanup: {save_error}")

    def count_tokens(self, text: str) -> int:
        return len(self.llm.tokenize(text.encode('utf-8'))) if text else 0

    def new_chat(self, chat_name: str, description: str = ""):
        """Создает новый чат в памяти."""
        if chat_name not in self.histories:
            self.histories[chat_name] = []
            self.scratchpads[chat_name] = self._create_new_scratchpad()
            self.current_chat = chat_name
            logger.info(f"Создан новый чат: '{chat_name}'")
            return f"Создан и выбран новый чат: '{chat_name}'"
        return f"Ошибка: Чат '{chat_name}' уже существует в памяти."

    def switch_chat(self, chat_name: str):
        """Переключается на существующий чат в памяти или загружает с диска."""
        # Сначала проверяем, есть ли чат в памяти
        if chat_name in self.histories:
            self.current_chat = chat_name
            return f"Переключено на чат: '{chat_name}' (из памяти)"
        
        # Если нет в памяти, пробуем загрузить с диска
        loaded_chat = self.chat_manager.load_chat(chat_name)
        if loaded_chat:
            self.histories[chat_name] = loaded_chat['history']
            self.scratchpads[chat_name] = loaded_chat['scratchpad']
            self.current_chat = chat_name
            logger.info(f"Чат '{chat_name}' загружен с диска")
            return f"Переключено на чат: '{chat_name}' (загружен с диска, {len(loaded_chat['history'])} сообщений)"
        
        return f"Ошибка: Чат '{chat_name}' не найден ни в памяти, ни на диске."

    def save_current_chat(self, description: str = ""):
        """Сохраняет текущий чат на диск."""
        success = self.chat_manager.save_chat(
            self.current_chat,
            self.histories[self.current_chat],
            self.scratchpads[self.current_chat],
            description
        )
        if success:
            # Также сохраняем проектную память
            project_memory = self.memory_manager.get_project_memory(self.current_chat)
            project_memory.save()
            return f"Чат '{self.current_chat}' успешно сохранен на диск."
        return f"Ошибка при сохранении чата '{self.current_chat}'."

    def load_chat(self, chat_name: str):
        """Загружает чат с диска."""
        loaded_chat = self.chat_manager.load_chat(chat_name)
        if loaded_chat:
            self.histories[chat_name] = loaded_chat['history']
            self.scratchpads[chat_name] = loaded_chat['scratchpad']
            self.current_chat = chat_name
            return f"Чат '{chat_name}' загружен с диска ({len(loaded_chat['history'])} сообщений)."
        return f"Ошибка: Чат '{chat_name}' не найден на диске."

    def delete_saved_chat(self, chat_name: str):
        """Удаляет сохраненный чат с диска."""
        success = self.chat_manager.delete_chat(chat_name)
        if success:
            # Удаляем из памяти, если загружен
            if chat_name in self.histories:
                del self.histories[chat_name]
                del self.scratchpads[chat_name]
                if self.current_chat == chat_name:
                    self.current_chat = "default"
            return f"Чат '{chat_name}' удален с диска."
        return f"Ошибка при удалении чата '{chat_name}'."

    def list_chats(self):
        """Показывает список активных чатов в памяти."""
        lines = ["📝 Активные чаты (в памяти):"]
        for name in self.histories.keys():
            prefix = " *" if name == self.current_chat else "  "
            msg_count = len(self.histories[name])
            lines.append(f"{prefix} {name} ({msg_count} сообщений)")
        return "\n".join(lines)
    
    def list_saved_chats(self):
        """Показывает список сохраненных чатов на диске."""
        saved = self.chat_manager.list_saved_chats()
        if not saved:
            return "💾 Сохраненных чатов не найдено."
        
        lines = ["💾 Сохраненные чаты:"]
        for chat in saved:
            name = chat['name']
            msg_count = chat.get('messages_count', 0)
            last_saved = chat.get('last_saved', 'N/A')[:19]  # Обрезаем до даты+времени
            desc = chat.get('description', '')
            desc_str = f" - {desc}" if desc else ""
            lines.append(f"  {name} ({msg_count} сообщений, обновлен: {last_saved}){desc_str}")
        
        return "\n".join(lines)
    
    def get_memory_stats(self):
        """Возвращает статистику всех памятей."""
        stats = self.memory_manager.get_all_stats()
        
        lines = ["📊 Статистика памяти:"]
        lines.append("\n📚 Глобальная память:")
        lines.append(f"  - Записей: {stats['global']['total_entries']}")
        lines.append(f"  - Путь: {stats['global']['storage_path']}")
        
        if stats['projects']:
            lines.append("\n🔬 Проектные памяти:")
            for name, proj_stats in stats['projects'].items():
                lines.append(f"  - {name}: {proj_stats['total_entries']} записей")
        
        return "\n".join(lines)
