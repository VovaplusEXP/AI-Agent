# Решение проблемы загрузки модели в RAM вместо VRAM

**Дата:** 2025-10-18  
**Версия:** v0.0.3-p4-alpha  
**Проблема:** Модель загружается в RAM вместо VRAM при использовании CUDA 12.x

---

## 🔴 Описание проблемы

### Симптомы
- Модель загружается в RAM вместо VRAM
- Очень низкая скорость генерации (практически 0 токенов/сек)
- GPU не используется или используется минимально
- Высокое использование CPU и системной памяти

### Причина
Проблема НЕ в коде agent.py, а в установке llama-cpp-python!

**Корневая причина:** llama-cpp-python установлен БЕЗ CUDA поддержки (CPU-only версия)

Когда вы устанавливаете через `pip install llama-cpp-python`, по умолчанию устанавливается
**CPU-only** версия, которая не может использовать GPU, даже если указать `n_gpu_layers=-1`.

---

## ✅ Решение

### Шаг 1: Диагностика

Запустите диагностический скрипт:

```bash
python3 diagnose_cuda.py
```

Скрипт проверит:
- ✅ Установлена ли CUDA и какая версия
- ✅ Работает ли NVIDIA драйвер
- ✅ Поддерживает ли llama-cpp-python CUDA
- ✅ Правильно ли настроены переменные окружения

### Шаг 2: Проверка CUDA

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
