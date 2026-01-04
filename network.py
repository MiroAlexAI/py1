import httpx
import asyncio
import logging
import os
import time
from dotenv import load_dotenv
import db

logger = logging.getLogger(__name__)

async def fetch_model_response(model_name, api_url, api_key_name, prompt, timeout=60, 
                         temperature=0.7, max_tokens=2000, top_p=1.0, thinking=False):
    """
    Отправляет асинхронный запрос к API конкретной модели с учетом глобальных параметров.
    """
    load_dotenv()
    start_time = time.time()
    
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
    elif api_key_name == "ZAI_API_KEY":
        k = os.getenv("ZAI_API_KEY")
        if k: api_keys.append(k)
    else:
        k = os.getenv(api_key_name)
        if k: api_keys.append(k)

    if not api_keys:
        return {"model": model_name, "response": "API key not found", "status": "Error: Auth", "resp_time": 0.0}

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
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p
        }

        # Специфичный блок для z.ai (GLM)
        if "z.ai" in api_url:
            data["model"] = model_name.lower()
            if thinking:
                data["thinking"] = {
                    "type": "enabled"
                }

        try:
            async with httpx.AsyncClient(timeout=float(timeout)) as client:
                response = await client.post(api_url, headers=headers, json=data)
                elapsed = time.time() - start_time
                
                # Ротация при ошибках или лимитах (401, 429, 502, 503)
                if response.status_code in [401, 429, 502, 503] and i < len(api_keys) - 1:
                    logger.warning(f"Key {i+1} failed ({response.status_code}) for {model_name}. Switching...")
                    continue
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"API Error {response.status_code} for {model_name}: {error_text}")
                    return {"model": model_name, "response": f"Error {response.status_code}", "status": "Error: API", "resp_time": elapsed}

                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content')
                
                if content:
                    return {"model": model_name, "response": content, "status": "Success", "resp_time": elapsed}
                else:
                    return {"model": model_name, "response": "Empty answer", "status": "Error: Parse", "resp_time": elapsed}
                    
        except Exception as e:
            elapsed = time.time() - start_time
            last_error = str(e)
            if i < len(api_keys) - 1:
                logger.error(f"Attempt {i+1} for {model_name} failed: {last_error}. Trying next key...")
                continue
            break

    return {"model": model_name, "response": last_error, "status": "Error", "resp_time": elapsed}

async def delayed_fetch(delay, model_name, api_url, api_key_name, prompt, timeout=60, **kwargs):
    """Вспомогательная функция для ступенчатого запуска запросов."""
    if delay > 0:
        await asyncio.sleep(delay)
    return await fetch_model_response(model_name, api_url, api_key_name, prompt, timeout, **kwargs)

async def send_parallel_prompts(active_models, prompt):
    """Отправляет промт одновременно во все активные модели с учетом задержки."""
    delay_step = float(db.get_setting("request_delay", 0.0))
    tasks = []
    for i, m in enumerate(active_models):
        # Первый запрос уходит сразу, каждый последующий - с шагом задержки
        tasks.append(delayed_fetch(i * delay_step, m[0], m[1], m[2], prompt))
    
    return await asyncio.gather(*tasks)
