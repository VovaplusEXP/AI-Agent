"""
Unit-тесты для парсеров v3.0.0 (флаговый формат + fallback на JSON).

Покрывает:
- Кейс 1: Простое создание файла
- Кейс 2: Regex паттерны (проблемный в v2.1.2)
- Кейс 3: JSON внутри кода
- Кейс 4: Многострочные строки
- Кейс 5: Bash команды с кавычками
- Edge cases: отсутствие опциональных блоков, fallback на JSON
"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers import parse_flagged_response, parse_json_response, parse_response_with_fallback


class TestFlaggedParser:
    """Тесты для нового флагового формата v3.0.0"""
    
    def test_case_1_simple_file_creation(self):
        """Кейс 1: Простое создание файла с Python кодом"""
        
        response = """<THOUGHT>
Нужно создать Python файл с простой функцией приветствия
<TOOL>
write_file
<PARAMS>
{"file_path": "hello.py"}
<CONTENT>
def greet(name):
    print(f"Привет, {name}!")

if __name__ == "__main__":
    greet("Мир")
<END>"""
        
        result = parse_flagged_response(response)
        
        assert result['thought'] == "Нужно создать Python файл с простой функцией приветствия"
        assert result['tool_name'] == "write_file"
        assert result['parameters']['file_path'] == "hello.py"
        assert 'def greet(name):' in result['parameters']['content']
        assert 'print(f"Привет, {name}!")' in result['parameters']['content']
    
    def test_case_2_regex_patterns(self):
        """Кейс 2: Regex паттерны (проблемный в v2.1.2) 🔥"""
        
        response = r"""<THOUGHT>
Создам скрипт с regex для валидации email адресов
<TOOL>
write_file
<PARAMS>
{"file_path": "validate_email.py"}
<CONTENT>
import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Тест
test_emails = [
    "user@example.com",
    "invalid.email",
    "test+tag@domain.co.uk"
]

for email in test_emails:
    print(f"{email}: {validate_email(email)}")
<END>"""
        
        result = parse_flagged_response(response)
        
        assert result['tool_name'] == "write_file"
        assert result['parameters']['file_path'] == "validate_email.py"
        
        # КРИТИЧНО: Проверяем, что все невалидные JSON escapes сохранились
        content = result['parameters']['content']
        assert r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$' in content
        assert r'pattern = r' in content
        assert 'import re' in content
    
    def test_case_3_json_inside_code(self):
        """Кейс 3: JSON внутри кода (двойные проблемы с escaping) 🔥"""
        
        response = r"""<THOUGHT>
Создам скрипт для работы с JSON
<TOOL>
write_file
<PARAMS>
{"file_path": "json_handler.py"}
<CONTENT>
import json

data = {
    "name": "John \"The Great\"",
    "path": "C:\\Users\\John\\Documents",
    "regex": r"\d+\.\d+",
    "url": "https://example.com/api?param=value"
}

json_str = json.dumps(data, indent=2)
print(json_str)
<END>"""
        
        result = parse_flagged_response(response)
        
        content = result['parameters']['content']
        
        # Проверяем, что все специальные символы сохранились
        assert 'John "The Great"' in content or r'John \"The Great\"' in content
        assert 'C:' in content and 'Users' in content and 'John' in content  # путь сохранился
        assert r'\d+' in content or 'd+' in content  # regex паттерн
        assert 'https://example.com' in content
    
    def test_case_4_multiline_strings(self):
        """Кейс 4: Многострочные строки с разными кавычками"""
        
        response = """<THOUGHT>
Создам файл с многострочными строками
<TOOL>
write_file
<PARAMS>
{"file_path": "multiline.py"}
<CONTENT>
text = '''
Это многострочный текст
с разными "кавычками" и 'апострофами'
и даже backslash: \\
'''

query = \"\"\"
SELECT * 
FROM users 
WHERE name = 'John' AND status != "inactive"
\"\"\"

print(text)
print(query)
<END>"""
        
        result = parse_flagged_response(response)
        
        content = result['parameters']['content']
        
        # Все кавычки и escapes должны остаться как есть
        assert "'''" in content
        assert '"""' in content
        assert "WHERE name = 'John'" in content
        assert 'status != "inactive"' in content
    
    def test_case_5_bash_commands(self):
        """Кейс 5: Bash команды с кавычками и спецсимволами"""
        
        response = """<THOUGHT>
Создам bash скрипт для автоматизации
<TOOL>
write_file
<PARAMS>
{"file_path": "deploy.sh"}
<CONTENT>
#!/bin/bash

# Переменные
APP_DIR="/var/www/app"
BACKUP_DIR="/backup/$(date +%Y-%m-%d)"

# Создать бэкап
tar -czf "$BACKUP_DIR/app.tar.gz" "$APP_DIR"

# Развернуть новую версию
cd "$APP_DIR" && git pull origin main

# Перезапустить сервис
systemctl restart myapp.service

echo "Deployment complete!"
<END>"""
        
        result = parse_flagged_response(response)
        
        content = result['parameters']['content']
        
        # Все bash конструкции должны быть валидными
        assert '#!/bin/bash' in content
        assert 'BACKUP_DIR="/backup/$(date +%Y-%m-%d)"' in content
        assert 'tar -czf' in content
        assert 'systemctl restart' in content
    
    def test_optional_params_block(self):
        """Edge case: Отсутствие блока <PARAMS> (опциональный)"""
        
        response = """<THOUGHT>
Просто список файлов
<TOOL>
list_files
<CONTENT>
.
<END>"""
        
        result = parse_flagged_response(response)
        
        assert result['thought'] == "Просто список файлов"
        assert result['tool_name'] == "list_files"
        assert result['parameters']['content'] == "."
    
    def test_optional_content_block(self):
        """Edge case: Отсутствие блока <CONTENT> (опциональный)"""
        
        response = """<THOUGHT>
Получить текущее время
<TOOL>
get_current_time
<PARAMS>
{"format": "ISO8601"}
<END>"""
        
        result = parse_flagged_response(response)
        
        assert result['thought'] == "Получить текущее время"
        assert result['tool_name'] == "get_current_time"
        assert result['parameters']['format'] == "ISO8601"
        assert 'content' not in result['parameters'] or result['parameters']['content'] == ""
    
    def test_missing_required_thought(self):
        """Edge case: Отсутствие <THOUGHT> - парсер должен восстановить"""
        
        response = """<TOOL>
write_file
<PARAMS>
{"file_path": "test.py"}
<END>"""
        
        # Парсер v3.0.0 ВОССТАНАВЛИВАЕТ отсутствующий thought
        result = parse_flagged_response(response)
        assert result['tool_name'] == 'write_file'
        # Thought будет восстановлен как текст до <TOOL> или заглушка
        assert 'write_file' in result['thought']
    
    def test_missing_required_tool(self):
        """Edge case: Отсутствие обязательного блока <TOOL>"""
        
        response = """<THOUGHT>
Какая-то мысль
<PARAMS>
{"file_path": "test.py"}
<END>"""
        
        with pytest.raises(ValueError, match="отсутствует обязательный флаг <TOOL>"):
            parse_flagged_response(response)
    
    def test_invalid_json_in_params(self):
        """Edge case: Невалидный JSON в <PARAMS>"""
        
        response = """<THOUGHT>
Создать файл
<TOOL>
write_file
<PARAMS>
{broken json here}
<END>"""
        
        with pytest.raises(ValueError, match="Невалидный JSON в <PARAMS>"):
            parse_flagged_response(response)


class TestJSONParserLegacy:
    """Тесты для старого JSON парсера v2.1.2 (legacy, для fallback)"""
    
    def test_valid_json_with_escapes(self):
        """JSON формат с проблемными escapes (v2.1.2 должен справиться)"""
        
        response = """{
    "thought": "Создать файл с regex",
    "action": {
        "tool_name": "write_file",
        "parameters": {
            "file_path": "test.py",
            "content": "pattern = r'\\d+\\.\\d+'"
        }
    }
}"""
        
        result = parse_json_response(response)
        
        assert result['thought'] == "Создать файл с regex"
        assert result['tool_name'] == "write_file"
        assert result['parameters']['file_path'] == "test.py"
        # Очистка должна была удалить невалидные escapes
        assert 'pattern' in result['parameters']['content']
    
    def test_json_in_markdown_block(self):
        """JSON внутри markdown блока"""
        
        response = """Вот мой ответ:
```json
{
    "thought": "Создать файл",
    "action": {
        "tool_name": "write_file",
        "parameters": {
            "file_path": "hello.py"
        }
    }
}
```
Готово!"""
        
        result = parse_json_response(response)
        
        assert result['thought'] == "Создать файл"
        assert result['tool_name'] == "write_file"


class TestFallbackParser:
    """Тесты для универсального парсера с fallback"""
    
    def test_fallback_prefers_flagged_format(self):
        """Fallback парсер предпочитает флаговый формат"""
        
        response = """<THOUGHT>
Создать файл
<TOOL>
write_file
<PARAMS>
{"file_path": "test.py"}
<CONTENT>
print("Hello")
<END>"""
        
        result = parse_response_with_fallback(response)
        
        assert result['tool_name'] == "write_file"
        assert 'print("Hello")' in result['parameters']['content']
    
    def test_fallback_to_json_when_flags_fail(self):
        """Fallback на JSON когда флаги не распознаны"""
        
        response = """{
    "thought": "Создать файл",
    "action": {
        "tool_name": "write_file",
        "parameters": {
            "file_path": "test.py",
            "content": "print('Hello')"
        }
    }
}"""
        
        result = parse_response_with_fallback(response)
        
        assert result['thought'] == "Создать файл"
        assert result['tool_name'] == "write_file"
        assert result['parameters']['file_path'] == "test.py"
    
    def test_fallback_fails_on_both_formats(self):
        """Fallback выбрасывает ошибку если оба формата невалидны"""
        
        response = "Просто какой-то текст без формата"
        
        with pytest.raises(Exception):  # JSONDecodeError или ValueError
            parse_response_with_fallback(response)


# Запуск тестов
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
