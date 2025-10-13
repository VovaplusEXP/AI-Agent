# chat_manager.py
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ChatManager:
    """
    Менеджер чатов - управляет сохранением и загрузкой чатов на диск.
    
    Структура директории чата:
    chats/
    └── <chat_name>/
        ├── metadata.json      - метаданные (дата создания, описание)
        ├── history.json       - история диалога
        ├── scratchpad.json    - рабочая память (план, цель)
        └── memory/            - проектная память (векторная БД)
            ├── index.faiss
            └── storage.json
    """
    
    def __init__(self, chats_dir: str = "chats"):
        self.chats_dir = Path(chats_dir)
        self.chats_dir.mkdir(exist_ok=True)
        logger.info(f"ChatManager инициализирован с директорией: {self.chats_dir}")
    
    def save_chat(
        self,
        chat_name: str,
        history: List[Dict],
        scratchpad: Dict,
        description: str = ""
    ) -> bool:
        """
        Сохраняет чат на диск.
        
        Args:
            chat_name: Имя чата
            history: История диалога
            scratchpad: Рабочая память
            description: Описание чата (опционально)
            
        Returns:
            True если успешно сохранено
        """
        try:
            chat_path = self.chats_dir / chat_name
            chat_path.mkdir(exist_ok=True)
            
            # Сохраняем метаданные
            metadata = {
                'name': chat_name,
                'description': description,
                'created_at': datetime.now().isoformat(),
                'last_saved': datetime.now().isoformat(),
                'messages_count': len(history)
            }
            
            with open(chat_path / 'metadata.json', 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Сохраняем историю
            with open(chat_path / 'history.json', 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            # Сохраняем scratchpad
            with open(chat_path / 'scratchpad.json', 'w', encoding='utf-8') as f:
                json.dump(scratchpad, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Чат '{chat_name}' успешно сохранен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении чата '{chat_name}': {e}", exc_info=True)
            return False
    
    def load_chat(self, chat_name: str) -> Optional[Dict]:
        """
        Загружает чат с диска.
        
        Args:
            chat_name: Имя чата
            
        Returns:
            Dict с ключами: metadata, history, scratchpad или None
        """
        try:
            chat_path = self.chats_dir / chat_name
            
            if not chat_path.exists():
                logger.warning(f"Чат '{chat_name}' не найден")
                return None
            
            # Загружаем метаданные
            with open(chat_path / 'metadata.json', 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Загружаем историю
            with open(chat_path / 'history.json', 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # Загружаем scratchpad
            with open(chat_path / 'scratchpad.json', 'r', encoding='utf-8') as f:
                scratchpad = json.load(f)
            
            logger.info(f"Чат '{chat_name}' успешно загружен ({len(history)} сообщений)")
            
            return {
                'metadata': metadata,
                'history': history,
                'scratchpad': scratchpad
            }
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке чата '{chat_name}': {e}", exc_info=True)
            return None
    
    def list_saved_chats(self) -> List[Dict]:
        """
        Возвращает список сохраненных чатов с метаданными.
        
        Returns:
            Список словарей с метаданными чатов
        """
        saved_chats = []
        
        try:
            for chat_path in self.chats_dir.iterdir():
                if chat_path.is_dir():
                    metadata_file = chat_path / 'metadata.json'
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            saved_chats.append(metadata)
        except Exception as e:
            logger.error(f"Ошибка при получении списка чатов: {e}", exc_info=True)
        
        # Сортируем по дате последнего сохранения
        saved_chats.sort(key=lambda x: x.get('last_saved', ''), reverse=True)
        
        return saved_chats
    
    def delete_chat(self, chat_name: str) -> bool:
        """
        Удаляет чат с диска.
        
        Args:
            chat_name: Имя чата
            
        Returns:
            True если успешно удалено
        """
        try:
            chat_path = self.chats_dir / chat_name
            
            if not chat_path.exists():
                logger.warning(f"Чат '{chat_name}' не найден")
                return False
            
            # Удаляем директорию со всем содержимым
            import shutil
            shutil.rmtree(chat_path)
            
            logger.info(f"Чат '{chat_name}' успешно удален")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при удалении чата '{chat_name}': {e}", exc_info=True)
            return False
    
    def chat_exists(self, chat_name: str) -> bool:
        """Проверяет, существует ли чат на диске."""
        chat_path = self.chats_dir / chat_name
        return chat_path.exists() and (chat_path / 'metadata.json').exists()
    
    def get_chat_path(self, chat_name: str) -> Path:
        """Возвращает путь к директории чата."""
        return self.chats_dir / chat_name
    
    def auto_save_chat(
        self,
        chat_name: str,
        history: List[Dict],
        scratchpad: Dict,
        description: str = ""
    ) -> None:
        """
        Автоматически сохраняет чат (тихо, без логов).
        Используется для периодического сохранения в фоне.
        """
        try:
            chat_path = self.chats_dir / chat_name
            chat_path.mkdir(exist_ok=True)
            
            # Обновляем метаданные
            metadata_file = chat_path / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                metadata['last_saved'] = datetime.now().isoformat()
                metadata['messages_count'] = len(history)
            else:
                metadata = {
                    'name': chat_name,
                    'description': description,
                    'created_at': datetime.now().isoformat(),
                    'last_saved': datetime.now().isoformat(),
                    'messages_count': len(history)
                }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Сохраняем историю и scratchpad
            with open(chat_path / 'history.json', 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            with open(chat_path / 'scratchpad.json', 'w', encoding='utf-8') as f:
                json.dump(scratchpad, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.debug(f"Ошибка автосохранения чата '{chat_name}': {e}")
