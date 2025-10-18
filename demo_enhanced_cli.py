#!/usr/bin/env python3
"""
Demo script to showcase Enhanced CLI features without needing the full LLM
This demonstrates the visual components and UI improvements
"""
import os
import sys
from pathlib import Path
from unittest.mock import Mock

# Мокируем Agent для демо
sys.modules['agent'] = Mock()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich import box
import time

console = Console()


def demo_welcome_screen():
    """Демонстрация экрана приветствия"""
    console.clear()
    
    # ASCII art logo
    logo = """
╔═══════════════════════════════════════════╗
║                                           ║
║         🤖  AI Agent Enhanced CLI         ║
║                                           ║
║         Powered by Gemma-3n-E4B          ║
║                                           ║
╚═══════════════════════════════════════════╝
    """
    
    console.print(logo, style="bold cyan", justify="center")
    console.print()
    
    # Статус-панель
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left")
    table.add_column(justify="left")
    table.add_column(justify="left")
    
    table.add_row(
        "[bold cyan]Chat:[/bold cyan]",
        "[bold blue]demo_chat[/bold blue]",
        ""
    )
    
    table.add_row(
        "[bold cyan]Context:[/bold cyan]",
        "[bold green]75% free[/bold green]",
        "[dim](6,000/24,576 tokens)[/dim]"
    )
    
    table.add_row(
        "[bold cyan]Memory:[/bold cyan]",
        "[bold green]145.3 MB[/bold green]",
        ""
    )
    
    console.print(Panel(
        table,
        title="[bold cyan]Status[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()
    
    # Подсказки
    hints = Table.grid(padding=(0, 2))
    hints.add_column(style="cyan", justify="right")
    hints.add_column(style="white")
    
    hints.add_row("📝 Commands:", "/help - show all commands")
    hints.add_row("🔄 Switch mode:", "Ctrl+O - toggle chat/shell mode")
    hints.add_row("📊 Statistics:", "/memory - show memory stats")
    hints.add_row("🚪 Exit:", "exit or quit")
    
    console.print(Panel(
        hints,
        title="[bold cyan]Quick Start[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()


def demo_agent_thinking():
    """Демонстрация мысли агента"""
    console.print(Panel(
        "[yellow]Анализирую запрос и планирую создание файла с функцией приветствия[/yellow]",
        title="[bold cyan]💭 Agent Thinking[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()


def demo_action():
    """Демонстрация действия"""
    console.print("[bold magenta]🔧 Action:[/bold magenta] [bold cyan]write_file[/bold cyan](file_path='hello.py')")
    console.print()


def demo_code_preview():
    """Демонстрация предпросмотра кода"""
    console.rule("[bold cyan]Code Preview[/bold cyan]")
    console.print()
    
    console.print("[bold]File:[/bold] [cyan]hello.py[/cyan]")
    console.print("[bold]Lines:[/bold] 10")
    console.print()
    
    code = """def greet(name):
    \"\"\"Приветствует пользователя по имени\"\"\"
    print(f"Привет, {name}!")
    print("Добро пожаловать в Enhanced CLI!")

def main():
    greet("Пользователь")
    print("Это демонстрация новых возможностей")

if __name__ == "__main__":
    main()"""
    
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(Panel(
        syntax,
        title="[bold cyan]hello.py[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()


def demo_markdown_rendering():
    """Демонстрация улучшенного рендеринга Markdown"""
    md_content = """
# Результат Выполнения

Файл **hello.py** успешно создан! 

## Что было сделано:

1. Создана функция `greet(name)` для приветствия
2. Добавлена документация (docstring)
3. Реализован main() блок

## Пример использования:

```python
python hello.py
# Вывод:
# Привет, Пользователь!
# Добро пожаловать в Enhanced CLI!
# Это демонстрация новых возможностей
```

## Особенности:

- ✓ Понятный код
- ✓ Хорошая структура
- ✓ Готов к использованию

**Файл готов к использованию!** 🎉
"""
    
    console.print(Panel(
        Markdown(md_content),
        title="[bold green]✓ Final Answer[/bold green]",
        border_style="green",
        box=box.ROUNDED
    ))


def demo_tool_stats():
    """Демонстрация статистики инструментов"""
    console.print("\n[bold]Tool Statistics:[/bold]\n")
    
    table = Table(title="Tool Statistics", box=box.ROUNDED)
    table.add_column("Tool", style="cyan")
    table.add_column("Calls", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Time", justify="right")
    
    # Примеры данных
    table.add_row("write_file", "5", "[green]100.0%[/green]", "0.15s")
    table.add_row("read_file", "8", "[green]100.0%[/green]", "0.08s")
    table.add_row("internet_search", "3", "[yellow]66.7%[/yellow]", "2.34s")
    table.add_row("web_fetch", "2", "[green]100.0%[/green]", "1.82s")
    table.add_row("analyze_code", "1", "[green]100.0%[/green]", "0.92s")
    
    console.print(table)
    console.print()


def demo_status_colors():
    """Демонстрация цветовых индикаторов"""
    console.print("\n[bold]Цветовые Индикаторы Состояния:[/bold]\n")
    
    # Контекст
    context_table = Table(title="Context Usage", box=box.ROUNDED)
    context_table.add_column("State", style="bold")
    context_table.add_column("Free %", justify="right")
    context_table.add_column("Color")
    
    context_table.add_row("Healthy", "75%", "[bold green]🟢 Green[/bold green]")
    context_table.add_row("Warning", "35%", "[bold yellow]🟡 Yellow[/bold yellow]")
    context_table.add_row("Critical", "10%", "[bold red]🔴 Red[/bold red]")
    
    console.print(context_table)
    console.print()
    
    # Память
    memory_table = Table(title="Memory Usage", box=box.ROUNDED)
    memory_table.add_column("State", style="bold")
    memory_table.add_column("Usage", justify="right")
    memory_table.add_column("Color")
    
    memory_table.add_row("Healthy", "512 MB", "[bold green]🟢 Green[/bold green]")
    memory_table.add_row("Warning", "1.5 GB", "[bold yellow]🟡 Yellow[/bold yellow]")
    memory_table.add_row("Critical", "2.8 GB", "[bold red]🔴 Red[/bold red]")
    
    console.print(memory_table)
    console.print()


def demo_commands_help():
    """Демонстрация справки по командам"""
    help_content = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    help_content.add_column("Command", style="cyan", width=25)
    help_content.add_column("Description", style="white")
    
    # Команды управления чатами
    help_content.add_row("", "")
    help_content.add_row("[bold]Chat Management[/bold]", "")
    help_content.add_row("/new <name> [desc]", "Create new chat")
    help_content.add_row("/switch <name>", "Switch to chat")
    help_content.add_row("/list", "Show active chats")
    
    # Команды сохранения
    help_content.add_row("", "")
    help_content.add_row("[bold]Save/Load[/bold]", "")
    help_content.add_row("/save [desc]", "Save current chat")
    help_content.add_row("/load <name>", "Load chat from disk")
    help_content.add_row("/saved", "Show saved chats")
    help_content.add_row("/delete <name>", "Delete saved chat")
    
    # Команды памяти
    help_content.add_row("", "")
    help_content.add_row("[bold]Memory & Stats[/bold]", "")
    help_content.add_row("/memory", "Show memory statistics")
    help_content.add_row("/status", "Show detailed status")
    help_content.add_row("/stats", "Show session & tool stats")
    
    # Прочее
    help_content.add_row("", "")
    help_content.add_row("[bold]Other[/bold]", "")
    help_content.add_row("Ctrl+O", "Toggle chat/shell mode")
    help_content.add_row("exit, quit", "Exit program")
    
    console.print(Panel(
        help_content,
        title="[bold cyan]Available Commands[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    ))


def run_demo():
    """Запускает полную демонстрацию"""
    console.print("\n[bold green]🎬 Enhanced CLI Demo[/bold green]")
    console.print("[dim]Демонстрация улучшенного интерфейса командной строки[/dim]\n")
    
    input("Нажмите Enter для начала демонстрации...")
    
    # 1. Экран приветствия
    console.print("\n[bold cyan]1. Экран Приветствия[/bold cyan]")
    demo_welcome_screen()
    time.sleep(2)
    
    input("\nНажмите Enter для продолжения...")
    
    # 2. Мысль агента
    console.print("\n[bold cyan]2. Мысль Агента[/bold cyan]")
    demo_agent_thinking()
    time.sleep(1)
    
    # 3. Действие
    console.print("[bold cyan]3. Действие Агента[/bold cyan]")
    demo_action()
    time.sleep(1)
    
    input("Нажмите Enter для предпросмотра кода...")
    
    # 4. Предпросмотр кода
    console.print("\n[bold cyan]4. Предпросмотр Кода[/bold cyan]")
    demo_code_preview()
    time.sleep(2)
    
    input("Нажмите Enter для финального ответа...")
    
    # 5. Markdown рендеринг
    console.print("\n[bold cyan]5. Улучшенный Markdown[/bold cyan]")
    demo_markdown_rendering()
    time.sleep(2)
    
    input("\nНажмите Enter для цветовых индикаторов...")
    
    # 6. Цветовые индикаторы
    console.print("\n[bold cyan]6. Цветовые Индикаторы[/bold cyan]")
    demo_status_colors()
    time.sleep(2)
    
    input("\nНажмите Enter для статистики инструментов...")
    
    # 7. Статистика инструментов
    console.print("\n[bold cyan]7. Статистика Инструментов[/bold cyan]")
    demo_tool_stats()
    time.sleep(2)
    
    input("\nНажмите Enter для справки по командам...")
    
    # 8. Справка
    console.print("\n[bold cyan]8. Справка по Командам[/bold cyan]\n")
    demo_commands_help()
    
    console.print("\n[bold green]✓ Демонстрация завершена![/bold green]")
    console.print("\n[dim]Запустите enhanced_cli.py для полного опыта[/dim]\n")


if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Демонстрация прервана[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Ошибка: {e}[/red]")
