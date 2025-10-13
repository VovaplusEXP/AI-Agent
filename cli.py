import time
import os
import logging
import subprocess
from pathlib import Path
from agent import Agent

from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings

# --- КОНФИГУРАЯ ---
MODEL_PATH = "/home/vova/AI/ai/gemma-3n-E4B-it-IQ4_XS.gguf"
HISTORY_FILE = ".chat_history"
CHATS_DIR = "chats"

class RichCLI:
    """
    Класс для создания интерактивного TUI с использованием rich и prompt_toolkit.
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
            "Переключение между режимом чата и оболочки"
            self.in_shell_mode = not self.in_shell_mode
            if self.in_shell_mode:
                self.console.print("\n[bold green]Переключено в режим оболочки. Введите 'exit' для возврата.[/bold green]")
            else:
                self.console.print("\n[bold blue]Переключено в режим чата.[/bold blue]")
            # Прерываем текущий prompt, чтобы цикл мог перерисовать его
            event.app.exit()

        self.session = PromptSession(history=FileHistory(str(history_path)), style=style, key_bindings=bindings)
        self.agent = Agent(model_path=model_path, chats_dir=chats_dir)

    def show_help(self):
        """Выводит красивую справку по командам."""
        help_text = """
[bold]Команды управления чатами:[/bold]
  [cyan]/new <имя> [описание][/cyan]  - Создать новый чат в памяти.
  [cyan]/switch <имя>[/cyan]           - Переключиться на чат (из памяти или загрузить с диска).
  [cyan]/list[/cyan]                   - Показать активные чаты в памяти.
  
[bold]Команды сохранения и загрузки:[/bold]
  [cyan]/save [описание][/cyan]        - Сохранить текущий чат на диск.
  [cyan]/load <имя>[/cyan]             - Загрузить чат с диска.
  [cyan]/saved[/cyan]                  - Показать список сохраненных чатов.
  [cyan]/delete <имя>[/cyan]           - Удалить сохраненный чат с диска.

[bold]Команды памяти:[/bold]
  [cyan]/memory[/cyan]                 - Показать статистику памяти.

[bold]Прочее:[/bold]
  [cyan]/help[/cyan]                   - Показать это сообщение.
  [cyan]Ctrl+O[/cyan]                  - Переключить режим чат/оболочка.
  [yellow]exit, quit[/yellow]          - Выйти из программы.
        """
        self.console.print(Panel(help_text, title="Справка", border_style="green"))

    def handle_command(self, user_input: str):
        """Обрабатывает команды, введенные пользователем."""
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
            
        elif command == '/help':
            self.show_help()
            
        else:
            self.console.print(f"[red]Неизвестная команда или неверный аргумент. Введите /help.[/red]")

    def handle_shell_command(self, command: str):
        """Выполняет команду оболочки."""
        if command.lower() == 'exit':
            self.in_shell_mode = False
            self.console.print("[bold blue]Возврат в режим чата.[/bold blue]")
            return

        try:
            # Особая обработка для 'cd'
            if command.strip().startswith('cd '):
                path = command.strip().split(' ', 1)[1]
                os.chdir(path)
                output_msg = f"Изменена директория: {os.getcwd()}"
                self.console.print(f"[cyan]{output_msg}[/cyan]")
                
                # Добавляем результат в историю агента
                shell_context = f"[Shell Command] $ {command}\n{output_msg}"
                self.agent.histories[self.agent.current_chat].append({
                    "role": "user",
                    "content": f"Observation (Shell): {shell_context}"
                })
            else:
                # Выполнение других команд
                result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
                output = ""
                if result.stdout:
                    output += result.stdout.strip()
                    self.console.print(result.stdout.strip())
                if result.stderr:
                    stderr_msg = result.stderr.strip()
                    output += f"\n[stderr] {stderr_msg}"
                    self.console.print(f"[red]{stderr_msg}[/red]")
                
                # Добавляем результат в историю агента (ограничиваем до 500 символов)
                shell_context = f"[Shell Command] $ {command}\n{output[:500]}"
                if len(output) > 500:
                    shell_context += "\n... (вывод обрезан)"
                
                self.agent.histories[self.agent.current_chat].append({
                    "role": "user", 
                    "content": f"Observation (Shell): {shell_context}"
                })
                
        except FileNotFoundError:
            error_msg = f"Ошибка: Директория не найдена '{path}'"
            self.console.print(f"[red]{error_msg}[/red]")
            # Добавляем ошибку в историю
            self.agent.histories[self.agent.current_chat].append({
                "role": "user",
                "content": f"Observation (Shell): [Error] {error_msg}"
            })
        except Exception as e:
            error_msg = f"Ошибка выполнения команды: {e}"
            self.console.print(f"[bold red]{error_msg}[/bold red]")
            # Добавляем ошибку в историю
            self.agent.histories[self.agent.current_chat].append({
                "role": "user",
                "content": f"Observation (Shell): [Error] {error_msg}"
            })

    def run(self):
        self.console.print("\n[bold green]Начинаем интерактивный чат.[/bold green]")
        self.console.print("Нажмите [cyan]Ctrl+O[/cyan] для переключения в режим оболочки.")
        self.console.print("Введите [cyan]/help[/cyan] для списка команд или '[yellow]exit[/yellow]' для выхода.")
        self.console.rule()
        
        auto_approve = False

        try:
            while True:
                if self.in_shell_mode:
                    prompt_parts = [
                        ('class:prompt.shell', '[Оболочка] '),
                        ('class:prompt.path', f'{os.getcwd()}'),
                        ('', ' $ '),
                    ]
                    user_input = self.session.prompt(prompt_parts)
                    if user_input is None:  # Происходит при прерывании prompt через Ctrl+O
                        continue
                    self.handle_shell_command(user_input)
                    continue

                # Режим чата
                prompt_parts = [
                    ('class:prompt.bracket', '['),
                    ('class:prompt.chat_name', self.agent.current_chat),
                    ('class:prompt.bracket', ']'),
                    ('', ' Вы: '),
                ]
                user_input = self.session.prompt(prompt_parts)
                if user_input is None:  # Происходит при прерывании prompt через Ctrl+O
                    continue

                if user_input.lower() in ["exit", "quit", "выход"]:
                    self.console.print("[bold yellow]Завершение диалога.[/bold yellow]")
                    break

                if user_input.startswith('/'):
                    self.handle_command(user_input)
                    continue

                # --- Запуск и обработка цикла ReAct ---
                agent_generator = self.agent.run_cycle(user_input)
                
                try:
                    # Получаем самый первый шаг от агента
                    agent_step = next(agent_generator)

                    while True:
                        thought = agent_step['thought']
                        action = agent_step['action']
                        tool_name = action.get("tool_name")
                        parameters = action.get("parameters", {})

                        self.console.print(Panel(f"[yellow]Мысль:[/yellow] {thought}", title="План агента", border_style="yellow"))

                        action_str = f"[bold cyan]{tool_name}[/bold cyan]({', '.join([f'{k}={v!r}' for k, v in parameters.items()])})"
                        self.console.print(f"[bold magenta]Действие:[/bold magenta] {action_str}")

                        if tool_name == "finish":
                            final_answer = parameters.get("final_answer", "Задача выполнена.")
                            self.console.print(Panel(Markdown(final_answer), title="Финальный ответ", border_style="green"))
                            # Для finish НЕ отправляем сигнал, просто завершаем
                            break  # Выходим из цикла while
                        else:
                            should_proceed = False
                            user_choice = ''

                            if auto_approve:
                                self.console.print("[dim]Выполнение (автоматическое подтверждение)...[/dim]")
                                should_proceed = True
                            else:
                                user_choice = self.session.prompt("Выполнить это действие? ([Y]es/[N]o/[A]lways) ", default="y").lower()
                                if user_choice in ['y', 'yes', 'д']:
                                    should_proceed = True
                                elif user_choice in ['a', 'always', 'всегда']:
                                    auto_approve = True
                                    should_proceed = True

                        # --- Отправка сигнала и получение СЛЕДУЮЩЕГО шага ---
                        if should_proceed:
                            agent_step = agent_generator.send(True)
                        else:
                            agent_step = agent_generator.send(False)
                            self.console.print("[red]Действие отменено.[/red]")
                
                except StopIteration:
                    self.console.print("[yellow]Агент завершил работу или достиг лимита итераций.[/yellow]")
                
                self.console.rule()

        except KeyboardInterrupt:
            self.console.print("\n\n[bold yellow]Перехвачено прерывание. Завершение программы.[/bold yellow]")
        except Exception as e:
            logging.critical("Произошла критическая ошибка в главном цикле CLI.", exc_info=True)
            self.console.print(f"\n[bold red]Произошла критическая ошибка (подробности в agent.log):[/bold red] {e}")
        finally:
            # --- Сохранение памяти при выходе ---
            try:
                self.console.print("\n[bold blue]Сохранение памяти агента...[/bold blue]")
                self.agent.memory_manager.save_all()
                self.console.print("[bold green]Память успешно сохранена.[/bold green]")
            except Exception as e:
                self.console.print(f"[bold red]Ошибка при сохранении памяти: {e}[/bold red]")
                logging.error(f"Ошибка при сохранении памяти: {e}", exc_info=True)

def main():
    """Главная функция для запуска CLI."""
    try:
        cli = RichCLI(model_path=MODEL_PATH, chats_dir=CHATS_DIR)
        cli.run()
    except Exception as e:
        logging.critical("Ошибка при инициализации агента.", exc_info=True)
        print(f"Ошибка при инициализации агента (подробности в agent.log): {e}")

if __name__ == "__main__":
    main()
