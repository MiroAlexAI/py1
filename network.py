import httpx
import asyncio
import logging
import os
from dotenv import load_dotenv
import db

logger = logging.getLogger(__name__)

async def fetch_model_response(model_name, api_url, api_key_name, prompt, timeout=60):
    """
    Отправляет асинхронный запрос к API конкретной модели.
    Поддерживает ротацию ключей для OpenRouter и интеграцию с Hugging Face.
    """
    load_dotenv()
    
    # Логика выбора ключей (ротация)
    api_keys = []
    if api_key_name == "OPENROUTER_API_KEY":
        k1 = os.getenv("OPENROUTER_API_KEY")
        k2 = os.getenv("OPENROUTER_API_KEY2")
        if k1: api_keys.append(k1)
        if k2: api_keys.append(k2)
    elif api_key_name in ["HF_API_KEY", "HF_TOKEN"]:
        k = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")
        if k: api_keys.append(k)
    else:
        k = os.getenv(api_key_name)
        if k: api_keys.append(k)

    if not api_keys:
        return {"model": model_name, "response": "API key not found", "status": "Error: Auth"}

    last_error = ""
    for i, api_key in enumerate(api_keys):
        # Экспоненциальная выдержка перед переключением на запасной ключ (если попытка не первая)
        if i > 0:
            wait_time = 2 ** i 
            logger.info(f"Waiting {wait_time}s before switching to backup key for {model_name}...")
            await asyncio.sleep(wait_time)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Специфичные заголовки для OpenRouter
        if "openrouter.ai" in api_url:
            headers["HTTP-Referer"] = "https://github.com/antigravity/chatlist"
            headers["X-Title"] = "ChatList AI Tool"

        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            async with httpx.AsyncClient(timeout=float(timeout)) as client:
                response = await client.post(api_url, headers=headers, json=data)
                
                # Ротация при ошибках или лимитах (401, 429, 502, 503)
                if response.status_code in [401, 429, 502, 503] and i < len(api_keys) - 1:
                    logger.warning(f"Key {i+1} failed ({response.status_code}) for {model_name}. Switching...")
                    continue
                
                response.raise_for_status()
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content')
                
                if content:
                    # Важно: возвращаем именно полученный ответ
                    return {"model": model_name, "response": content, "status": "Success"}
                else:
                    return {"model": model_name, "response": "Empty answer from model", "status": "Error: Parse"}
                    
        except Exception as e:
            last_error = str(e)
            if i < len(api_keys) - 1:
                logger.error(f"Attempt {i+1} for {model_name} failed: {last_error}. Trying next key...")
                continue
            break

    return {"model": model_name, "response": last_error, "status": "Error"}

async def delayed_fetch(delay, model_name, api_url, api_key_name, prompt, timeout=60):
    """Вспомогательная функция для ступенчатого запуска запросов."""
    if delay > 0:
        await asyncio.sleep(delay)
    return await fetch_model_response(model_name, api_url, api_key_name, prompt, timeout)

async def send_parallel_prompts(active_models, prompt):
    """Отправляет промт одновременно во все активные модели с учетом задержки."""
    delay_step = float(db.get_setting("request_delay", 0.0))
    tasks = []
    for i, m in enumerate(active_models):
        # Первый запрос уходит сразу, каждый последующий - с шагом задержки
        tasks.append(delayed_fetch(i * delay_step, m[0], m[1], m[2], prompt))
    
    return await asyncio.gather(*tasks)
