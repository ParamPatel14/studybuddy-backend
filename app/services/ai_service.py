from google import genai
from app.config.settings import settings
import json
import re

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Try gemini-2.0-flash if 2.5-pro continues to have issues
        self.model = "models/gemini-2.5-pro"
    
    async def extract_topics(self, text: str, subject: str) -> list:
        """Extract topics - simplified version"""
        
        prompt = f"""
        Analyze this {subject} content and extract topics with weights (1-10).
        
        Content:
        {text[:3500]}
        
        Return JSON: {{"topics": [{{"name": "Topic", "weight": 8}}]}}
        """
        
        try:
            # Simpler config without max_output_tokens
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            if not response or not response.text:
                return self._default_topics()
            
            content = response.text.strip()
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'^```', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            result = json.loads(content.strip())
            return result.get("topics", self._default_topics())
            
        except:
            return self._default_topics()
    
    def _default_topics(self):
        return [
            {"name": "Introduction", "weight": 6},
            {"name": "Core Concepts", "weight": 8},
            {"name": "Advanced Topics", "weight": 7}
        ]
