"""
LLM Client - Unified interface for OpenAI and Gemini.
"""

import json
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
import google.generativeai as genai

from ...config import settings


class LLMClient:
    """Unified LLM client supporting OpenAI and Gemini."""
    
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        
        if self.provider == "openai":
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
        elif self.provider == "gemini":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
            self.model = settings.GEMINI_MODEL
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
        if self.provider == "openai":
            return await self._openai_complete(
                prompt, system_prompt, temperature, max_tokens, json_response
            )
        else:
            return await self._gemini_complete(
                prompt, system_prompt, temperature, max_tokens, json_response
            )
    
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
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_response:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await self.openai_client.chat.completions.create(**kwargs)
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


# Global LLM client instance
llm_client = LLMClient()


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """Get LLM client instance."""
    if provider and provider != settings.LLM_PROVIDER:
        return LLMClient(provider=provider)
    return llm_client

