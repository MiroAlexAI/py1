import httpx
import asyncio
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

async def fetch_model_response(model_name, api_url, api_key_name, prompt):
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
    for api_key in api_keys:
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
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(api_url, headers=headers, json=data)
                
                # Ротация при ошибках авторизации или лимитах
                if response.status_code in [401, 429] and len(api_keys) > 1 and api_key == api_keys[0]:
                    logger.warning(f"Switching to backup key for {model_name}")
                    continue
                
                response.raise_for_status()
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content')
                if content:
                    return {"model": model_name, "response": content, "status": "Success"}
                else:
                    return {"model": model_name, "response": "No content in response", "status": "Error: Parse"}
                    
        except Exception as e:
            last_error = str(e)
            if len(api_keys) > 1 and api_key == api_keys[0]:
                logger.error(f"Fallback triggered for {model_name}: {last_error}")
                continue
            break

    return {"model": model_name, "response": last_error, "status": "Error"}

async def send_parallel_prompts(active_models, prompt):
    """Отправляет промт одновременно во все активные модели."""
    tasks = [fetch_model_response(m[0], m[1], m[2], prompt) for m in active_models]
    return await asyncio.gather(*tasks)
