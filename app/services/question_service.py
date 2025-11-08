from google import genai
from google.genai import types
from app.config.settings import settings
import json
import re
import time
from typing import List, Dict
from app.models.models import Question, MCQOption, WrittenAnswer, Topic
from sqlalchemy.orm import Session

class QuestionService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Use more stable model
        self.model = "gemini-2.0-flash-exp"
        
        print(f"✓ QuestionService initialized with model: {self.model}")
    
    def _clean_json_response(self, content: str) -> str:
        """Remove markdown formatting"""
        if not content:
            return "{}"
        
        # Remove code blocks
        content = re.sub(r'^```', '', content)
        content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*```$', '', content)
        
        return content.strip()
    
    def _retry_with_backoff(self, func, max_retries=3):
        """Retry function with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise
    
    async def generate_mcqs(
        self, 
        topic: Topic, 
        difficulty: str, 
        count: int = 10,
        db: Session = None
    ) -> List[Question]:
        """Generate MCQ questions using Gemini"""
        
        print(f"\n{'='*60}")
        print(f"🎯 Generating {count} MCQs")
        print(f"   Topic: {topic.name}")
        print(f"   Difficulty: {difficulty}")
        print(f"{'='*60}")
        
        # Simplified prompt that Gemini understands better
        prompt = f"""Generate {count} multiple-choice questions about "{topic.name}" at {difficulty} difficulty level.

RULES:
1. Each question must have exactly 4 options labeled A, B, C, D
2. Only ONE option should be correct
3. Include a brief explanation for the correct answer
4. Questions should test understanding, not just memorization

FORMAT YOUR RESPONSE AS VALID JSON ONLY (no markdown, no extra text):
{{
  "questions": [
    {{
      "question": "What is the definition of X?",
      "options": [
        {{"label": "A", "text": "First option", "is_correct": false}},
        {{"label": "B", "text": "Second option", "is_correct": true}},
        {{"label": "C", "text": "Third option", "is_correct": false}},
        {{"label": "D", "text": "Fourth option", "is_correct": false}}
      ],
      "explanation": "B is correct because..."
    }}
  ]
}}

Generate exactly {count} questions now:"""

        try:
            # Function to call API
            def call_api():
                print("📤 Sending request to Gemini...")
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        top_p=0.95,
                        top_k=40,
                        max_output_tokens=4096,
                        response_mime_type="application/json"  # Force JSON response
                    )
                )
                
                return response
            
            # Retry with backoff
            response = self._retry_with_backoff(call_api)
            
            if not response:
                raise Exception("No response from Gemini API")
            
            # Check response
            if not hasattr(response, 'text') or not response.text:
                print(f"⚠️ Empty response. Response object: {response}")
                
                # Try to get from candidates
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates
                    if hasattr(candidate, 'content'):
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            content = candidate.content.parts.text
                        else:
                            raise Exception("No text in candidate content")
                    else:
                        raise Exception("No content in candidate")
                else:
                    raise Exception("Empty response from Gemini - no candidates")
            else:
                content = response.text
            
            print(f"✓ Received response ({len(content)} chars)")
            print(f"   Preview: {content[:200]}...")
            
            # Clean and parse JSON
            content = self._clean_json_response(content)
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"   Content: {content[:500]}")
                raise Exception(f"Failed to parse JSON response: {e}")
            
            questions_data = result.get("questions", [])
            
            if not questions_data:
                raise Exception("No questions found in response")
            
            print(f"✓ Parsed {len(questions_data)} questions")
            
            # Save to database
            saved_questions = []
            for i, q_data in enumerate(questions_data, 1):
                print(f"   Saving question {i}/{len(questions_data)}...")
                
                question = Question(
                    topic_id=topic.id,
                    question_type="mcq",
                    difficulty=difficulty,
                    question_text=q_data["question"],
                    marks=1,
                    time_limit=60
                )
                db.add(question)
                db.flush()
                
                # Add options
                for opt in q_data["options"]:
                    option = MCQOption(
                        question_id=question.id,
                        option_label=opt["label"],
                        option_text=opt["text"],
                        is_correct=opt["is_correct"],
                        explanation=q_data.get("explanation") if opt["is_correct"] else None
                    )
                    db.add(option)
                
                saved_questions.append(question)
            
            db.commit()
            print(f"✅ Successfully saved {len(saved_questions)} MCQs to database")
            return saved_questions
            
        except Exception as e:
            db.rollback()
            print(f"\n❌ Error generating MCQs:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def generate_written_questions(
        self,
        topic: Topic,
        difficulty: str,
        count: int = 5,
        db: Session = None
    ) -> List[Question]:
        """Generate written questions using Gemini"""
        
        print(f"\n{'='*60}")
        print(f"📝 Generating {count} written questions")
        print(f"   Topic: {topic.name}")
        print(f"   Difficulty: {difficulty}")
        print(f"{'='*60}")
        
        marks_by_difficulty = {
            "easy": 5,
            "medium": 10,
            "hard": 15
        }
        
        marks = marks_by_difficulty.get(difficulty, 10)
        
        prompt = f"""Generate {count} exam-style written questions about "{topic.name}" at {difficulty} difficulty level.

Each question should be worth {marks} marks and require a detailed written answer.

FORMAT YOUR RESPONSE AS VALID JSON ONLY:
{{
  "questions": [
    {{
      "question": "Explain the concept of X in detail.",
      "marks": {marks},
      "time_minutes": {marks + 2},
      "model_answer": {{
        "introduction": "Brief 2-3 sentence introduction...",
        "main_body": "Detailed explanation covering all key points...",
        "conclusion": "Summary statement..."
      }},
      "marking_scheme": {{
        "introduction": 2,
        "main_body": {marks - 3},
        "conclusion": 1
      }},
      "keywords": [
        {{"word": "key concept 1", "importance": "high"}},
        {{"word": "supporting idea", "importance": "medium"}}
      ],
      "expected_length": "200-250 words"
    }}
  ]
}}

Generate exactly {count} questions now:"""

        try:
            def call_api():
                print("📤 Sending request to Gemini...")
                return self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.6,
                        top_p=0.95,
                        max_output_tokens=4096,
                        response_mime_type="application/json"
                    )
                )
            
            response = self._retry_with_backoff(call_api)
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini")
            
            content = self._clean_json_response(response.text)
            print(f"✓ Received response ({len(content)} chars)")
            
            result = json.loads(content)
            questions_data = result.get("questions", [])
            
            print(f"✓ Parsed {len(questions_data)} questions")
            
            # Save to database
            saved_questions = []
            for i, q_data in enumerate(questions_data, 1):
                print(f"   Saving question {i}/{len(questions_data)}...")
                
                question = Question(
                    topic_id=topic.id,
                    question_type="written",
                    difficulty=difficulty,
                    question_text=q_data["question"],
                    marks=q_data.get("marks", marks),
                    time_limit=q_data.get("time_minutes", marks + 2) * 60
                )
                db.add(question)
                db.flush()
                
                # Combine model answer
                model_answer_parts = q_data.get("model_answer", {})
                full_answer = f"{model_answer_parts.get('introduction', '')}\n\n{model_answer_parts.get('main_body', '')}\n\n{model_answer_parts.get('conclusion', '')}"
                
                written_answer = WrittenAnswer(
                    question_id=question.id,
                    model_answer=full_answer,
                    marking_scheme=q_data.get("marking_scheme", {}),
                    keywords=q_data.get("keywords", []),
                    expected_length=q_data.get("expected_length", "200-300 words")
                )
                db.add(written_answer)
                saved_questions.append(question)
            
            db.commit()
            print(f"✅ Successfully saved {len(saved_questions)} written questions")
            return saved_questions
            
        except Exception as e:
            db.rollback()
            print(f"\n❌ Error generating written questions:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def evaluate_written_answer(
        self,
        question: Question,
        student_answer: str,
        model_answer: str,
        marking_scheme: Dict,
        keywords: List[Dict]
    ) -> Dict:
        """Evaluate student's written answer using Gemini"""
        
        print(f"\n{'='*60}")
        print(f"📊 Evaluating written answer")
        print(f"   Question ID: {question.id}")
        print(f"   Answer length: {len(student_answer)} chars")
        print(f"{'='*60}")
        
        prompt = f"""Grade this student's exam answer.

QUESTION ({question.marks} marks):
{question.question_text}

MODEL ANSWER:
{model_answer}

MARKING SCHEME:
{json.dumps(marking_scheme, indent=2)}

KEYWORDS TO CHECK:
{json.dumps(keywords, indent=2)}

STUDENT'S ANSWER:
{student_answer}

INSTRUCTIONS:
1. Compare student's answer with model answer
2. Check for keyword coverage
3. Assess structure and clarity
4. Identify strengths and areas for improvement

FORMAT YOUR RESPONSE AS VALID JSON:
{{
  "score": 7.5,
  "max_score": {question.marks},
  "feedback": "Detailed paragraph explaining the grade...",
  "strengths": ["Point 1 done well", "Point 2 covered"],
  "improvements": ["Missing concept X", "Could expand on Y"],
  "keyword_coverage": 6,
  "keyword_total": {len(keywords)}
}}

Provide evaluation now:"""

        try:
            def call_api():
                return self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        response_mime_type="application/json"
                    )
                )
            
            response = self._retry_with_backoff(call_api)
            
            if not response or not response.text:
                raise Exception("Empty evaluation response")
            
            content = self._clean_json_response(response.text)
            result = json.loads(content)
            
            print(f"✓ Evaluation complete: {result['score']}/{result['max_score']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Evaluation error: {e}")
            # Fallback to basic evaluation
            return self._fallback_evaluation(student_answer, keywords, question.marks)
    
    def _fallback_evaluation(self, student_answer: str, keywords: List[Dict], max_marks: int) -> Dict:
        """Basic keyword-based evaluation as fallback"""
        answer_lower = student_answer.lower()
        
        keywords_found = sum(1 for kw in keywords if kw['word'].lower() in answer_lower)
        keyword_percentage = (keywords_found / len(keywords)) if keywords else 0
        score = round(max_marks * keyword_percentage, 1)
        
        return {
            "score": score,
            "max_score": max_marks,
            "feedback": f"Your answer covered {keywords_found} out of {len(keywords)} key concepts. Try to include more relevant terminology and expand on the main ideas.",
            "strengths": ["Answer attempted", "Used some relevant terms"] if keywords_found > 0 else ["Answer provided"],
            "improvements": ["Include more key concepts", "Provide more detailed explanation", "Add examples"],
            "keyword_coverage": keywords_found,
            "keyword_total": len(keywords)
        }
