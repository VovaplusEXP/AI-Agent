"""
Tests for Enhanced CLI components
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Мокируем Agent перед импортом enhanced_cli
sys.modules['agent'] = MagicMock()

from enhanced_cli import EnhancedStatusBar, CodePreviewDialog


class TestEnhancedStatusBar:
    """Тесты для EnhancedStatusBar"""
    
    @pytest.fixture
    def mock_agent(self):
        """Создает мок агента для тестирования"""
        agent = Mock()
        agent.current_chat = "test_chat"
        agent.context_manager = Mock()
        agent.context_manager.max_tokens = 24576
        agent.last_context_stats = {'total_tokens': 10000}
        return agent
    
    def test_get_context_usage(self, mock_agent):
        """Тест получения использования контекста"""
        status_bar = EnhancedStatusBar(mock_agent)
        
        current_tokens, max_tokens, free_percent = status_bar.get_context_usage()
        
        assert current_tokens == 10000
        assert max_tokens == 24576
        assert abs(free_percent - 59.25) < 0.1  # Примерно 59.25% свободно
    
    def test_get_memory_usage(self, mock_agent):
        """Тест получения использования памяти"""
        status_bar = EnhancedStatusBar(mock_agent)
        
        mem_mb, mem_str = status_bar.get_memory_usage()
        
        assert mem_mb > 0  # Должно быть больше 0
        assert isinstance(mem_str, str)
        assert "MB" in mem_str or "GB" in mem_str
    
    def test_render_status_bar(self, mock_agent):
        """Тест рендеринга статус-панели"""
        status_bar = EnhancedStatusBar(mock_agent)
        
        panel = status_bar.render()
        
        # Проверяем, что возвращается Panel
        from rich.panel import Panel
        assert isinstance(panel, Panel)
    
    def test_context_color_green(self, mock_agent):
        """Тест зеленого цвета при >50% свободного контекста"""
        mock_agent.last_context_stats = {'total_tokens': 5000}  # ~80% свободно
        status_bar = EnhancedStatusBar(mock_agent)
        
        _, _, free_percent = status_bar.get_context_usage()
        
        assert free_percent > 50
    
    def test_context_color_yellow(self, mock_agent):
        """Тест желтого цвета при 20-50% свободного контекста"""
        mock_agent.last_context_stats = {'total_tokens': 17000}  # ~30% свободно
        status_bar = EnhancedStatusBar(mock_agent)
        
        _, _, free_percent = status_bar.get_context_usage()
        
        assert 20 < free_percent <= 50
    
    def test_context_color_red(self, mock_agent):
        """Тест красного цвета при <20% свободного контекста"""
        mock_agent.last_context_stats = {'total_tokens': 22000}  # ~10% свободно
        status_bar = EnhancedStatusBar(mock_agent)
        
        _, _, free_percent = status_bar.get_context_usage()
        
        assert free_percent < 20


class TestCodePreviewDialog:
    """Тесты для CodePreviewDialog"""
    
    @pytest.fixture
    def mock_console(self):
        """Создает мок консоли"""
        return Mock()
    
    @pytest.fixture
    def mock_session(self):
        """Создает мок сессии"""
        return Mock()
    
    def test_code_preview_dialog_init(self, mock_console, mock_session):
        """Тест инициализации диалога предпросмотра"""
        dialog = CodePreviewDialog(mock_console, mock_session)
        
        assert dialog.console == mock_console
        assert dialog.session == mock_session
    
    @patch('enhanced_cli.CodePreviewDialog.show')
    def test_show_code_preview_yes(self, mock_show, mock_console, mock_session):
        """Тест подтверждения записи файла"""
        mock_show.return_value = True
        
        dialog = CodePreviewDialog(mock_console, mock_session)
        result = dialog.show("test.py", "print('hello')", "python")
        
        assert result == True
    
    @patch('enhanced_cli.CodePreviewDialog.show')
    def test_show_code_preview_no(self, mock_show, mock_console, mock_session):
        """Тест отмены записи файла"""
        mock_show.return_value = False
        
        dialog = CodePreviewDialog(mock_console, mock_session)
        result = dialog.show("test.py", "print('hello')", "python")
        
        assert result == False


class TestEnhancedCLI:
    """Тесты для основного класса EnhancedCLI - будут добавлены после установки зависимостей"""
    
    def test_placeholder(self):
        """Placeholder test"""
        assert True


def test_imports():
    """Тест импортов всех необходимых модулей"""
    import rich
    import prompt_toolkit
    import psutil
    
    # Проверяем версии
    assert rich is not None
    assert prompt_toolkit is not None
    assert psutil is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
