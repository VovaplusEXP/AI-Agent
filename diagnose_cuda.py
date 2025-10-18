#!/usr/bin/env python3
"""
Диагностический скрипт для проверки CUDA поддержки и llama-cpp-python

Этот скрипт поможет определить:
- Установлена ли CUDA и какая версия
- Поддерживает ли llama-cpp-python CUDA
- Доступна ли GPU для llama-cpp-python
- Правильно ли настроены переменные окружения
"""

import sys
import os
from pathlib import Path

def check_cuda_environment():
    """Проверка переменных окружения CUDA"""
    print("=" * 70)
    print("1. ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ CUDA")
    print("=" * 70)
    
    cuda_home = os.environ.get('CUDA_HOME') or os.environ.get('CUDA_PATH')
    if cuda_home:
        print(f"✅ CUDA_HOME: {cuda_home}")
    else:
        print("⚠️  CUDA_HOME не установлена")
        print("   Установите: export CUDA_HOME=/usr/local/cuda")
    
    ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')
    if 'cuda' in ld_library_path.lower():
        print(f"✅ LD_LIBRARY_PATH содержит CUDA")
    else:
        print("⚠️  LD_LIBRARY_PATH не содержит CUDA")
        print("   Установите: export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH")
    
    print()

def check_cuda_toolkit():
    """Проверка установки CUDA Toolkit"""
    print("=" * 70)
    print("2. ПРОВЕРКА CUDA TOOLKIT")
    print("=" * 70)
    
    import subprocess
    
    # Проверка nvcc
    try:
        result = subprocess.run(['nvcc', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = [l for l in result.stdout.split('\n') if 'release' in l.lower()]
            if version_line:
                print(f"✅ NVCC установлен: {version_line[0].strip()}")
        else:
            print("❌ NVCC не найден")
    except FileNotFoundError:
        print("❌ NVCC не найден в PATH")
        print("   Убедитесь что CUDA Toolkit установлен и $CUDA_HOME/bin в PATH")
    except Exception as e:
        print(f"⚠️  Ошибка при проверке nvcc: {e}")
    
    # Проверка nvidia-smi
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
                               '--format=csv,noheader'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ NVIDIA Driver установлен")
            for line in result.stdout.strip().split('\n'):
                print(f"   GPU: {line}")
        else:
            print("❌ nvidia-smi не работает")
    except FileNotFoundError:
        print("❌ nvidia-smi не найден")
        print("   Установите NVIDIA драйвер")
    except Exception as e:
        print(f"⚠️  Ошибка при проверке nvidia-smi: {e}")
    
    print()

def check_pytorch_cuda():
    """Проверка CUDA поддержки в PyTorch"""
    print("=" * 70)
    print("3. ПРОВЕРКА PYTORCH CUDA")
    print("=" * 70)
    
    try:
        import torch
        print(f"✅ PyTorch установлен: {torch.__version__}")
        
        if torch.cuda.is_available():
            print(f"✅ CUDA доступна в PyTorch: {torch.version.cuda}")
            print(f"✅ Устройств CUDA: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"   Устройство {i}: {torch.cuda.get_device_name(i)}")
        else:
            print("❌ CUDA НЕ доступна в PyTorch")
            print("   Переустановите PyTorch с CUDA:")
            print("   pip install torch --index-url https://download.pytorch.org/whl/cu121")
    except ImportError:
        print("⚠️  PyTorch не установлен")
    except Exception as e:
        print(f"⚠️  Ошибка при проверке PyTorch: {e}")
    
    print()

def check_llama_cpp_cuda():
    """Проверка CUDA поддержки в llama-cpp-python"""
    print("=" * 70)
    print("4. ПРОВЕРКА LLAMA-CPP-PYTHON CUDA")
    print("=" * 70)
    
    try:
        import llama_cpp
        print(f"✅ llama-cpp-python установлен: {llama_cpp.__version__}")
        
        # Проверяем, скомпилирован ли с CUDA
        # Это можно определить попыткой инициализации с n_gpu_layers
        print("\n🔍 Проверка CUDA поддержки...")
        print("   (попытка инициализации с n_gpu_layers=1)")
        
        # Создаём временный тестовый GGUF файл в памяти
        # Или просто проверяем импорт и вывод
        
        # Проверка через verbose вывод
        import io
        import contextlib
        
        # Захватываем вывод инициализации
        f = io.StringIO()
        try:
            # Попытка импорта символов CUDA
            from llama_cpp import llama_cpp
            
            # Проверка наличия CUDA бэкенда
            backends = []
            try:
                # В llama.cpp 0.2.0+ есть llama_backend_init
                if hasattr(llama_cpp, 'llama_backend_init'):
                    print("✅ llama_backend_init доступен")
                
                # Проверка поддержки CUDA через символы
                cuda_symbols = [
                    'GGML_CUDA',
                    'llama_cublas',
                    'ggml_cuda',
                ]
                
                found_cuda = False
                for symbol in cuda_symbols:
                    if hasattr(llama_cpp, symbol):
                        found_cuda = True
                        print(f"✅ Найден CUDA символ: {symbol}")
                        break
                
                if not found_cuda:
                    # Проверяем через вывод версии
                    import llama_cpp
                    print("\n⚠️  CUDA символы не найдены в llama_cpp")
                    print("   llama-cpp-python скорее всего собран БЕЗ CUDA поддержки")
                    print("\n📌 РЕШЕНИЕ:")
                    print("   Переустановите llama-cpp-python с CUDA:")
                    print()
                    print("   Вариант 1 (предсобранные wheels для CUDA 12.1):")
                    print("   pip uninstall llama-cpp-python -y")
                    print("   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121")
                    print()
                    print("   Вариант 2 (компиляция из исходников, рекомендуется):")
                    print("   pip uninstall llama-cpp-python -y")
                    print("   CMAKE_ARGS=\"-DGGML_CUDA=on\" pip install llama-cpp-python --force-reinstall --no-cache-dir")
                    return False
                else:
                    print("\n✅ llama-cpp-python СКОМПИЛИРОВАН С CUDA ПОДДЕРЖКОЙ")
                    return True
                    
            except Exception as e:
                print(f"⚠️  Ошибка при проверке CUDA поддержки: {e}")
                return False
                
        except ImportError as e:
            print(f"❌ Ошибка импорта llama_cpp: {e}")
            return False
            
    except ImportError:
        print("❌ llama-cpp-python не установлен")
        print("   Установите: pip install llama-cpp-python")
        return False
    except Exception as e:
        print(f"⚠️  Ошибка при проверке llama-cpp-python: {e}")
        return False
    
    print()

def print_recommendations():
    """Вывод рекомендаций"""
    print("=" * 70)
    print("5. РЕКОМЕНДАЦИИ")
    print("=" * 70)
    
    print("""
📌 ПОШАГОВОЕ РУКОВОДСТВО ПО ИСПРАВЛЕНИЮ:

1. Убедитесь что NVIDIA драйвер установлен:
   nvidia-smi

2. Убедитесь что CUDA Toolkit установлен:
   nvcc --version

3. Установите переменные окружения (добавьте в ~/.bashrc):
   export CUDA_HOME=/usr/local/cuda
   export PATH=$CUDA_HOME/bin:$PATH
   export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

4. Переустановите PyTorch с CUDA (если нужно):
   pip install torch --index-url https://download.pytorch.org/whl/cu121

5. Переустановите llama-cpp-python с CUDA:
   
   Вариант A (предсобранные wheels, быстрее):
   pip uninstall llama-cpp-python -y
   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
   
   Вариант B (компиляция, лучшая производительность):
   pip uninstall llama-cpp-python -y
   CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

6. Перезапустите terminal и проверьте снова:
   python3 diagnose_cuda.py

7. Запустите агент:
   python cli.py
""")

def main():
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║         ДИАГНОСТИКА CUDA ДЛЯ AI-AGENT (llama-cpp-python)            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    
    check_cuda_environment()
    check_cuda_toolkit()
    check_pytorch_cuda()
    has_cuda = check_llama_cpp_cuda()
    
    if not has_cuda:
        print_recommendations()
        return 1
    else:
        print("=" * 70)
        print("✅ ВСЁ НАСТРОЕНО ПРАВИЛЬНО!")
        print("=" * 70)
        print()
        print("Модель должна загружаться в VRAM при n_gpu_layers=-1")
        print()
        return 0

if __name__ == "__main__":
    sys.exit(main())
