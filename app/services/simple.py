from google import genai
from app.config.settings import settings
import json
import re
import time

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "models/gemini-2.5-pro"
    
    def _clean_json_response(self, content: str) -> str:
        """Clean markdown formatting from Gemini response"""
        if not content:
            return "{}"
        
        # Remove markdown fenced code blocks (```...```)
        content = re.sub(r'```[\s\S]*?```', '', content)
        # Remove any remaining triple backticks at line starts or ends
        content = re.sub(r'^\s*```', '', content, flags=re.M)
        content = re.sub(r'```\s*$', '', content, flags=re.M)
        return content.strip()
    
    def _retry_generate(self, prompt: str, system_instruction: str, config: dict, max_retries: int = 3):
        """Retry generation if response is empty"""
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "system_instruction": system_instruction,
                        **config
                    }
                )
                
                # Check if response has text
                if response and hasattr(response, 'text') and response.text:
                    return response.text
                
                # Check candidates
                if response and hasattr(response, 'candidates') and response.candidates:
                    if len(response.candidates) > 0:
                        candidate = response.candidates
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                if len(candidate.content.parts) > 0:
                                    if hasattr(candidate.content.parts, 'text'):
                                        return candidate.content.parts.text
                
                print(f"Attempt {attempt + 1}: Gemini returned empty response, retrying...")
                time.sleep(1)  # Wait before retry
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise
        
        return None
    
    async def extract_topics(self, text: str, subject: str) -> list:
        """Extract topics from text using Gemini 2.5 Pro"""
        
        system_instruction = """
        You are an expert at analyzing academic content and extracting study topics.
        Analyze the provided text and extract all distinct topics.
        Assign each topic an importance weight from 1-10 based on frequency, emphasis, and apparent significance.
        Return ONLY valid JSON in this exact format:
        {"topics": [{"name": "Topic Name", "weight": 8}, {"name": "Another Topic", "weight": 6}]}
        
        Do not include any markdown formatting, code blocks, or additional text.
        """
        
        prompt = f"""
        Subject: {subject}
        
        Content to analyze:
        {text[:3500]}
        
        Extract all major topics and subtopics with their importance weights (1-10).
        Return only the JSON object, no additional text or formatting.
        """
        
        try:
            content = self._retry_generate(
                prompt=prompt,
                system_instruction=system_instruction,
                config={
                    "temperature": 0.3,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,  # Important: set high enough
                }
            )
            
            if not content:
                print("Warning: Gemini returned empty response for topic extraction")
                return self._get_default_topics()
            
            content = self._clean_json_response(content)
            result = json.loads(content)
            topics = result.get("topics", [])
            
            if not topics or len(topics) == 0:
                return self._get_default_topics()
            
            return topics
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response content: {content}")
            return self._get_default_topics()
        except Exception as e:
            print(f"Gemini API error: {e}")
            return self._get_default_topics()
    
    async def generate_lesson_content(self, topic_name: str, subject: str) -> dict:
        """Generate lesson content for a topic using Gemini 2.5 Pro"""
        
        system_instruction = """
        You are an expert educator creating concise, clear study materials.
        Create a structured lesson with:
        1. Brief concept explanation (3-4 sentences)
        2. 2-3 key formulas, definitions, or principles
        3. One worked example
        4. Common mistakes to avoid
        
        Return ONLY valid JSON in this format:
        {
            "explanation": "...",
            "key_points": ["point 1", "point 2", "point 3"],
            "example": "...",
            "common_mistakes": ["mistake 1", "mistake 2"]
        }
        
        Do not include any markdown formatting, code blocks, or additional text.
        """
        
        prompt = f"Create a comprehensive lesson for: {topic_name} in {subject}"
        
        try:
            content = self._retry_generate(
                prompt=prompt,
                system_instruction=system_instruction,
                config={
                    "temperature": 0.5,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            
            if not content:
                print("Warning: Gemini returned empty response for lesson generation")
                return self._get_default_lesson(topic_name, subject)
            
            content = self._clean_json_response(content)
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response content: {content}")
            return self._get_default_lesson(topic_name, subject)
        except Exception as e:
            print(f"Gemini API error: {e}")
            return self._get_default_lesson(topic_name, subject)
    
    async def analyze_study_materials(self, text: str, material_type: str) -> dict:
        """Analyze uploaded study materials and provide insights"""
        
        if not text or len(text.strip()) == 0:
            print("Warning: Empty text provided for analysis")
            return self._get_default_analysis()
        
        system_instruction = f"""
        You are analyzing {material_type} for a student.
        Provide insights about:
        1. Main themes covered
        2. Difficulty level (Easy/Medium/Hard)
        3. Estimated study time needed (in hours)
        4. Key areas of focus
        
        Return JSON format:
        {{
            "themes": ["theme1", "theme2"],
            "difficulty": "Medium",
            "estimated_hours": 10,
            "focus_areas": ["area1", "area2"]
        }}
        """
        
        prompt = f"Analyze this {material_type}:\n\n{text[:2500]}"
        
        try:
            content = self._retry_generate(
                prompt=prompt,
                system_instruction=system_instruction,
                config={
                    "temperature": 0.3,
                    "max_output_tokens": 1024,
                }
            )
            
            if not content:
                print("Warning: Gemini returned empty response for material analysis")
                return self._get_default_analysis()
            
            content = self._clean_json_response(content)
            return json.loads(content)
            
        except Exception as e:
            print(f"Analysis error: {e}")
            return self._get_default_analysis()
    
    # Default fallback methods
    def _get_default_topics(self) -> list:
        """Return default topics when extraction fails"""
        return [
            {"name": "Introduction and Fundamentals", "weight": 6},
            {"name": "Core Concepts", "weight": 8},
            {"name": "Advanced Topics", "weight": 7},
            {"name": "Problem-Solving Techniques", "weight": 8},
            {"name": "Review and Practice", "weight": 6}
        ]
    
    def _get_default_lesson(self, topic_name: str, subject: str) -> dict:
        """Return default lesson structure when generation fails"""
        return {
            "explanation": f"This section covers {topic_name} in {subject}. This is a fundamental concept that requires understanding of basic principles and their practical applications. Students should focus on building a strong foundation in this area.",
            "key_points": [
                f"Core principle 1 of {topic_name}",
                f"Important concept 2 related to {topic_name}",
                f"Key application of {topic_name} in {subject}"
            ],
            "example": f"A practical example of {topic_name} would be demonstrated here with step-by-step solution showing how to apply the concepts learned.",
            "common_mistakes": [
                "Not understanding the fundamental concepts before moving to advanced topics",
                "Overlooking important details in problem-solving"
            ]
        }
    
    def _get_default_analysis(self) -> dict:
        """Return default analysis when extraction fails"""
        return {
            "themes": ["General topics", "Core concepts"],
            "difficulty": "Medium",
            "estimated_hours": 8,
            "focus_areas": ["Fundamental understanding", "Practice problems"]
        }
