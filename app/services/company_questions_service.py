import json
import os
from typing import Dict, Optional
from pathlib import Path
from app.services.llm_service import LLMService

class CompanyQuestionsService:
    """
    Service to retrieve company-specific interview questions
    Uses curated JSON files + AI fallback
    """
    
    def __init__(self):
        self.llm_service = LLMService()
        self.data_dir = Path(__file__).parent.parent / "data" / "companies"
        self.companies_cache = {}
        self._load_all_companies()
    
    def _load_all_companies(self):
        """Load all company JSON files into memory"""
        if not self.data_dir.exists():
            print(f"⚠️  Company data directory not found: {self.data_dir}")
            return
        
        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    company_name = data.get("company", "").lower()
                    self.companies_cache[company_name] = data
                    print(f"  ✓ Loaded: {data.get('company')}")
            except Exception as e:
                print(f"  ✗ Error loading {json_file.name}: {e}")
        
        print(f"✓ Loaded {len(self.companies_cache)} companies")
    
    def get_company_questions(self, company_name: str, role: str) -> Dict:
        """
        Get questions for a specific company
        Returns curated list or AI-generated fallback
        """
        company_lower = company_name.lower()
        
        # Check cache first
        if company_lower in self.companies_cache:
            print(f"✓ Found curated data for {company_name}")
            return self._format_response(self.companies_cache[company_lower], role)
        
        # Fallback: Generate using AI
        print(f"⚠️  No curated data for {company_name}, generating with AI...")
        return self._generate_with_ai(company_name, role)
    
    def _format_response(self, company_data: Dict, role: str) -> Dict:
        """Format company data for response"""
        
        # Calculate recommended study time per topic
        topics_with_time = {}
        for topic, data in company_data["topics"].items():
            frequency = data["frequency"]
            time_hours = {
                "very_high": 15,
                "high": 10,
                "medium": 7,
                "low": 5
            }.get(frequency, 7)
            
            topics_with_time[topic] = {
                "questions": data["questions"],
                "frequency": frequency,
                "recommended_hours": time_hours,
                "question_count": len(data["questions"])
            }
        
        return {
            "company": company_data["company"],
            "data_source": "curated",
            "total_questions": company_data["total_questions"],
            "difficulty_distribution": company_data["difficulty_distribution"],
            "topics": topics_with_time,
            "system_design": company_data.get("system_design", []),
            "behavioral_focus": company_data.get("behavioral_focus", []),
            "role_specific_notes": self._get_role_notes(role)
        }
    
    def _generate_with_ai(self, company_name: str, role: str) -> Dict:
        """Generate question patterns using AI when company not in database"""
        
        prompt = f"""Generate a comprehensive interview preparation guide for {company_name} for the role of {role}.

Include:
1. Top 5 DSA topics frequently asked (with frequency: very_high/high/medium)
2. 3-5 specific question names per topic
3. 3 system design questions
4. Key behavioral focus areas

Return in this JSON format:
{{
  "company": "{company_name}",
  "topics": {{
    "Arrays": {{
      "frequency": "high",
      "questions": ["Two Sum", "3Sum", "..."],
      "recommended_hours": 10
    }},
    "Trees": {{ ... }}
  }},
  "system_design": ["Design X", "Design Y"],
  "behavioral_focus": ["Focus area 1", "Focus area 2"]
}}

Return ONLY valid JSON, no other text."""

        try:
            result = self.llm_service.generate_content(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2000,
                preferred_provider='groq'  # Fast generation
            )
            
            if result['success']:
                # Clean and parse JSON
                import re
                content = result['text']
                # Remove common Markdown code fences like ```json or ```
                content = re.sub(r'^\s*```(?:[\w+\-]*)\s*', '', content, flags=re.MULTILINE)
                content = re.sub(r'\s*```\s*$', '', content, flags=re.MULTILINE)
                # If there is extra surrounding text, try to extract the first JSON object
                m = re.search(r'(\{.*\})', content, flags=re.DOTALL)
                if m:
                    content = m.group(1)
                
                generated_data = json.loads(content.strip())
                generated_data["data_source"] = "ai_generated"
                generated_data["role_specific_notes"] = self._get_role_notes(role)
                
                return generated_data
            else:
                return self._get_fallback_response(company_name, role)
                
        except Exception as e:
            print(f"❌ AI generation failed: {e}")
            return self._get_fallback_response(company_name, role)
    
    def _get_fallback_response(self, company_name: str, role: str) -> Dict:
        """Basic fallback when everything else fails"""
        return {
            "company": company_name,
            "data_source": "fallback",
            "message": "Company-specific data not available. Using general preparation guide.",
            "topics": {
                "Arrays": {
                    "frequency": "high",
                    "questions": ["Two Sum", "Best Time to Buy and Sell Stock", "Contains Duplicate"],
                    "recommended_hours": 10
                },
                "LinkedList": {
                    "frequency": "medium",
                    "questions": ["Reverse Linked List", "Merge Two Sorted Lists"],
                    "recommended_hours": 7
                },
                "Trees": {
                    "frequency": "high",
                    "questions": ["Binary Tree Inorder Traversal", "Validate BST"],
                    "recommended_hours": 10
                },
                "Dynamic Programming": {
                    "frequency": "high",
                    "questions": ["Climbing Stairs", "Coin Change"],
                    "recommended_hours": 12
                }
            },
            "system_design": [
                "Design URL Shortener",
                "Design Twitter Feed",
                "Design Cache System"
            ],
            "behavioral_focus": [
                "Problem-solving approach",
                "Teamwork examples",
                "Leadership experience"
            ],
            "role_specific_notes": self._get_role_notes(role)
        }
    
    def _get_role_notes(self, role: str) -> str:
        """Get role-specific preparation notes"""
        role_lower = role.lower()
        
        if "sde" in role_lower or "software" in role_lower:
            return "Focus heavily on DSA (70%), System Design (20%), and Behavioral (10%)"
        elif "data analyst" in role_lower:
            return "Focus on SQL (40%), Statistics (30%), Data Structures (20%), Behavioral (10%)"
        elif "qa" in role_lower or "test" in role_lower:
            return "Focus on Testing Concepts (40%), Automation (30%), Basic DSA (20%), Behavioral (10%)"
        elif "data engineer" in role_lower:
            return "Focus on SQL (30%), System Design (30%), ETL (20%), DSA (20%)"
        else:
            return "Balanced preparation across DSA, System Design, and Behavioral"
    
    def get_available_companies(self) -> list:
        """Get list of companies with curated data"""
        return [data["company"] for data in self.companies_cache.values()]
