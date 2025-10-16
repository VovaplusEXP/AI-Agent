import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# Singleton для модели эмбеддингов
class EmbeddingModelSingleton:
    """
    Singleton для SentenceTransformer модели.
    Гарантирует, что модель загружается только один раз.
    """
    _instance = None
    _model = None
    _model_name = None
    
    @classmethod
    def get_model(cls, model_name: str = 'all-MiniLM-L6-v2'):
        """Возвращает единственный экземпляр модели."""
        if cls._model is None or cls._model_name != model_name:
            logger.info(f"Загрузка модели эмбеддингов: {model_name}...")
            print(f"[INFO] Идет загрузка модели эмбеддингов '{model_name}'. Это может занять несколько минут при первом запуске...")
            try:
                # ИСПРАВЛЕНО: local_files_only=True отключает проверку HuggingFace API
                # Модель будет загружаться из локального кэша (~/.cache/huggingface/)
                # Если модели нет - упадёт с ошибкой, тогда загрузим с интернета
                try:
                    cls._model = SentenceTransformer(model_name, local_files_only=True)
                    logger.info("Модель загружена из локального кэша")
                except Exception as local_err:
                    logger.info(f"Локальный кэш не найден, загружаем из интернета: {local_err}")
                    cls._model = SentenceTransformer(model_name, local_files_only=False)
                
                cls._model_name = model_name
                print(f"[INFO] Модель эмбеддингов '{model_name}' успешно загружена.")
                logger.info(f"Модель эмбеддингов '{model_name}' успешно загружена.")
            except Exception as e:
                logger.critical(f"Не удалось загрузить модель SentenceTransformer: {e}", exc_info=True)
                print(f"[ERROR] Не удалось загрузить модель эмбеддингов: {e}")
                cls._model = None
        return cls._model

class VectorMemory:
    """
    Базовый класс для векторной памяти с возможностью
    сохранения и загрузки на диск.
    
    Поддерживает два типа памяти:
    - GlobalMemory: общая для всех чатов (knowledge base)
    - ProjectMemory: локальная для каждого чата (project context)
    """
    def __init__(self, memory_dir: str, model_name: str = 'all-MiniLM-L6-v2', memory_type: str = "global"):
        self.memory_path = Path(memory_dir)
        self.memory_path.mkdir(exist_ok=True, parents=True)
        self.memory_type = memory_type
        self.index_path = self.memory_path / "index.faiss"
        self.storage_path = self.memory_path / "storage.json"

        # Используем singleton для модели эмбеддингов
        self.model = EmbeddingModelSingleton.get_model(model_name)
        
        if self.model:
            self.dimension = self.model.get_sentence_embedding_dimension()
            self.load()
            logger.info(f"{memory_type.capitalize()} память успешно загружена/инициализирована.")
        else:
            logger.error(f"Не удалось инициализировать {memory_type} память: модель не загружена")
            self.index = None
            self.storage = []

    def load(self):
        """Загружает индекс и хранилище с диска, если они существуют."""
        if self.index_path.exists() and self.storage_path.exists():
            logger.info(f"Загрузка существующей {self.memory_type} памяти с диска...")
            self.index = faiss.read_index(str(self.index_path))
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                self.storage = json.load(f)
        else:
            logger.info(f"Создание новой пустой {self.memory_type} памяти.")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.storage = []

    def save(self):
        """Сохраняет текущее состояние индекса и хранилища на диск."""
        if not self.model:
            logger.warning(f"Модель не загружена, сохранение {self.memory_type} памяти невозможно.")
            return
        
        # Убеждаемся, что директория существует
        self.memory_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Сохранение {self.memory_type} памяти на диск...")
        try:
            faiss.write_index(self.index, str(self.index_path))
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.storage, f, ensure_ascii=False, indent=4)
            logger.debug(f"{self.memory_type.capitalize()} память успешно сохранена в {self.memory_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении {self.memory_type} памяти: {e}", exc_info=True)

    def _rebuild_index(self):
        """Полностью перестраивает индекс FAISS на основе текущего хранилища."""
        logger.debug(f"Перестройка индекса FAISS для {self.memory_type} памяти...")
        self.index = faiss.IndexFlatL2(self.dimension)
        if self.storage:
            embeddings = self.model.encode(self.storage, convert_to_tensor=False)
            self.index.add(np.array(embeddings, dtype=np.float32))

    def add(self, text: str, metadata: Optional[Dict] = None):
        """
        Добавляет текстовую информацию в память и сохраняет изменения.
        
        Args:
            text: Текст для добавления
            metadata: Дополнительные метаданные (опционально)
        """
        if not self.model:
            return
        try:
            # Проверка на дубликаты - не добавляем, если уже есть
            if text in self.storage:
                logger.debug(f"Запись уже существует в {self.memory_type} памяти, пропускаем дубликат")
                return
                
            embedding = self.model.encode([text], convert_to_tensor=False)
            self.index.add(np.array(embedding, dtype=np.float32))
            
            # Если есть метаданные, сохраняем их вместе с текстом
            if metadata:
                entry = {'text': text, 'metadata': metadata}
                self.storage.append(entry)
            else:
                self.storage.append(text)
            
            logger.debug(f"Добавлена новая запись в {self.memory_type} память. Всего записей: {len(self.storage)}")
            self.save()
        except Exception as e:
            logger.error(f"Ошибка при добавлении в {self.memory_type} векторную память: {e}", exc_info=True)

    def delete(self, entry_id: int) -> str:
        """Удаляет запись из памяти по ID и перестраивает индекс."""
        if not self.model:
            return "Ошибка: модель не загружена."
        if 0 <= entry_id < len(self.storage):
            removed = self.storage.pop(entry_id)
            removed_text = removed['text'] if isinstance(removed, dict) else removed
            self._rebuild_index()
            self.save()
            logger.info(f"Запись {entry_id} удалена из {self.memory_type} памяти. Перестроен индекс.")
            return f"Запись {entry_id} ('{removed_text[:30]}...') успешно удалена."
        return f"Ошибка: Неверный ID {entry_id}."

    def list_entries(self) -> str:
        """Возвращает пронумерованный список всех записей в памяти."""
        if not self.storage:
            return f"{self.memory_type.capitalize()} память пуста."
        
        lines = []
        for i, entry in enumerate(self.storage):
            if isinstance(entry, dict):
                text = entry['text']
                meta = entry.get('metadata', {})
                meta_str = f" [{meta}]" if meta else ""
                lines.append(f"ID {i}: {text}{meta_str}")
            else:
                lines.append(f"ID {i}: {entry}")
        
        return "\n".join(lines)

    def search(self, query: str, k: int = 3) -> List[str]:
        """Ищет наиболее релевантную информацию в памяти."""
        if not self.model or self.index.ntotal == 0:
            return []
        try:
            query_embedding = self.model.encode([query], convert_to_tensor=False)
            num_results = min(k, self.index.ntotal)
            _, indices = self.index.search(np.array(query_embedding, dtype=np.float32), num_results)
            
            results = []
            for i in indices[0]:
                entry = self.storage[i]
                if isinstance(entry, dict):
                    results.append(entry['text'])
                else:
                    results.append(entry)
            
            return results
        except Exception as e:
            logger.error(f"Ошибка при поиске по {self.memory_type} векторной памяти: {e}", exc_info=True)
            return []
    
    def get_stats(self) -> Dict:
        """Возвращает статистику памяти."""
        return {
            'type': self.memory_type,
            'total_entries': len(self.storage),
            'index_size': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'storage_path': str(self.memory_path)
        }


class MemoryManager:
    """
    Менеджер памяти - управляет глобальной и проектными памятями.
    """
    
    def __init__(self, global_memory_dir: str = "memory/global", chats_base_dir: str = None):
        self.global_memory = VectorMemory(global_memory_dir, memory_type="global")
        self.project_memories: Dict[str, VectorMemory] = {}
        # Сохраняем базовую директорию для чатов (если передана)
        self.chats_base_dir = Path(chats_base_dir) if chats_base_dir else None
    
    def get_project_memory(self, project_name: str, project_dir: str = None) -> VectorMemory:
        """
        Получает или создает проектную память для указанного проекта/чата.
        
        Args:
            project_name: Имя проекта/чата
            project_dir: Директория проекта (если None, используется chats_base_dir/<project_name>/memory)
        """
        if project_name not in self.project_memories:
            if project_dir is None:
                # Используем абсолютный путь, если установлен chats_base_dir
                if self.chats_base_dir:
                    project_dir = str(self.chats_base_dir / project_name / "memory")
                else:
                    # Fallback на относительный путь (для обратной совместимости)
                    project_dir = f"chats/{project_name}/memory"
            
            self.project_memories[project_name] = VectorMemory(
                project_dir,
                memory_type=f"project:{project_name}"
            )
        
        return self.project_memories[project_name]
    
    def save_all(self):
        """Сохраняет все памяти (глобальную и все проектные)."""
        self.global_memory.save()
        for project_memory in self.project_memories.values():
            project_memory.save()
    
    def get_all_stats(self) -> Dict:
        """Возвращает статистику всех памятей."""
        stats = {
            'global': self.global_memory.get_stats(),
            'projects': {}
        }
        
        for name, memory in self.project_memories.items():
            stats['projects'][name] = memory.get_stats()
        
        return stats

