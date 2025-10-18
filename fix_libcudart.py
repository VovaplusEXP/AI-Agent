#!/usr/bin/env python3
"""
Быстрое исправление для ошибки: libcudart.so.12: cannot open shared object file

Этот скрипт автоматически найдет CUDA библиотеки и подскажет как установить LD_LIBRARY_PATH
"""

import os
import sys
import glob
import subprocess

def find_cuda_libraries():
    """Поиск CUDA библиотек в системе"""
    print("🔍 Поиск CUDA библиотек...")
    print()
    
    # Возможные пути к CUDA
    search_paths = [
        '/usr/local/cuda*/targets/*/lib',  # Новый формат CUDA 13.x
        '/usr/local/cuda*/lib64',
        '/usr/local/cuda*/lib',
        '/usr/lib/x86_64-linux-gnu',
        '/usr/lib64',
        '/opt/cuda*/lib64',
        '/opt/cuda*/targets/*/lib',
    ]
    
    found_libs = {}
    
    for pattern in search_paths:
        paths = glob.glob(pattern)
        for path in paths:
            if os.path.isdir(path):
                # Ищем libcudart.so*
                cudart_files = glob.glob(os.path.join(path, 'libcudart.so*'))
                if cudart_files:
                    version = "unknown"
                    for f in cudart_files:
                        if 'libcudart.so.13' in f:
                            version = "13.x"
                            break
                        elif 'libcudart.so.12' in f:
                            version = "12.x"
                            break
                        elif 'libcudart.so.11' in f:
                            version = "11.x"
                            break
                    found_libs[path] = {
                        'files': cudart_files,
                        'version': version
                    }
    
    return found_libs

def check_current_ld_library_path():
    """Проверка текущего LD_LIBRARY_PATH"""
    ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    if ld_path:
        print(f"📌 Текущий LD_LIBRARY_PATH: {ld_path}")
        return ld_path.split(':')
    else:
        print("⚠️  LD_LIBRARY_PATH не установлена")
        return []

def generate_fix_commands(cuda_paths):
    """Генерация команд для исправления"""
    print()
    print("=" * 70)
    print("🔧 РЕШЕНИЕ")
    print("=" * 70)
    print()
    
    if not cuda_paths:
        print("❌ CUDA библиотеки не найдены в системе")
        print()
        print("Установите CUDA Toolkit:")
        print("  https://developer.nvidia.com/cuda-downloads")
        return
    
    # Выбираем лучший путь (самую новую версию)
    best_path = None
    best_version = None
    for path, info in cuda_paths.items():
        if info['version'] == '13.x':
            best_path = path
            best_version = '13.x'
            break
        elif info['version'] == '12.x' and not best_path:
            best_path = path
            best_version = '12.x'
    
    if not best_path:
        best_path = list(cuda_paths.keys())[0]
        best_version = cuda_paths[best_path]['version']
    
    print(f"✅ Найдена CUDA библиотека: {best_path}")
    print(f"   Версия: {best_version}")
    print()
    
    # Проверяем на несоответствие версий
    if best_version == '13.x':
        print("⚠️  ВАЖНО: У вас CUDA 13.x, но llama-cpp-python может ожидать CUDA 12.x!")
        print("   Это может вызвать ошибку 'libcudart.so.12: cannot open shared object file'")
        print()
        print("📝 Два варианта решения:")
        print()
        print("Вариант 1: Создать симлинк для совместимости")
        print()
        print(f"   sudo ln -s {best_path}/libcudart.so.13 {best_path}/libcudart.so.12")
        print(f"   export LD_LIBRARY_PATH={best_path}:$LD_LIBRARY_PATH")
        print()
        print("Вариант 2: Переустановить llama-cpp-python из исходников")
        print()
        print("   pip uninstall llama-cpp-python -y")
        print("   CMAKE_ARGS=\"-DGGML_CUDA=on\" pip install llama-cpp-python --force-reinstall --no-cache-dir")
        print()
    
    # Определяем shell
    shell = os.environ.get('SHELL', '/bin/bash')
    if 'zsh' in shell:
        rc_file = '~/.zshrc'
    else:
        rc_file = '~/.bashrc'
    
    print("📝 Выполните следующие команды:")
    print()
    print("1. Добавьте в", rc_file, ":")
    print()
    print(f"   echo 'export LD_LIBRARY_PATH={best_path}:$LD_LIBRARY_PATH' >> {rc_file}")
    print()
    print("2. Примените изменения:")
    print()
    print(f"   source {rc_file}")
    print()
    print("3. Или временно (только для текущей сессии):")
    print()
    print(f"   export LD_LIBRARY_PATH={best_path}:$LD_LIBRARY_PATH")
    print()
    print("4. Проверьте:")
    print()
    print("   python3 cli.py")
    print()
    
    # Также показываем альтернативные пути
    if len(cuda_paths) > 1:
        print("📌 Альтернативные пути CUDA (если первый не работает):")
        for path, info in cuda_paths.items():
            if path != best_path:
                print(f"   {path} (версия {info['version']})")
        print()

def main():
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║   БЫСТРОЕ ИСПРАВЛЕНИЕ: libcudart.so.12: cannot open shared object   ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Проверяем текущий LD_LIBRARY_PATH
    current_paths = check_current_ld_library_path()
    print()
    
    # Ищем CUDA библиотеки
    cuda_paths = find_cuda_libraries()
    
    if cuda_paths:
        print(f"✅ Найдено путей с CUDA: {len(cuda_paths)}")
        for path, info in cuda_paths.items():
            print(f"   • {path} (версия {info['version']})")
    else:
        print("❌ CUDA библиотеки не найдены")
    
    # Генерируем команды для исправления
    generate_fix_commands(cuda_paths)
    
    print("=" * 70)
    print("💡 СОВЕТ")
    print("=" * 70)
    print()
    print("После установки LD_LIBRARY_PATH проблема должна исчезнуть.")
    print("Если проблема остается, запустите полную диагностику:")
    print()
    print("  python3 diagnose_cuda.py")
    print()

if __name__ == "__main__":
    main()
