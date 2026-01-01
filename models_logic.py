import os
from dotenv import load_dotenv
import db

def load_environment():
    """Загрузка переменных окружения из .env."""
    load_dotenv()

def get_active_models_with_keys():
    """Возвращает список моделей, готовых к отправке (активные и с ключами)."""
    load_environment()
    all_active = db.get_models(only_active=True)
    ready_models = []
    
    for model in all_active:
        name, url, key_name, _ = model
        if os.getenv(key_name):
            ready_models.append(model)
        else:
            # Можно логировать отсутствие ключа
            pass
            
    return ready_models

def setup_default_models():
    """Предварительная настройка популярных моделей, если таблица пуста."""
    existing = db.get_models()
    if not existing:
        openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        or_key = "OPENROUTER_API_KEY"
        
        # Список бесплатных моделей OpenRouter (только стабильные)
        free_models = [
            "nvidia/nemotron-nano-12b-v2-vl:free",
            "nvidia/nemotron-nano-9b-v2:free",
            "z-ai/glm-4.5-air:free",
            "qwen/qwen3-coder:free",
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "google/gemma-3-2b-it:free"
        ]
        
        for model_id in free_models:
            # Используем model_id как имя в БД, чтобы network.py отправлял его в JSON
            db.add_model(model_id, openrouter_url, or_key)
        
        # Добавляем стандартные для примера
        db.add_model("gpt-4o-mini", "https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY")
