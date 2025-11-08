from typing import Optional, List, Dict
import os
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    """
    Multi-provider LLM service with automatic fallback
    Supports: Mistral API, Groq, Gemini
    """
    
    def __init__(self):
        self.provider_order = os.getenv("LLM_PROVIDER_ORDER", "mistral,groq,gemini").split(',')
        self.default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "mistral")
        
        self.clients = {}
        self._init_clients()
        
        print(f"✓ LLM Service initialized")
        print(f"  Provider order: {self.provider_order}")
        print(f"  Available: {list(self.clients.keys())}")
    
    def _init_clients(self):
        """Initialize all available LLM clients"""
        
        # Mistral API
        if os.getenv("MISTRAL_API_KEY"):
            try:
                from mistralai import Mistral
                self.clients['mistral'] = {
                    'client': Mistral(api_key=os.getenv("MISTRAL_API_KEY")),
                    'model': 'mistral-small-latest',
                    'type': 'mistral'
                }
                print("  ✓ Mistral API initialized")
            except Exception as e:
                print(f"  ✗ Mistral failed: {e}")
        
        # Groq
        if os.getenv("GROQ_API_KEY"):
            try:
                from groq import Groq
                self.clients['groq'] = {
                    'client': Groq(api_key=os.getenv("GROQ_API_KEY")),
                    'model': 'llama-3.3-70b-versatile',
                    'type': 'groq'
                }
                print("  ✓ Groq initialized")
            except Exception as e:
                print(f"  ✗ Groq failed: {e}")
        
        # Gemini
        if os.getenv("GEMINI_API_KEY"):
            try:
                from google import genai
                self.clients['gemini'] = {
                    'client': genai.Client(api_key=os.getenv("GEMINI_API_KEY")),
                    'model': 'gemini-2.0-flash-exp',
                    'type': 'gemini'
                }
                print("  ✓ Gemini initialized")
            except Exception as e:
                print(f"  ✗ Gemini failed: {e}")
    
    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        preferred_provider: Optional[str] = None
    ) -> Dict:
        """Generate content with automatic fallback"""
        
        if preferred_provider and preferred_provider in self.clients:
            providers_to_try = [preferred_provider] + [p for p in self.provider_order if p != preferred_provider]
        else:
            providers_to_try = self.provider_order
        
        last_error = None
        for provider_name in providers_to_try:
            if provider_name not in self.clients:
                continue
            
            try:
                print(f"  🤖 Trying {provider_name}...")
                
                response = self._call_provider(
                    provider_name,
                    prompt,
                    system_instruction,
                    temperature,
                    max_tokens
                )
                
                print(f"  ✓ Success with {provider_name}")
                
                return {
                    'success': True,
                    'provider': provider_name,
                    'text': response,
                    'error': None
                }
                
            except Exception as e:
                print(f"  ✗ {provider_name} failed: {e}")
                last_error = str(e)
                continue
        
        return {
            'success': False,
            'provider': None,
            'text': None,
            'error': f"All providers failed. Last error: {last_error}"
        }
    
    def _call_provider(
        self,
        provider_name: str,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call specific provider"""
        
        provider = self.clients[provider_name]
        provider_type = provider['type']
        
        if provider_type == 'mistral':
            return self._call_mistral(provider, prompt, system_instruction, temperature, max_tokens)
        elif provider_type == 'groq':
            return self._call_groq(provider, prompt, system_instruction, temperature, max_tokens)
        elif provider_type == 'gemini':
            return self._call_gemini(provider, prompt, system_instruction, temperature, max_tokens)
        else:
            raise Exception(f"Unknown provider type: {provider_type}")
    
    def _call_mistral(self, provider: Dict, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        """Call Mistral API"""
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = provider['client'].chat.complete(
            model=provider['model'],
            messages=messages,
            temperature=temp,
            max_tokens=max_tokens,
        )
        
        return response.choices[0].message.content
    
    def _call_groq(self, provider: Dict, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        """Call Groq API"""
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = provider['client'].chat.completions.create(
            model=provider['model'],
            messages=messages,
            temperature=temp,
            max_tokens=max_tokens,
        )
        
        return response.choices[0].message.content
    
    def _call_gemini(self, provider: Dict, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        """Call Gemini API"""
        from google.genai import types
        
        response = provider['client'].models.generate_content(
            model=provider['model'],
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temp,
                max_output_tokens=max_tokens,
            )
        )
        
        return response.text if response and response.text else ""
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return list(self.clients.keys())
