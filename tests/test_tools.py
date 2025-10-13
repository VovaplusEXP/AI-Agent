"""
Unit and Integration Tests for the Agent's Tools.

To run only the fast, local unit tests (mocks):
> pytest

To run only the integration tests that require a network connection:
> pytest -m integration

To run all tests:
> pytest -m "unit or integration"

"""
import os
import unittest
from unittest.mock import patch, MagicMock
import pytest
import requests

# Добавляем корневую директорию проекта в sys.path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import (
    internet_search,
    web_fetch,
    list_directory,
    read_file,
    write_file,
    create_file,
    replace_in_file,
    run_shell_command,
    analyze_code,
    edit_file_at_line,
    finish
)

# --- Маркеры для тестов ---
unit = pytest.mark.unit
integration = pytest.mark.integration


# --- Тесты для файловых операций ---

@pytest.fixture(scope="function")
def temp_file(tmp_path):
    """Фикстура для создания временного файла и директории для тестов."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    file_path = test_dir / "test_file.txt"
    file_path.write_text("Hello, world!")
    return file_path, test_dir

@unit
def test_list_directory_success(temp_file):
    """Тест успешного листинга директории."""
    _, test_dir = temp_file
    result = list_directory(str(test_dir))
    assert "test_file.txt" in result
    assert "не найдена" not in result

@unit
def test_list_directory_not_found():
    """Тест листинга несуществующей директории."""
    result = list_directory("non_existent_dir")
    assert "Ошибка: Директория не найдена" in result

@unit
def test_read_file_success(temp_file):
    """Тест успешного чтения файла."""
    file_path, _ = temp_file
    content = read_file(str(file_path))
    assert content == "Hello, world!"

@unit
def test_read_file_not_found():
    """Тест чтения несуществующего файла."""
    content = read_file("non_existent_file.txt")
    assert "Ошибка: Файл не найден" in content

def test_write_file_success(tmp_path):
    """Тест успешной записи в файл."""
    new_file_path = tmp_path / "new_file.txt"
    content_to_write = "This is a new file."
    result = write_file(str(new_file_path), content_to_write)
    
    assert "Файл успешно записан" in result
    assert new_file_path.read_text() == content_to_write

@unit
def test_create_file_success(tmp_path):
    """Тест успешного создания нового файла."""
    file_path = tmp_path / "newly_created.txt"
    result = create_file(str(file_path), "initial content")
    assert "Файл успешно создан" in result
    assert file_path.exists()
    assert file_path.read_text() == "initial content"

@unit
def test_create_file_already_exists(temp_file):
    """Тест на ошибку, если создаваемый файл уже существует."""
    file_path, _ = temp_file
    result = create_file(str(file_path), "some content")
    assert "Ошибка: Файл" in result
    assert "уже существует" in result

@unit
def test_replace_in_file_success(temp_file):
    """Тест успешной замены строки в файле."""
    file_path, _ = temp_file
    assert file_path.read_text() == "Hello, world!" # Проверка начального состояния
    
    result = replace_in_file(str(file_path), "world", "pytest")
    assert "Замена в файле" in result
    assert "успешно выполнена" in result
    assert file_path.read_text() == "Hello, pytest!"

@unit
def test_replace_in_file_string_not_found(temp_file):
    """Тест замены в файле, когда строка не найдена."""
    file_path, _ = temp_file
    result = replace_in_file(str(file_path), "nonexistent", "string")
    assert "не найдена" in result or "не изменен" in result
    assert file_path.read_text() == "Hello, world!" # Содержимое не должно измениться

@unit
def test_replace_in_file_not_found_error():
    """Тест замены в несуществующем файле."""
    result = replace_in_file("non/existent/file.txt", "a", "b")
    assert "Ошибка: Файл не найден" in result

# --- Тесты для `run_shell_command` ---

@unit
def test_run_shell_command_success():
    """Тест успешного выполнения команды в оболочке."""
    result = run_shell_command('echo "hello world"')
    assert "hello world" in result
    assert "STDOUT" in result
    assert "Exit Code: 0" in result
    assert "STDERR" not in result

@unit
def test_run_shell_command_error():
    """Тест выполнения команды, которая завершается с ошибкой."""
    # Команда 'ls' на несуществующую директорию вернет ненулевой код
    result = run_shell_command('ls non_existent_directory_for_test')
    assert "STDERR" in result
    assert "Exit Code:" in result
    assert "0" not in result # Код завершения не должен быть 0

# --- Тесты для сетевых инструментов с использованием моков ---

@unit
@patch('tools.requests.get')
def test_internet_search_success_mock(mock_get):
    """Тест успешного поиска в интернете с моком."""
    # Настраиваем мок для возврата успешного ответа
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "title": "Test Title",
                "link": "http://example.com",
                "snippet": "Test snippet."
            }
        ]
    }
    mock_get.return_value = mock_response
    
    # Устанавливаем временные переменные окружения
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key", "GOOGLE_CSE_ID": "test_id"}):
        result = internet_search("test query")

    assert "Test Title" in result
    assert "http://example.com" in result
    assert "Ошибка" not in result

@unit
@patch('tools.requests.get', side_effect=requests.exceptions.RequestException("Network Error"))
def test_internet_search_network_error_mock(mock_get):
    """Тест обработки сетевой ошибки при поиске."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key", "GOOGLE_CSE_ID": "test_id"}):
        result = internet_search("test query")
    assert "Произошла ошибка сети" in result

@unit
def test_internet_search_no_api_keys_mock():
    """Тест проверки отсутствия API ключей."""
    # Убедимся, что переменных окружения нет
    with patch.dict(os.environ, {}, clear=True):
        result = internet_search("test query")
    assert "Переменные окружения GOOGLE_API_KEY и GOOGLE_CSE_ID не установлены" in result

@unit
@patch('tools.requests.get')
def test_web_fetch_success_mock(mock_get):
    """Тест успешного получения содержимого веб-страницы."""
    # Мокаем ответ от requests.get
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.text = "<html><head><title>Test</title></head><body><p>Hello content</p></body></html>"
    mock_get.return_value = mock_response

    result = web_fetch("http://example.com")
    
    assert "Hello content" in result
    assert "Ошибка при загрузке URL" not in result

@unit
@patch('tools.requests.get', side_effect=requests.exceptions.RequestException("Failed to connect"))
def test_web_fetch_request_exception_mock(mock_get):
    """Тест обработки ошибки при загрузке URL."""
    result = web_fetch("http://example.com")
    assert "Ошибка при загрузке URL: Failed to connect" in result

# --- Тест для `finish` ---

@unit
def test_finish():
    """Тест для функции завершения."""
    final_answer = "Все задачи выполнены."
    result = finish(final_answer)
    assert final_answer in result
    assert "Задача выполнена" in result

# --- Интеграционные тесты (требуют реального сетевого подключения) ---

@integration
def test_web_fetch_integration_real_url():
    """
    Интеграционный тест для web_fetch с реальным, стабильным URL.
    """
    url = "http://info.cern.ch/" # Первый в мире веб-сайт, очень стабильный
    result = web_fetch(url)
    assert "http" in result.lower()
    assert "Ошибка" not in result

@integration
@pytest.mark.skipif(
    not (os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID")),
    reason="Для этого теста необходимы GOOGLE_API_KEY и GOOGLE_CSE_ID"
)
def test_internet_search_integration_real_query():
    """
    Интеграционный тест для internet_search с реальным запросом.
    Пропускается, если не установлены переменные окружения.
    """
    result = internet_search("новости науки")
    assert isinstance(result, str)
    assert "Ошибка" not in result
    assert len(result) > 10 # Ожидаем непустой результат


# --- Тесты для analyze_code ---

@unit
def test_analyze_code_valid_file(tmp_path):
    """Тест анализа валидного Python файла."""
    test_file = tmp_path / "test_module.py"
    test_file.write_text("""
import os
from pathlib import Path

CONSTANT = 42

def hello(name):
    return f"Hello, {name}"

class MyClass:
    def __init__(self):
        pass
    
    def method(self, x):
        return x * 2
""")
    
    result = analyze_code(str(test_file))
    assert "Анализ файла" in result
    assert "Импорты" in result
    assert "import os" in result
    assert "from pathlib import Path" in result
    assert "Функции" in result
    assert "def hello(name)" in result
    assert "Классы" in result
    assert "class MyClass" in result
    assert "Глобальные переменные" in result
    assert "CONSTANT" in result


@unit
def test_analyze_code_syntax_error(tmp_path):
    """Тест анализа файла с синтаксической ошибкой."""
    test_file = tmp_path / "bad_syntax.py"
    test_file.write_text("def broken(\n    pass")  # Незакрытая скобка
    
    result = analyze_code(str(test_file))
    assert "Ошибка синтаксиса" in result


@unit
def test_analyze_code_file_not_found():
    """Тест анализа несуществующего файла."""
    result = analyze_code("/nonexistent/file.py")
    assert "не найден" in result


# --- Тесты для edit_file_at_line ---

@unit
def test_edit_file_at_line_replace_single(tmp_path):
    """Тест замены одной строки."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line 1\nline 2\nline 3\n")
    
    result = edit_file_at_line(str(test_file), 2, 2, "NEW LINE 2")
    assert "Успешно" in result
    
    content = test_file.read_text()
    assert content == "line 1\nNEW LINE 2\nline 3\n"


@unit
def test_edit_file_at_line_replace_range(tmp_path):
    """Тест замены диапазона строк."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line 1\nline 2\nline 3\nline 4\n")
    
    result = edit_file_at_line(str(test_file), 2, 3, "MERGED LINES 2-3")
    assert "Успешно" in result
    
    content = test_file.read_text()
    assert content == "line 1\nMERGED LINES 2-3\nline 4\n"


@unit
def test_edit_file_at_line_insert(tmp_path):
    """Тест вставки новой строки (start == end)."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line 1\nline 2\n")
    
    result = edit_file_at_line(str(test_file), 2, 2, "INSERTED")
    assert "Успешно" in result
    
    content = test_file.read_text()
    assert "INSERTED" in content


@unit
def test_edit_file_at_line_invalid_params(tmp_path):
    """Тест с невалидными параметрами."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("line 1\n")
    
    # start > end
    result = edit_file_at_line(str(test_file), 5, 2, "text")
    assert "Ошибка" in result
    
    # start < 1
    result = edit_file_at_line(str(test_file), 0, 1, "text")
    assert "Ошибка" in result
    
    # start > total_lines
    result = edit_file_at_line(str(test_file), 100, 100, "text")
    assert "Ошибка" in result


@unit
def test_edit_file_at_line_file_not_found():
    """Тест редактирования несуществующего файла."""
    result = edit_file_at_line("/nonexistent/file.txt", 1, 1, "text")
    assert "не найден" in result


if __name__ == "__main__":
    # Запуск с аргументами для включения всех маркеров
    pytest.main(["-m", "unit or integration"])
