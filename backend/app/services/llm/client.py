"""
LLM Client - Unified interface for OpenAI and Gemini.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
import google.generativeai as genai
import time

from ...config import settings


_telemetry_lock = threading.Lock()


def _emit_telemetry(record: Dict[str, Any]) -> None:
    """Append a telemetry record as JSONL when LLM_TELEMETRY_FILE env is set.

    No-op when the env var is empty. Used by the benchmark harness to
    reconstruct per-module latency / cost without changing runtime behavior.
    """
    target = os.environ.get("LLM_TELEMETRY_FILE")
    if not target:
        return
    try:
        with _telemetry_lock:
            with open(target, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


class LLMClient:
    """Unified LLM client supporting OpenAI and Gemini."""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        task_type: Optional[str] = None
    ):
        self.task_type = task_type or "default"
        self.model = model or _model_for_task(task_type)
        self.provider = provider or _provider_for_model(self.model) or settings.LLM_PROVIDER
        self.last_usage: Dict[str, Any] = {}
        
        if self.provider == "openai":
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = self.model or settings.OPENAI_MODEL
        elif self.provider == "gemini":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = self.model or settings.GEMINI_MODEL
            self.gemini_model = genai.GenerativeModel(self.model)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        json_response: bool = False
    ) -> str:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Creativity level (0-1)
            max_tokens: Maximum response tokens
            json_response: Whether to expect JSON response
            
        Returns:
            The generated text response
        """
        started_at = time.perf_counter()
        success = True
        result: Optional[str] = None
        try:
            if self.provider == "openai":
                result = await self._openai_complete(
                    prompt, system_prompt, temperature, max_tokens, json_response
                )
            else:
                result = await self._gemini_complete(
                    prompt, system_prompt, temperature, max_tokens, json_response
                )
            return result
        except Exception:
            success = False
            raise
        finally:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            usage = self.last_usage or {}
            print(
                f"       [LLM] task={self.task_type} provider={self.provider} model={self.model} "
                f"latency_ms={latency_ms} tokens_in={usage.get('tokens_in')} tokens_out={usage.get('tokens_out')}"
            )
            _emit_telemetry({
                "ts": datetime.now(timezone.utc).isoformat(),
                "task_type": self.task_type,
                "provider": self.provider,
                "model": self.model,
                "latency_ms": latency_ms,
                "tokens_in": usage.get("tokens_in"),
                "tokens_out": usage.get("tokens_out"),
                "success": success,
            })
    
    async def _openai_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        json_response: bool
    ) -> str:
        """Generate completion using OpenAI."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        # gpt-5.x and o-series models require `max_completion_tokens` and
        # reject the legacy `max_tokens` parameter with a 400.
        if _uses_completion_tokens(self.model):
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

        if json_response:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self.openai_client.chat.completions.create(**kwargs)
        except Exception as err:
            # Defensive fallback: if the API rejects `max_tokens` for an
            # unknown future model, retry once with the new parameter name
            # rather than burning the whole session.
            err_msg = str(err)
            if "max_tokens" in err_msg and "max_completion_tokens" in err_msg and "max_tokens" in kwargs:
                kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
                response = await self.openai_client.chat.completions.create(**kwargs)
            else:
                raise
        usage = getattr(response, "usage", None)
        self.last_usage = {
            "tokens_in": getattr(usage, "prompt_tokens", None),
            "tokens_out": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
        return response.choices[0].message.content
    
    async def _gemini_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        json_response: bool
    ) -> str:
        """Generate completion using Gemini with timeout protection."""
        import asyncio
        
        full_prompt = ""
        
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        
        full_prompt += prompt
        
        if json_response:
            full_prompt += "\n\nRespond with valid JSON only."
        
        def generate():
            try:
                response = self.gemini_model.generate_content(
                    full_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens
                    ),
                    request_options={"timeout": 60}
                )
                self.last_usage = {"tokens_in": None, "tokens_out": None, "total_tokens": None}
                return response.text
            except Exception as e:
                error_str = str(e).lower()
                if "timeout" in error_str or "deadline" in error_str:
                    raise asyncio.TimeoutError(f"Gemini API timeout: {e}")
                raise
        
        loop = asyncio.get_running_loop()
        
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, generate),
                timeout=90.0
            )
            return result
        except asyncio.TimeoutError:
            print(f"       [!] Gemini LLM call timed out")
            raise asyncio.TimeoutError("Gemini timeout")
    
    async def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a JSON response from the LLM.
        
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        try:
            response = await self.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_response=True
            )
            
            if not response:
                print("       [!] LLM devolvio respuesta vacia")
                return None
            
            # Clean response and parse JSON
            response = response.strip()
            import re
            
            # Clean markdown code blocks
            response = response.strip()
            # Match ```json (content) ``` or just ``` (content) ```
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                response = match.group(1).strip()
            
            # Direct parse
            try:
                return json.loads(response)
            except json.JSONDecodeError as err:
                # If direct parse fails, try finding the first { or [ and the last } or ]
                start_idx_dict = response.find('{')
                start_idx_arr = response.find('[')
                
                # Default to dict if both exist, pick the one that appears first
                if start_idx_dict != -1 and start_idx_arr != -1:
                    start_idx = min(start_idx_dict, start_idx_arr)
                else:
                    start_idx = max(start_idx_dict, start_idx_arr)
                
                if start_idx != -1:
                    end_char = '}' if response[start_idx] == '{' else ']'
                    end_idx = response.rfind(end_char)
                    
                    if end_idx != -1 and end_idx > start_idx:
                        try:
                            return json.loads(response[start_idx:end_idx+1])
                        except json.JSONDecodeError:
                            pass
                            
                print(f"       [!] No se pudo extraer JSON valido")
                print(f"       [!] JSON Parse error: {err}")
                print(f"       [!] Response (primeros 300 chars): {response[:300]}")
                return None
            
        except Exception as e:
            print(f"       [!] Error en complete_json: {e}")
            return None


def _model_for_task(task_type: Optional[str]) -> Optional[str]:
    """Resolve task-specific model names while preserving legacy defaults."""
    task = (task_type or "").lower()
    if task in {"strategy", "insights", "ctp", "funnel", "angle_bank", "competitor"}:
        return settings.LLM_MODEL_STRATEGY
    if task in {"creative", "scripts", "hooks", "briefs", "ugc", "survey", "thumbnail", "ab_test"}:
        return settings.LLM_MODEL_CREATIVE
    if task in {"chat", "rag_chat"}:
        return settings.LLM_MODEL_CHAT
    if task in {"classifier", "classification", "stance", "snippet"}:
        return settings.LLM_MODEL_CLASSIFIER
    if task in {"vision", "ad_vision"}:
        return settings.LLM_MODEL_VISION
    return None


def _provider_for_model(model: Optional[str]) -> Optional[str]:
    """Infer provider from model name for task routing."""
    if not model:
        return None
    normalized = model.lower()
    if "gemini" in normalized:
        return "gemini"
    if normalized.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    return None


def _uses_completion_tokens(model: Optional[str]) -> bool:
    """Return True for OpenAI models that require `max_completion_tokens`.

    gpt-5.x and the o-series (o1, o3, o4) reject the legacy `max_tokens`
    parameter with a 400. Legacy gpt-4o / gpt-4-turbo / gpt-3.5 still use
    `max_tokens`.
    """
    if not model:
        return False
    normalized = model.lower()
    if normalized.startswith(("o1", "o3", "o4")):
        return True
    if normalized.startswith("gpt-5"):
        return True
    return False


# Global LLM client instance
llm_client = LLMClient()
_client_cache: Dict[tuple, LLMClient] = {}


def get_llm_client(
    provider: Optional[str] = None,
    task_type: Optional[str] = None,
    model: Optional[str] = None
) -> LLMClient:
    """Get LLM client instance."""
    if not provider and not task_type and not model:
        return llm_client

    resolved_model = model or _model_for_task(task_type)
    resolved_provider = provider or _provider_for_model(resolved_model) or settings.LLM_PROVIDER
    key = (resolved_provider, resolved_model, task_type or "default")
    if key not in _client_cache:
        _client_cache[key] = LLMClient(provider=resolved_provider, model=resolved_model, task_type=task_type)
    return _client_cache[key]
