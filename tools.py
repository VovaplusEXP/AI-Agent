"""
Набор инструментов, которые может использовать AI-агент.
Каждая функция должна иметь подробный docstring, описывающий ее назначение,
аргументы и возвращаемое значение, так как LLM будет использовать эту информацию
для принятия решений о выборе и использовании инструмента.
"""
import os
import subprocess
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.connection import create_connection
from bs4 import BeautifulSoup
import logging
import socket

logger = logging.getLogger(__name__)

# Сохраняем оригинальную функцию create_connection
_orig_create_connection = create_connection

# WORKAROUND для Kali Linux: обход mDNS задержек
# Если установлена переменная BYPASS_MDNS=true, используем dnspython для резолвинга
_DNS_CACHE = {}
_CUSTOM_RESOLVER = None

def _init_custom_resolver():
    """
    Инициализирует кастомный DNS resolver с использованием dnspython.
    Полностью обходит NSS (Name Service Switch) и mDNS.
    """
    global _CUSTOM_RESOLVER
    if _CUSTOM_RESOLVER is not None:
        return _CUSTOM_RESOLVER
    
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        
        # Используем публичные DNS серверы напрямую (обход /etc/resolv.conf)
        # Google DNS: 8.8.8.8, 8.8.4.4
        # Cloudflare DNS: 1.1.1.1, 1.0.0.1
        resolver.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4']
        resolver.timeout = 2.0
        resolver.lifetime = 5.0
        
        _CUSTOM_RESOLVER = resolver
        logger.debug("Кастомный DNS resolver инициализирован (Google DNS + Cloudflare)")
        return resolver
    except ImportError:
        logger.warning("dnspython не установлен, используем fallback на socket.getaddrinfo")
        return None
    except Exception as e:
        logger.error(f"Ошибка инициализации DNS resolver: {e}")
        return None

def _resolve_dns_fast(hostname: str) -> str:
    """
    Быстрый резолвинг DNS с обходом mDNS (для Kali Linux).
    
    Использует dnspython для прямых DNS запросов, минуя NSS и mDNS.
    Кеширует результаты в памяти для ускорения повторных запросов.
    
    Args:
        hostname: Доменное имя для резолвинга
        
    Returns:
        IP-адрес (IPv4) или исходный hostname при ошибке
    """
    # Проверяем кеш
    if hostname in _DNS_CACHE:
        logger.debug(f"DNS из кеша: {hostname} -> {_DNS_CACHE[hostname]}")
        return _DNS_CACHE[hostname]
    
    bypass_mdns = os.getenv("BYPASS_MDNS", "false").lower() == "true"
    
    if bypass_mdns:
        # Метод 1: dnspython (предпочтительный)
        resolver = _init_custom_resolver()
        if resolver:
            try:
                import dns.resolver
                # Резолвим A-запись (IPv4)
                answers = resolver.resolve(hostname, 'A')
                ip = str(answers[0])
                _DNS_CACHE[hostname] = ip
                logger.debug(f"DNS резолв (dnspython, bypass mDNS): {hostname} -> {ip}")
                return ip
            except Exception as e:
                logger.warning(f"dnspython резолв не удался для {hostname}: {e}")
        
        # Метод 2: socket.getaddrinfo с AF_INET (fallback)
        try:
            import socket
            # AF_INET заставляет использовать только IPv4 DNS
            result = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
            ip = str(result[0][4][0])
            _DNS_CACHE[hostname] = ip
            logger.debug(f"DNS резолв (socket.AF_INET fallback): {hostname} -> {ip}")
            return ip
        except Exception as e:
            logger.warning(f"Не удалось резолвнуть {hostname} ни одним методом: {e}")
    
    return hostname  # Возвращаем hostname как есть


def _patched_create_connection(address, *args, **kwargs):
    """
    Патченная версия urllib3.util.connection.create_connection.
    Использует наш кастомный DNS resolver вместо системного.
    
    Это позволяет requests обходить mDNS, сохраняя при этом:
    - Корректные SSL сертификаты (SNI с hostname)
    - Все заголовки HTTP
    - Cookie и session management
    """
    host, port = address
    
    # Резолвим через наш кастомный resolver
    resolved_host = _resolve_dns_fast(host)
    
    # Создаём соединение с резолвнутым IP, но сохраняем оригинальный hostname
    # для SNI и Host заголовка
    return _orig_create_connection((resolved_host, port), *args, **kwargs)


def _enable_custom_dns():
    """
    Включает кастомный DNS resolver для всех requests в этом процессе.
    Патчит urllib3.util.connection.create_connection.
    """
    if os.getenv("BYPASS_MDNS", "false").lower() == "true":
        try:
            from urllib3.util import connection
            connection.create_connection = _patched_create_connection
            logger.info("✅ Кастомный DNS resolver активирован (обход mDNS)")
        except Exception as e:
            logger.error(f"Не удалось активировать кастомный DNS resolver: {e}")


# Активируем кастомный DNS при импорте модуля (если BYPASS_MDNS=true)
_enable_custom_dns()


def internet_search(query: str, num_results: int = 5) -> str:
    """
    Ищет информацию в интернете с помощью Google. Используй для поиска актуальных данных или сведений, отсутствующих в твоих знаниях.
    ⚠️ ВАЖНО: После получения результатов ОБЯЗАТЕЛЬНО используй web_search_in_page или web_fetch для анализа найденных страниц!

    Args:
        query (str): Поисковый запрос.
        num_results (int): Количество результатов для возврата (по умолчанию 5, максимум 10).

    Returns:
        str: Отформатированная строка с результатами поиска.
    """
    import time
    start_time = time.time()
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        cse_id = os.environ.get("GOOGLE_CSE_ID")

        if not api_key or not cse_id:
            logger.error("GOOGLE_API_KEY или GOOGLE_CSE_ID не установлены в окружении")
            return "Ошибка: Переменные окружения GOOGLE_API_KEY и GOOGLE_CSE_ID не установлены. Поиск невозможен."

        logger.debug(f"Начало поиска Google: query='{query}', num_results={num_results}")
        num = min(num_results, 10)  # Ограничение API Google

        url = "https://www.googleapis.com/customsearch/v1"
        params = {'key': api_key, 'cx': cse_id, 'q': query, 'num': num}
        
        # Если BYPASS_MDNS=true, кастомный DNS уже активирован через патч urllib3
        logger.debug(f"Отправка запроса к Google API: {url}")
        request_start = time.time()
        response = requests.get(url, params=params, timeout=30)
        request_time = time.time() - request_start
        logger.debug(f"Ответ от Google API получен за {request_time:.2f}с, статус: {response.status_code}")
        response.raise_for_status()
        res = response.json()
        items = res.get('items', [])

        if not items:
            return "По вашему запросу ничего не найдено."

        results_formatted = []
        for i, item in enumerate(items, 1):
            snippet = item.get('snippet', 'N/A').replace('\n', ' ').strip()
            results_formatted.append(
                f"{i}. Название: {item.get('title', 'N/A')}\n"
                f"   URL: {item.get('link', 'N/A')}\n"
                f"   Краткое описание: {snippet}"
            )
        
        total_time = time.time() - start_time
        logger.info(f"Поиск завершён успешно за {total_time:.2f}с, найдено результатов: {len(items)}")
        return "\n\n".join(results_formatted)

    except requests.exceptions.RequestException as e:
        total_time = time.time() - start_time
        logger.error(f"Ошибка сети при поиске (время: {total_time:.2f}с): {e}", exc_info=True)
        return f"Произошла ошибка сети при выполнении поиска: {e}"
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Непредвиденная ошибка при поиске (время: {total_time:.2f}с): {e}", exc_info=True)
        return f"Произошла непредвиденная ошибка при выполнении поиска: {e}"


def web_fetch(url: str) -> str:
    """
    Получает и извлекает чистое текстовое содержимое с указанного URL.
    
    ⚠️ ВАЖНО: Если страница очень большая (>10К токенов), используй сначала web_get_structure() 
    чтобы увидеть разделы, затем web_search_in_page() для поиска нужной информации через RAG.

    Args:
        url (str): URL-адрес веб-страницы для чтения.

    Returns:
        str: Чистый текст со страницы или сообщение об ошибке.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        text = '\n'.join(line.strip() for line in soup.get_text(separator='\n', strip=True).splitlines() if line.strip())
        
        # Предупреждение о большом размере
        estimated_tokens = len(text) // 4
        if estimated_tokens > 10000:
            return f"⚠️ ОШИБКА: Страница слишком большая (~{estimated_tokens} токенов).\n\nИСПОЛЬЗУЙ ВМЕСТО ЭТОГО:\n1. web_get_structure('{url}') - получить оглавление\n2. web_search_in_page(url='{url}', query='твой запрос') - RAG-поиск по странице"
        
        return text if text else "Не удалось извлечь содержимое со страницы."
    except requests.exceptions.RequestException as e:
        return f"Ошибка при загрузке URL: {e}"
    except Exception as e:
        return f"Ошибка при обработке страницы: {e}"


def web_get_structure(url: str) -> str:
    """
    Извлекает структуру документа: заголовки (h1-h6) с якорями/ID для навигации.
    Используй этот инструмент первым при работе с большими документациями/статьями.

    Args:
        url (str): URL-адрес веб-страницы.

    Returns:
        str: Иерархическая структура заголовков или сообщение об ошибке.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding  # Автоопределение кодировки (UTF-8)

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Сохраняем полный текст для последующего RAG
        _web_page_cache[url] = soup
        
        structure = []
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = int(heading.name[1])
            indent = "  " * (level - 1)
            text = heading.get_text(strip=True)
            
            # Извлекаем ID/якорь для навигации
            anchor = heading.get('id') or heading.get('name') or ''
            anchor_info = f" #{anchor}" if anchor else ""
            
            structure.append(f"{indent}{heading.name.upper()}: {text}{anchor_info}")
        
        if not structure:
            return "Структура не найдена (нет заголовков на странице)."
        
        header = f"📋 СТРУКТУРА ДОКУМЕНТА: {url}\n{'='*60}\n"
        footer = f"\n{'='*60}\n💡 Используй web_search_in_page(url, query) для поиска нужной информации через RAG"
        
        return header + '\n'.join(structure) + footer
        
    except requests.exceptions.RequestException as e:
        return f"Ошибка при загрузке URL: {e}"
    except Exception as e:
        return f"Ошибка при обработке страницы: {e}"


def web_search_in_page(url: str, query: str, top_k: int = 3) -> str:
    """
    Семантический поиск внутри веб-страницы через RAG (FAISS + embeddings).
    Загружает страницу в память, разбивает на чанки, ищет наиболее релевантные фрагменты.
    
    Используй после web_get_structure() или когда web_fetch() выдал ошибку о большом размере.

    Args:
        url (str): URL-адрес веб-страницы.
        query (str): Поисковый запрос (на русском или английском).
        top_k (int): Количество наиболее релевантных фрагментов для возврата (по умолчанию 3).

    Returns:
        str: Найденные релевантные фрагменты текста или сообщение об ошибке.
    """
    try:
        # Проверяем кэш
        if url not in _web_page_cache:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding  # Исправление кодировки
            soup = BeautifulSoup(response.text, 'html.parser')
            _web_page_cache[url] = soup
        else:
            soup = _web_page_cache[url]
        
        # Удаляем мусор
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
            element.decompose()
        
        # Извлекаем текст
        main_content = soup.find('main') or soup.find('article') or soup.body or soup
        full_text = main_content.get_text(separator='\n', strip=True)
        
        # Разбиваем на чанки (~250 токенов = ~1000 символов каждый)
        # Уменьшено с 2000 до 1000 для экономии контекста
        chunk_size = 1000
        overlap = 150
        chunks = []
        
        for i in range(0, len(full_text), chunk_size - overlap):
            chunk = full_text[i:i + chunk_size]
            if len(chunk.strip()) > 100:  # Пропускаем слишком короткие
                chunks.append(chunk.strip())
        
        if not chunks:
            return "Не удалось извлечь контент со страницы."
        
        # Импортируем для RAG (отложенный импорт)
        import faiss
        import numpy as np
        
        # Используем глобально закэшированную модель эмбеддингов
        global _embedding_model
        if _embedding_model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Загрузка модели эмбеддингов all-MiniLM-L6-v2 (первый запуск)...")
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Модель эмбеддингов загружена и закэширована")
        
        # Создаём эмбеддинги для чанков
        logger.info(f"Создание эмбеддингов для {len(chunks)} чанков...")
        chunk_embeddings = _embedding_model.encode(chunks, show_progress_bar=False)
        
        # Создаём FAISS индекс
        dimension = chunk_embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(chunk_embeddings).astype('float32'))
        
        # Поиск
        query_embedding = _embedding_model.encode([query], show_progress_bar=False)
        distances, indices = index.search(np.array(query_embedding).astype('float32'), top_k)
        
        # Формируем ответ
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(chunks):
                score = 1 / (1 + distances[0][i])  # Нормализация distance в score
                results.append(f"📄 ФРАГМЕНТ {i+1} (релевантность: {score:.2%}):\n{chunks[idx]}")
        
        header = f"🔍 РЕЗУЛЬТАТЫ RAG-ПОИСКА по запросу: '{query}'\n{'='*60}\n"
        footer = f"\n{'='*60}\n💡 Найдено {len(results)} релевантных фрагмента из {len(chunks)} чанков"
        
        return header + '\n\n'.join(results) + footer
        
    except ImportError as e:
        return f"Ошибка: Не установлены библиотеки для RAG (sentence-transformers, faiss). Детали: {e}"
    except requests.exceptions.RequestException as e:
        return f"Ошибка при загрузке URL: {e}"
    except Exception as e:
        logger.error(f"Ошибка RAG-поиска: {e}", exc_info=True)
        return f"Ошибка при выполнении поиска: {e}"


# Глобальные кэши
_web_page_cache = {}  # Кэш веб-страниц
_embedding_model = None  # Кэш модели эмбеддингов (загружается при первом использовании)


def list_directory(path: str = '.') -> str:
    """
    Возвращает список файлов и директорий по указанному пути, разделенный переносами строк. Используй для обзора содержимого директории.

    Args:
        path (str): Путь к директории для отображения.

    Returns:
        str: Список имен файлов и директорий или сообщение об ошибке.
    """
    try:
        entries = os.listdir(path)
        return "\n".join(entries) if entries else "Директория пуста."
    except FileNotFoundError:
        return f"Ошибка: Директория не найдена по пути '{path}'."
    except Exception as e:
        return f"Произошла ошибка: {e}"

def read_file(file_path: str) -> str:
    """
    Читает и возвращает полное содержимое ЛОКАЛЬНОГО текстового файла. 
    ⚠️ НЕ ИСПОЛЬЗУЙ для URL-адресов! Для веб-страниц используй web_fetch, web_get_structure или web_search_in_page.

    Args:
        file_path (str): Локальный путь к файлу (НЕ URL).

    Returns:
        str: Содержимое файла или сообщение об ошибке.
    """
    # Проверка: это URL, а не локальный файл?
    if file_path.startswith(('http://', 'https://', 'ftp://')):
        return (
            f"❌❌❌ КРИТИЧЕСКАЯ ОШИБКА: read_file() НЕ УМЕЕТ работать с URL! ❌❌❌\n\n"
            f"Ты пытался: read_file('{file_path}')\n"
            f"Это НЕВОЗМОЖНО! read_file() читает только ЛОКАЛЬНЫЕ файлы на диске!\n\n"
            f"✅ ПРАВИЛЬНЫЕ инструменты для веб-страниц:\n"
            f"  1. web_search_in_page(url, query) - ЛУЧШИЙ выбор для поиска информации\n"
            f"  2. web_get_structure(url) - получить оглавление страницы\n"
            f"  3. web_fetch(url) - только для маленьких страниц (<5000 символов)\n\n"
            f"❗ НЕ пытайся больше использовать read_file() с URL! Используй web_search_in_page()!"
        )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Ошибка: Файл не найден по пути '{file_path}'."
    except Exception as e:
        return f"Ошибка при чтении файла: {e}"

def write_file(file_path: str, content: str) -> str:
    """
    Записывает (создает новый) или полностью перезаписывает текстовый файл. Используй для сохранения нового кода или полного изменения файла.

    Args:
        file_path (str): Путь к файлу для записи.
        content (str): Содержимое для записи.

    Returns:
        str: Сообщение об успехе или ошибке.
    """
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Файл успешно записан по пути: {file_path}"
    except Exception as e:
        return f"Ошибка при записи файла: {e}"

def create_file(file_path: str, content: str = "") -> str:
    """
    Создает новый текстовый файл. Возвращает ошибку, если файл уже существует.

    Args:
        file_path (str): Путь к файлу для создания.
        content (str): Начальное содержимое файла.

    Returns:
        str: Сообщение об успехе или ошибке.
    """
    try:
        path_obj = Path(file_path)
        if path_obj.exists():
            return f"Ошибка: Файл '{file_path}' уже существует."
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text(content, encoding='utf-8')
        return f"Файл успешно создан по пути: {file_path}"
    except Exception as e:
        return f"Ошибка при создании файла: {e}"

def replace_in_file(file_path: str, old_string: str, new_string: str) -> str:
    """
    Находит и заменяет все вхождения 'old_string' на 'new_string' в файле. Используй для точечного редактирования кода.

    Args:
        file_path (str): Путь к файлу для модификации.
        old_string (str): Строка для замены.
        new_string (str): Новая строка.

    Returns:
        str: Сообщение об успехе или ошибке.
    """
    try:
        path_obj = Path(file_path)
        if not path_obj.is_file():
            return f"Ошибка: Файл не найден по пути '{file_path}'."
        original_content = path_obj.read_text(encoding='utf-8')
        if old_string not in original_content:
            return f"Информация: Строка для замены не найдена. Файл не изменен."
        new_content = original_content.replace(old_string, new_string)
        path_obj.write_text(new_content, encoding='utf-8')
        return f"Замена в файле '{file_path}' успешно выполнена."
    except Exception as e:
        return f"Ошибка при замене в файле: {e}"

def run_shell_command(command: str) -> str:
    """
    Выполняет команду в 'bash' и возвращает ее stdout, stderr и код завершения. Используй для компиляции, тестов, git. Не используй для чтения/записи файлов.

    Args:
        command (str): Команда для выполнения.

    Returns:
        str: Результат выполнения команды.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            encoding='utf-8', timeout=30
        )
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr}\n"
        return output.strip()
    except subprocess.TimeoutExpired:
        return "Ошибка: Команда выполнялась слишком долго и была прервана."
    except Exception as e:
        return f"Ошибка при выполнении команды: {e}"

# --- Инструменты для управления памятью ---

def list_memories() -> str:
    """
    Показывает пронумерованный список всех записей в долгосрочной памяти.
    Используй, чтобы понять, что уже известно.
    """
    # Реализация находится в agent.py, так как требует доступа к self.vector_memory
    return "Этот инструмент реализован в ядре агента."

def delete_memory(entry_id: int) -> str:
    """
    Удаляет запись из долгосрочной памяти по ее ID.
    Используй для удаления неверной или устаревшей информации.

    Args:
        entry_id (int): ID записи, которую нужно удалить.
    """
    # Реализация находится в agent.py
    return "Этот инструмент реализован в ядре агента."

def add_memory(text: str) -> str:
    """
    Добавляет новую текстовую запись в долгосрочную память.
    Используй, чтобы сохранить важную информацию, которую нужно запомнить надолго.

    Args:
        text (str): Текст для сохранения в памяти.
    """
    # Реализация находится в agent.py
    return "Этот инструмент реализован в ядре агента."


def analyze_code(file_path: str) -> str:
    """
    Анализирует структуру ЛОКАЛЬНОГО Python-файла без его выполнения. 
    Возвращает список функций, классов, импортов и их расположение.
    ⚠️ НЕ ИСПОЛЬЗУЙ для URL или HTML кода! Только для локальных .py файлов.
    
    Args:
        file_path (str): Локальный путь к Python-файлу для анализа (НЕ URL, НЕ HTML).

    Returns:
        str: Структурированный отчёт о коде (импорты, функции, классы с номерами строк).
    """
    import ast
    
    # Проверка: это URL, а не локальный файл?
    if file_path.startswith(('http://', 'https://', 'ftp://')):
        return (
            f"❌ ОШИБКА: analyze_code() работает только с ЛОКАЛЬНЫМИ Python-файлами!\n"
            f"Ты пытаешься анализировать URL: {file_path}\n\n"
            f"Для веб-страниц используй:\n"
            f"  • web_fetch(url) - получить текст страницы\n"
            f"  • web_get_structure(url) - получить структуру (заголовки)\n"
            f"  • web_search_in_page(url, query) - найти конкретную информацию\n\n"
            f"analyze_code() нужен только для анализа локальных .py файлов в проекте!"
        )
    
    # Проверка: это не Python файл?
    if not file_path.endswith('.py'):
        return (
            f"❌ ОШИБКА: analyze_code() работает только с Python-файлами (.py)!\n"
            f"Твой файл: {file_path}\n\n"
            f"Если это HTML/текст из интернета - используй web_search_in_page()"
        )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        tree = ast.parse(source_code, filename=file_path)
        
        report_lines = [f"📊 Анализ файла: {file_path}", ""]
        
        # Собираем импорты
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"  • import {alias.name} (строка {node.lineno})")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"  • from {module} import {alias.name} (строка {node.lineno})")
        
        if imports:
            report_lines.append("📦 Импорты:")
            report_lines.extend(imports[:15])  # Ограничиваем вывод
            if len(imports) > 15:
                report_lines.append(f"  ... и ещё {len(imports) - 15} импортов")
            report_lines.append("")
        
        # Собираем классы
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                methods_str = f" (методы: {', '.join(methods[:5])}{'...' if len(methods) > 5 else ''})" if methods else ""
                classes.append(f"  • class {node.name}{methods_str} (строка {node.lineno})")
        
        if classes:
            report_lines.append("🏛️ Классы:")
            report_lines.extend(classes)
            report_lines.append("")
        
        # Собираем функции верхнего уровня
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # Получаем параметры
                args = [arg.arg for arg in node.args.args]
                args_str = ', '.join(args)
                functions.append(f"  • def {node.name}({args_str}) (строка {node.lineno})")
        
        if functions:
            report_lines.append("⚙️ Функции (верхнего уровня):")
            report_lines.extend(functions)
            report_lines.append("")
        
        # Собираем глобальные переменные/константы
        globals_vars = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        globals_vars.append(f"  • {target.id} (строка {node.lineno})")
        
        if globals_vars:
            report_lines.append("🔧 Глобальные переменные:")
            report_lines.extend(globals_vars[:10])
            if len(globals_vars) > 10:
                report_lines.append(f"  ... и ещё {len(globals_vars) - 10} переменных")
            report_lines.append("")
        
        # Статистика
        total_lines = len(source_code.split('\n'))
        report_lines.append(f"📈 Статистика: {total_lines} строк, {len(classes)} классов, {len(functions)} функций")
        
        return "\n".join(report_lines)
    
    except SyntaxError as e:
        return f"Ошибка синтаксиса в файле {file_path}: {e.msg} на строке {e.lineno}"
    except FileNotFoundError:
        return f"Ошибка: файл '{file_path}' не найден."
    except Exception as e:
        return f"Ошибка при анализе файла: {e}"


def edit_file_at_line(file_path: str, start_line: int, end_line: int, new_content: str) -> str:
    """
    Заменяет указанный диапазон строк в файле на новое содержимое. Используй для точечного редактирования кода.
    Номера строк начинаются с 1. Для вставки новых строк используй start_line == end_line.

    Args:
        file_path (str): Путь к файлу для редактирования.
        start_line (int): Начальная строка для замены (включительно, от 1).
        end_line (int): Конечная строка для замены (включительно, от 1).
        new_content (str): Новое содержимое для вставки.

    Returns:
        str: Сообщение об успехе или ошибке.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Валидация параметров
        if start_line < 1 or end_line < 1:
            return f"Ошибка: номера строк должны быть >= 1. Получено: start={start_line}, end={end_line}"
        
        if start_line > end_line:
            return f"Ошибка: start_line ({start_line}) больше end_line ({end_line})"
        
        if start_line > total_lines:
            return f"Ошибка: start_line ({start_line}) больше общего числа строк ({total_lines})"
        
        # Корректируем end_line если он выходит за границы
        if end_line > total_lines:
            end_line = total_lines
        
        # Подготавливаем новое содержимое (добавляем \n если нет)
        if new_content and not new_content.endswith('\n'):
            new_content += '\n'
        
        # Собираем новый файл
        # Python использует 0-индексацию, а пользователь указывает с 1
        new_lines = (
            lines[:start_line - 1] +          # Строки до изменения
            [new_content] +                    # Новое содержимое
            lines[end_line:]                   # Строки после изменения
        )
        
        # Записываем обратно
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        lines_replaced = end_line - start_line + 1
        return f"Успешно заменены строки {start_line}-{end_line} ({lines_replaced} строк) в файле '{file_path}'."
    
    except FileNotFoundError:
        return f"Ошибка: файл '{file_path}' не найден."
    except Exception as e:
        return f"Ошибка при редактировании файла: {e}"


def finish(final_answer: str) -> str:
    """
    Вызови этот инструмент, когда все шаги плана выполнены и ты готов предоставить окончательный ответ.

    Args:
        final_answer (str): Итоговый, подробный ответ для пользователя.

    Returns:
        str: Сообщение о завершении работы.
    """
    return f"Задача выполнена. Финальный ответ: {final_answer}"