import time
import asyncio
from app.db.database import get_memory, save_message, log_metric, get_config_db
from app.services.llm_client import stream_openrouter

class Orchestrator:
    async def process_chat_stream(self, session_id: str, user_message: str):
        config = await get_config_db() # Fetch config from Cloud DB
        await save_message(session_id, "user", user_message)
        
        # Build Context Window
        history = await get_memory(session_id, config["memory_window"])
        messages = [{"role": "system", "content": config["system_prompt"]}] + history
        
        fallback_order = config["fallback_order"]
        max_retries = config["retry_count"]
        
        # Routing State
        current_model_idx = 0
        model = fallback_order[current_model_idx]
        fallback_triggered = False
        start_time = time.time()
        
        while current_model_idx < len(fallback_order):
            model = fallback_order[current_model_idx]
            model_conf = next((m for m in config["models"] if m["id"] == model), {"timeout": 15})
            
            for attempt in range(max_retries):
                try:
                    full_response = ""
                    async for chunk in stream_openrouter(model, messages, config["max_tokens"], model_conf["timeout"]):
                        full_response += chunk
                        yield chunk
                    
                    latency = (time.time() - start_time) * 1000
                    await save_message(session_id, "assistant", full_response)
                    await log_metric(session_id, model, latency, fallback_triggered, len(full_response)//4, "success")
                    return
                
                except Exception as e:
                    print(f"[Warn] Model {model} attempt {attempt+1} failed: {str(e)}")
                    await asyncio.sleep(1.5 ** attempt)
            
            print(f"[Fallback] Swapping from {model}")
            fallback_triggered = True
            current_model_idx += 1
            
            if current_model_idx == len(fallback_order) - 1:
                messages[0]["content"] += " (Respond extremely concisely. System is in degraded fallback mode)."
                config["max_tokens"] = int(config["max_tokens"] / 2)

        error_msg = "\n\n[ZenoAi Alert] All external providers are currently unavailable. Please try again later."
        yield error_msg
        await log_metric(session_id, "none", (time.time()-start_time)*1000, True, 0, "failed", "All models failed")
        await save_message(session_id, "assistant", error_msg)

orchestrator = Orchestrator()
