"""
Enhanced CLI for AI Agent with improved UX inspired by google-gemini/gemini-cli
Features:
- Real-time context usage display (% free)
- Memory usage monitoring (RAM)
- Enhanced Markdown rendering with code highlighting
- Code preview before file operations
- Beautiful status bar with gradient effects
- Improved layout and visual feedback
"""
import os
import sys
import logging
import subprocess
import psutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.syntax import Syntax
from rich.align import Align
from rich.text import Text
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings

from agent import Agent

# --- КОНФИГУРАЦИЯ ---
MODEL_PATH = "/home/vova/AI/ai/gemma-3n-E4B-it-IQ4_XS.gguf"
HISTORY_FILE = ".chat_history"
CHATS_DIR = "chats"


class ToolStatsTracker:
    """Отслеживание статистики использования инструментов"""
    
    def __init__(self):
        self.tool_stats = {}  # {tool_name: {'count': int, 'success': int, 'total_time': float}}
        self.start_time = None
    
    def start_tool(self, tool_name: str):
        """Начать отслеживание вызова инструмента"""
        self.start_time = time.time()
    
    def end_tool(self, tool_name: str, success: bool):
        """Завершить отслеживание вызова инструмента"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = {'count': 0, 'success': 0, 'total_time': 0.0}
        
        self.tool_stats[tool_name]['count'] += 1
        if success:
            self.tool_stats[tool_name]['success'] += 1
        self.tool_stats[tool_name]['total_time'] += elapsed
        self.start_time = None
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Получить статистику по всем инструментам"""
        return self.tool_stats
    
    def render_stats(self, console: Console):
        """Отобразить статистику инструментов"""
        if not self.tool_stats:
            return
        
        table = Table(title="Tool Statistics", box=box.ROUNDED)
        table.add_column("Tool", style="cyan")
        table.add_column("Calls", justify="right")
        table.add_column("Success Rate", justify="right")
        table.add_column("Avg Time", justify="right")
        
        for tool_name, stats in sorted(self.tool_stats.items()):
            success_rate = (stats['success'] / stats['count'] * 100) if stats['count'] > 0 else 0
            avg_time = (stats['total_time'] / stats['count']) if stats['count'] > 0 else 0
            
            # Цветовая индикация success rate
            if success_rate >= 90:
                rate_color = "green"
            elif success_rate >= 70:
                rate_color = "yellow"
            else:
                rate_color = "red"
            
            table.add_row(
                tool_name,
                str(stats['count']),
                f"[{rate_color}]{success_rate:.1f}%[/{rate_color}]",
                f"{avg_time:.2f}s"
            )
        
        console.print(table)


class EnhancedStatusBar:
    """Улучшенная статус-панель с отображением контекста и памяти"""
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self.console = Console()
        self.process = psutil.Process(os.getpid())
        
    def get_context_usage(self) -> tuple[int, int, float]:
        """Получает использование контекста (используемые токены, максимум, процент свободного)"""
        context_mgr = self.agent.context_manager
        
        # Получаем последнюю статистику из контекст менеджера
        # Подсчитываем текущее использование токенов
        current_tokens = 0
        if hasattr(self.agent, 'last_context_stats'):
            stats = self.agent.last_context_stats
            current_tokens = stats.get('total_tokens', 0)
        
        max_tokens = context_mgr.max_tokens
        free_percent = ((max_tokens - current_tokens) / max_tokens * 100) if max_tokens > 0 else 0
        
        return current_tokens, max_tokens, free_percent
    
    def get_memory_usage(self) -> tuple[float, str]:
        """Получает использование памяти (в МБ и форматированная строка)"""
        mem_info = self.process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024
        
        if mem_mb < 1024:
            mem_str = f"{mem_mb:.1f} MB"
        else:
            mem_str = f"{mem_mb/1024:.2f} GB"
        
        return mem_mb, mem_str
    
    def render(self) -> Panel:
        """Рендерит статус-панель"""
        # Получаем данные
        current_tokens, max_tokens, free_percent = self.get_context_usage()
        mem_mb, mem_str = self.get_memory_usage()
        
        # Выбираем цвет для контекста
        if free_percent > 50:
            context_color = "green"
        elif free_percent > 20:
            context_color = "yellow"
        else:
            context_color = "red"
        
        # Выбираем цвет для памяти
        if mem_mb < 1024:
            mem_color = "green"
        elif mem_mb < 2048:
            mem_color = "yellow"
        else:
            mem_color = "red"
        
        # Создаем таблицу со статистикой
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left")
        table.add_column(justify="left")
        table.add_column(justify="left")
        
        # Добавляем информацию
        table.add_row(
            Text("Chat:", style="bold cyan"),
            Text(self.agent.current_chat, style="bold blue"),
            ""
        )
        
        table.add_row(
            Text("Context:", style="bold cyan"),
            Text(f"{free_percent:.0f}% free", style=f"bold {context_color}"),
            Text(f"({current_tokens:,}/{max_tokens:,} tokens)", style="dim")
        )
        
        table.add_row(
            Text("Memory:", style="bold cyan"),
            Text(mem_str, style=f"bold {mem_color}"),
            ""
        )
        
        return Panel(
            table,
            title="[bold cyan]Status[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        )


class CodePreviewDialog:
    """Диалог предпросмотра кода перед записью в файл"""
    
    def __init__(self, console: Console, session: PromptSession):
        self.console = console
        self.session = session
    
    def show(self, file_path: str, content: str, language: str = "python") -> bool:
        """
        Показывает предпросмотр кода и запрашивает подтверждение
        
        Args:
            file_path: Путь к файлу
            content: Содержимое файла
            language: Язык для подсветки синтаксиса
            
        Returns:
            True если пользователь подтвердил, False иначе
        """
        self.console.print()
        self.console.rule("[bold cyan]Code Preview[/bold cyan]")
        self.console.print()
        
        # Показываем путь к файлу
        self.console.print(f"[bold]File:[/bold] [cyan]{file_path}[/cyan]")
        self.console.print(f"[bold]Lines:[/bold] {len(content.splitlines())}")
        self.console.print()
        
        # Показываем код с подсветкой синтаксиса
        syntax = Syntax(content, language, theme="monokai", line_numbers=True)
        self.console.print(Panel(
            syntax,
            title=f"[bold cyan]{os.path.basename(file_path)}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        
        self.console.print()
        
        # Запрашиваем подтверждение
        try:
            response = self.session.prompt(
                "Write this file? ([Y]es/[N]o/[E]dit path) ",
                default="y"
            ).lower()
            
            if response in ['y', 'yes', 'д', 'да']:
                return True
            elif response in ['e', 'edit', 'р', 'редактировать']:
                new_path = self.session.prompt("Enter new file path: ", default=file_path)
                return new_path  # Возвращаем новый путь
            else:
                return False
        except KeyboardInterrupt:
            return False


class EnhancedCLI:
    """
    Улучшенный CLI с вдохновением от gemini-cli
    """
    
    def __init__(self, model_path: str, chats_dir: str):
        self.console = Console()
        self.in_shell_mode = False
        
        home = Path.home()
        history_path = home / HISTORY_FILE
        
        style = Style.from_dict({
            'prompt.bracket': 'bold fg:blue',
            'prompt.chat_name': 'bold fg:blue',
            'prompt.shell': 'bold fg:green',
            'prompt.path': 'fg:cyan',
        })
        
        # Настройка сочетания клавиш
        bindings = KeyBindings()
        @bindings.add('c-o')
        def _(event):
            """Переключение между режимом чата и оболочки"""
            self.in_shell_mode = not self.in_shell_mode
            if self.in_shell_mode:
                self.console.print("\n[bold green]Переключено в режим оболочки. Введите 'exit' для возврата.[/bold green]")
            else:
                self.console.print("\n[bold blue]Переключено в режим чата.[/bold blue]")
            event.app.exit()

        self.session = PromptSession(
            history=FileHistory(str(history_path)),
            style=style,
            key_bindings=bindings
        )
        self.agent = Agent(model_path=model_path, chats_dir=chats_dir)
        self.status_bar = EnhancedStatusBar(self.agent)
        self.code_preview = CodePreviewDialog(self.console, self.session)
        self.tool_tracker = ToolStatsTracker()
        
        # Для отслеживания последней статистики контекста
        self.agent.last_context_stats = {'total_tokens': 0}
        
        # Для отслеживания времени сессии
        self.session_start_time = time.time()

    def show_welcome(self):
        """Показывает красивый экран приветствия"""
        self.console.clear()
        
        # ASCII art logo (упрощенный)
        logo = """
╔═══════════════════════════════════════════╗
║                                           ║
║         🤖  AI Agent Enhanced CLI         ║
║                                           ║
║         Powered by Gemma-3n-E4B          ║
║                                           ║
╚═══════════════════════════════════════════╝
        """
        
        self.console.print(logo, style="bold cyan", justify="center")
        self.console.print()
        
        # Показываем статус-бар
        self.console.print(self.status_bar.render())
        self.console.print()
        
        # Подсказки
        hints = Table.grid(padding=(0, 2))
        hints.add_column(style="cyan", justify="right")
        hints.add_column(style="white")
        
        hints.add_row("📝 Commands:", "/help - show all commands")
        hints.add_row("🔄 Switch mode:", "Ctrl+O - toggle chat/shell mode")
        hints.add_row("📊 Statistics:", "/memory - show memory stats")
        hints.add_row("🚪 Exit:", "exit or quit")
        
        self.console.print(Panel(
            hints,
            title="[bold cyan]Quick Start[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        self.console.print()

    def show_help(self):
        """Выводит красивую справку по командам"""
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
        
        # Команды памяти и статистики
        help_content.add_row("", "")
        help_content.add_row("[bold]Memory & Stats[/bold]", "")
        help_content.add_row("/memory", "Show memory statistics")
        help_content.add_row("/status", "Show detailed status")
        help_content.add_row("/stats", "Show session & tool statistics")
        
        # Прочее
        help_content.add_row("", "")
        help_content.add_row("[bold]Other[/bold]", "")
        help_content.add_row("Ctrl+O", "Toggle chat/shell mode")
        help_content.add_row("exit, quit", "Exit program")
        
        self.console.print(Panel(
            help_content,
            title="[bold cyan]Available Commands[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        ))

    def show_status(self):
        """Показывает детальный статус"""
        self.console.print(self.status_bar.render())
    
    def show_session_stats(self):
        """Показывает статистику сессии"""
        session_duration = time.time() - self.session_start_time
        
        # Создаем панель со статистикой сессии
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style="cyan", justify="right")
        stats_table.add_column(style="white")
        
        # Форматируем время
        hours = int(session_duration // 3600)
        minutes = int((session_duration % 3600) // 60)
        seconds = int(session_duration % 60)
        
        if hours > 0:
            duration_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{seconds}s"
        
        stats_table.add_row("Session Duration:", duration_str)
        stats_table.add_row("Current Chat:", self.agent.current_chat)
        
        # Получаем данные о контексте и памяти
        current_tokens, max_tokens, free_percent = self.status_bar.get_context_usage()
        mem_mb, mem_str = self.status_bar.get_memory_usage()
        
        stats_table.add_row("Context Usage:", f"{current_tokens:,}/{max_tokens:,} tokens ({free_percent:.0f}% free)")
        stats_table.add_row("Memory Usage:", mem_str)
        
        self.console.print(Panel(
            stats_table,
            title="[bold cyan]Session Statistics[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        
        # Показываем статистику инструментов, если есть
        if self.tool_tracker.tool_stats:
            self.console.print()
            self.tool_tracker.render_stats(self.console)

    def handle_command(self, user_input: str):
        """Обрабатывает команды пользователя"""
        parts = user_input.split(maxsplit=2)
        command = parts[0] if parts else ""
        arg1 = parts[1] if len(parts) > 1 else None
        arg2 = parts[2] if len(parts) > 2 else None

        if command == '/new' and arg1:
            description = arg2 if arg2 else ""
            result = self.agent.new_chat(arg1, description)
            self.console.print(f"[yellow]{result}[/yellow]")
            
        elif command == '/switch' and arg1:
            result = self.agent.switch_chat(arg1)
            self.console.print(f"[yellow]{result}[/yellow]")
            
        elif command == '/list':
            self.console.print(self.agent.list_chats())
            
        elif command == '/save':
            description = arg1 if arg1 else ""
            result = self.agent.save_current_chat(description)
            self.console.print(f"[yellow]{result}[/yellow]")
            
        elif command == '/load' and arg1:
            result = self.agent.load_chat(arg1)
            self.console.print(f"[yellow]{result}[/yellow]")
            
        elif command == '/saved':
            self.console.print(self.agent.list_saved_chats())
            
        elif command == '/delete' and arg1:
            result = self.agent.delete_saved_chat(arg1)
            self.console.print(f"[yellow]{result}[/yellow]")
            
        elif command == '/memory':
            self.console.print(self.agent.get_memory_stats())
            
        elif command == '/status':
            self.show_status()
        
        elif command == '/stats':
            self.show_session_stats()
            
        elif command == '/help':
            self.show_help()
            
        else:
            self.console.print("[red]Unknown command. Type /help for available commands.[/red]")

    def handle_shell_command(self, command: str):
        """Выполняет команду оболочки"""
        if command.lower() == 'exit':
            self.in_shell_mode = False
            self.console.print("[bold blue]Returning to chat mode.[/bold blue]")
            return

        try:
            if command.strip().startswith('cd '):
                path = command.strip().split(' ', 1)[1]
                os.chdir(path)
                output_msg = f"Changed directory: {os.getcwd()}"
                self.console.print(f"[cyan]{output_msg}[/cyan]")
                
                shell_context = f"[Shell Command] $ {command}\n{output_msg}"
                self.agent.histories[self.agent.current_chat].append({
                    "role": "user",
                    "content": f"Observation (Shell): {shell_context}"
                })
            else:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
                output = ""
                if result.stdout:
                    output += result.stdout.strip()
                    self.console.print(result.stdout.strip())
                if result.stderr:
                    stderr_msg = result.stderr.strip()
                    output += f"\n[stderr] {stderr_msg}"
                    self.console.print(f"[red]{stderr_msg}[/red]")
                
                shell_context = f"[Shell Command] $ {command}\n{output[:500]}"
                if len(output) > 500:
                    shell_context += "\n... (output truncated)"
                
                self.agent.histories[self.agent.current_chat].append({
                    "role": "user", 
                    "content": f"Observation (Shell): {shell_context}"
                })
                
        except FileNotFoundError:
            error_msg = f"Error: Directory not found '{path}'"
            self.console.print(f"[red]{error_msg}[/red]")
            self.agent.histories[self.agent.current_chat].append({
                "role": "user",
                "content": f"Observation (Shell): [Error] {error_msg}"
            })
        except Exception as e:
            error_msg = f"Error executing command: {e}"
            self.console.print(f"[bold red]{error_msg}[/bold red]")
            self.agent.histories[self.agent.current_chat].append({
                "role": "user",
                "content": f"Observation (Shell): [Error] {error_msg}"
            })

    def run(self):
        """Основной цикл CLI"""
        self.show_welcome()
        
        auto_approve = False

        try:
            while True:
                # Периодически обновляем статус-бар в промпте
                if self.in_shell_mode:
                    prompt_parts = [
                        ('class:prompt.shell', '[Shell] '),
                        ('class:prompt.path', f'{os.getcwd()}'),
                        ('', ' $ '),
                    ]
                    user_input = self.session.prompt(prompt_parts)
                    if user_input is None:
                        continue
                    self.handle_shell_command(user_input)
                    continue

                # Режим чата
                prompt_parts = [
                    ('class:prompt.bracket', '['),
                    ('class:prompt.chat_name', self.agent.current_chat),
                    ('class:prompt.bracket', ']'),
                    ('', ' You: '),
                ]
                user_input = self.session.prompt(prompt_parts)
                if user_input is None:
                    continue

                if user_input.lower() in ["exit", "quit", "выход"]:
                    self.console.print("[bold yellow]Exiting...[/bold yellow]")
                    break

                if user_input.startswith('/'):
                    self.handle_command(user_input)
                    continue

                # --- Запуск цикла ReAct ---
                agent_generator = self.agent.run_cycle(user_input)
                
                try:
                    # Показываем spinner во время ожидания первого ответа
                    with self.console.status("[cyan]Agent thinking...[/cyan]", spinner="dots") as status:
                        agent_step = next(agent_generator)

                    while True:
                        thought = agent_step['thought']
                        action = agent_step['action']
                        tool_name = action.get("tool_name")
                        parameters = action.get("parameters", {})

                        # Красивое отображение мысли агента
                        self.console.print(Panel(
                            f"[yellow]{thought}[/yellow]",
                            title="[bold cyan]💭 Agent Thinking[/bold cyan]",
                            border_style="cyan",
                            box=box.ROUNDED
                        ))

                        # Красивое отображение действия
                        action_str = f"[bold cyan]{tool_name}[/bold cyan]"
                        if parameters:
                            params_str = ', '.join([f'{k}={v!r}' for k, v in parameters.items()])
                            action_str += f"({params_str})"
                        
                        self.console.print(f"[bold magenta]🔧 Action:[/bold magenta] {action_str}")

                        if tool_name == "finish":
                            final_answer = parameters.get("final_answer", "Task completed.")
                            self.console.print(Panel(
                                Markdown(final_answer),
                                title="[bold green]✓ Final Answer[/bold green]",
                                border_style="green",
                                box=box.ROUNDED
                            ))
                            break
                        
                        # Специальная обработка для write_file и create_file с предпросмотром
                        if tool_name in ["write_file", "create_file"] and "content" in parameters:
                            file_path = parameters.get("file_path", "unknown")
                            content = parameters.get("content", "")
                            
                            # Определяем язык по расширению файла
                            ext = os.path.splitext(file_path)[1].lstrip('.')
                            language = ext if ext else "text"
                            
                            # Показываем предпросмотр
                            result = self.code_preview.show(file_path, content, language)
                            
                            if isinstance(result, str):  # Пользователь изменил путь
                                parameters["file_path"] = result
                                should_proceed = True
                            elif result:
                                should_proceed = True
                            else:
                                should_proceed = False
                                self.console.print("[red]✗ File write cancelled[/red]")
                        else:
                            should_proceed = False
                            user_choice = ''

                            if auto_approve:
                                self.console.print("[dim]Executing (auto-approved)...[/dim]")
                                should_proceed = True
                            else:
                                user_choice = self.session.prompt(
                                    "Execute this action? ([Y]es/[N]o/[A]lways) ",
                                    default="y"
                                ).lower()
                                if user_choice in ['y', 'yes', 'д']:
                                    should_proceed = True
                                elif user_choice in ['a', 'always', 'всегда']:
                                    auto_approve = True
                                    should_proceed = True

                        # Отправка сигнала и получение следующего шага
                        if should_proceed:
                            # Начинаем отслеживание времени выполнения инструмента
                            self.tool_tracker.start_tool(tool_name)
                            
                            # Показываем spinner во время выполнения
                            with self.console.status(f"[cyan]Executing {tool_name}...[/cyan]", spinner="dots"):
                                agent_step = agent_generator.send(True)
                            
                            # Записываем результат (предполагаем успех, если нет исключения)
                            self.tool_tracker.end_tool(tool_name, True)
                        else:
                            agent_step = agent_generator.send(False)
                            self.console.print("[red]✗ Action cancelled[/red]")
                
                except StopIteration:
                    self.console.print("[yellow]Agent completed or reached iteration limit.[/yellow]")
                
                # Обновляем статистику контекста после цикла
                if hasattr(self.agent.context_manager, 'last_build_stats'):
                    self.agent.last_context_stats = self.agent.context_manager.last_build_stats
                
                self.console.rule(style="dim")

        except KeyboardInterrupt:
            self.console.print("\n\n[bold yellow]Interrupted. Exiting...[/bold yellow]")
        except Exception as e:
            logging.critical("Critical error in main CLI loop.", exc_info=True)
            self.console.print(f"\n[bold red]Critical error (see agent.log):[/bold red] {e}")
        finally:
            # Сохранение памяти при выходе
            try:
                self.console.print("\n[bold blue]Saving agent memory...[/bold blue]")
                self.agent.memory_manager.save_all()
                self.console.print("[bold green]Memory saved successfully.[/bold green]")
            except Exception as e:
                self.console.print(f"[bold red]Error saving memory: {e}[/bold red]")
                logging.error(f"Error saving memory: {e}", exc_info=True)


def main():
    """Главная функция для запуска Enhanced CLI"""
    try:
        cli = EnhancedCLI(model_path=MODEL_PATH, chats_dir=CHATS_DIR)
        cli.run()
    except Exception as e:
        logging.critical("Error initializing agent.", exc_info=True)
        print(f"Error initializing agent (see agent.log): {e}")


if __name__ == "__main__":
    main()
