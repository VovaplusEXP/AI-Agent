# Решение проблемы загрузки модели в RAM вместо VRAM

**Дата:** 2025-10-18  
**Версия:** v0.0.3-p5-alpha  
**Проблема:** Модель загружается в RAM вместо VRAM при использовании CUDA 12.x

---

## 🔴 Описание проблем

### Проблема 1: llama-cpp-python без CUDA

**Симптомы:**
- Модель загружается в RAM вместо VRAM
- Очень низкая скорость генерации (практически 0 токенов/сек)
- GPU не используется или используется минимально

**Причина:** llama-cpp-python установлен БЕЗ CUDA поддержки (CPU-only версия)

### Проблема 2: libcudart.so.12 не найдена

**Симптомы:**
```
OSError: libcudart.so.12: cannot open shared object file: No such file or directory
```

**Причина:** CUDA runtime библиотеки не в LD_LIBRARY_PATH, даже если llama-cpp-python с CUDA установлен правильно

---

## ✅ Решение

### Быстрое исправление для libcudart.so.12

Если вы видите ошибку `libcudart.so.12: cannot open shared object file`, запустите:

```bash
python3 fix_libcudart.py
```

Скрипт автоматически найдет CUDA библиотеки и подскажет команды для исправления.

**Ручное исправление:**

1. Найдите где находится libcudart.so:
```bash
find /usr/local -name "libcudart.so*" 2>/dev/null
find /usr/lib -name "libcudart.so*" 2>/dev/null
```

2. Добавьте найденный путь в LD_LIBRARY_PATH:
```bash
# Для CUDA 12.4 (пример)
export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH

# Или для стандартной установки
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

3. Добавьте в ~/.bashrc или ~/.zshrc для постоянного эффекта:
```bash
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### Полная диагностика

Запустите диагностический скрипт:

```bash
python3 diagnose_cuda.py
```

Скрипт проверит:
- ✅ CUDA runtime библиотеки (libcudart.so)
- ✅ Переменные окружения (LD_LIBRARY_PATH)
- ✅ CUDA Toolkit и NVIDIA драйвер
- ✅ PyTorch CUDA поддержку
- ✅ llama-cpp-python CUDA поддержку

### Шаг 1: Проверка CUDA

Убедитесь что CUDA установлена:

```bash
# Проверка NVIDIA драйвера
nvidia-smi

# Проверка CUDA Toolkit
nvcc --version
```

Если команды не работают - установите NVIDIA драйвер и CUDA Toolkit:
- [NVIDIA Driver Download](https://www.nvidia.com/download/index.aspx)
- [CUDA Toolkit Download](https://developer.nvidia.com/cuda-downloads)

### Шаг 3: Переустановка llama-cpp-python с CUDA

#### Вариант A: Предсобранные CUDA wheels (быстрее)

**Для CUDA 12.1:**
```bash
pip uninstall llama-cpp-python -y
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

**Для CUDA 11.8:**
```bash
pip uninstall llama-cpp-python -y
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu118
```

#### Вариант B: Компиляция из исходников (лучшая производительность)

```bash
pip uninstall llama-cpp-python -y
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

**Примечание:** Для компиляции нужны:
- CUDA Toolkit
- CMake: `sudo apt install cmake` или `brew install cmake`
- GCC/Clang компилятор

### Шаг 4: Проверка установки

Проверьте что CUDA поддержка включена:

```python
import llama_cpp
print("llama-cpp-python version:", llama_cpp.__version__)

# Попытка инициализации с GPU
from llama_cpp import Llama
llm = Llama(
    model_path="your_model.gguf",
    n_gpu_layers=1,  # Хотя бы 1 слой на GPU
    verbose=True     # Покажет где загружается модель
)
```

В verbose выводе должно быть:
```
llama_model_load: using CUDA ...
llama_kv_cache_init: CUDA ...
```

Если видите только CPU - llama-cpp-python всё ещё без CUDA.

### Шаг 5: Настройка переменных окружения

Добавьте в `~/.bashrc` или `~/.zshrc`:

```bash
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

Перезагрузите терминал:
```bash
source ~/.bashrc
```

---

## 🔍 Часто задаваемые вопросы

### Q: Ошибка "libcudart.so.12: cannot open shared object file"
A: Это означает что llama-cpp-python с CUDA установлен ПРАВИЛЬНО, но система не может найти CUDA runtime библиотеки.
   
   **Быстрое решение:**
   ```bash
   python3 fix_libcudart.py
   ```
   
   **Ручное решение:**
   ```bash
   # Найдите libcudart.so
   find /usr/local -name "libcudart.so*" 2>/dev/null
   
   # Добавьте путь в LD_LIBRARY_PATH
   export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH
   
   # Добавьте в ~/.bashrc для постоянного эффекта
   echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
   source ~/.bashrc
   ```

### Q: Почему в v0.0.1-alpha это работало?
A: Возможно, в v0.0.1-alpha был установлен правильный CUDA-версия llama-cpp-python,
   который потом был переустановлен (например, при обновлении зависимостей).

### Q: Помогут ли параметры offload_kqv, type_k, type_v?
A: НЕТ! Эти параметры работают только если llama-cpp-python собран с CUDA.
   Без CUDA поддержки никакие параметры не помогут использовать GPU.

### Q: Можно ли использовать PyTorch CUDA для llama-cpp-python?
A: НЕТ! llama-cpp-python - это C++ библиотека с Python биндингами.
   Она использует CUDA напрямую, а не через PyTorch.

### Q: Как проверить что проблема точно в llama-cpp-python?
A: Запустите `python3 diagnose_cuda.py` - скрипт точно определит проблему.

### Q: Я обновил CUDA до 12.x, что делать?
A: Переустановите llama-cpp-python с поддержкой CUDA 12.1:
   ```bash
   pip uninstall llama-cpp-python -y
   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
   ```

---

## 📊 Сравнение производительности

### CPU-only (без CUDA):
- Загрузка: Вся модель в RAM
- Скорость: ~0.1-1 токен/сек (очень медленно)
- Память: Высокое использование RAM
- GPU: Не используется

### С CUDA (правильная установка):
- Загрузка: Модель в VRAM
- Скорость: ~10-50 токенов/сек (нормально)
- Память: VRAM ~70-80%, RAM минимально
- GPU: Утилизация ~95%

**Разница:** ~100x ускорение!

---

## 🛠️ Дополнительные инструменты

### Мониторинг GPU в реальном времени

```bash
# Мониторинг VRAM и GPU
watch -n 1 nvidia-smi

# Или более детально
nvtop  # Нужно установить: sudo apt install nvtop
```

### Проверка загрузки модели

В логах агента (`logs/agent_*.log`) ищите строки:
```
llama_model_load: using CUDA ...
llama_kv_cache_init: CUDA ...
```

Если их нет - модель на CPU.

---

## 📝 Резюме

**Проблема:** CPU-only версия llama-cpp-python  
**Решение:** Переустановить с CUDA поддержкой  
**Диагностика:** `python3 diagnose_cuda.py`  
**Документация:** См. `requirements-cuda.txt`

**Важно:** Параметры в agent.py (`offload_kqv`, `type_k`, `type_v`) корректны!
Проблема исключительно в установке llama-cpp-python.

---

**Версия:** v0.0.3-p4-alpha  
**Дата:** 2025-10-18
