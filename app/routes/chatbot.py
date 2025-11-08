from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.models import StudyPlan, UploadedFile, Topic
from app.services.llm_service import LLMService
from pydantic import BaseModel
from typing import Dict, List, Optional
import json

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])
llm_service = LLMService()

# In-memory conversation storage (use Redis in production)
conversation_histories: Dict[str, List[Dict]] = {}

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatQuery(BaseModel):
    query: str
    plan_id: Optional[int] = None
    user_id: int = 1
    context: Optional[str] = None

class QuickHelpRequest(BaseModel):
    topic: str
    help_type: str  # "explain", "example", "tips", "mistakes"

# ============================================================================
# MAIN CHATBOT ENDPOINTS
# ============================================================================

@router.post("/query")
async def chat_query(
    query_data: ChatQuery,
    db: Session = Depends(get_db)
):
    """
    Universal chatbot query handler
    Works globally across all pages (exam prep, placement, peer learning)
    """
    try:
        print(f"\n{'='*60}")
        print(f"💬 Chatbot Query")
        print(f"   User: {query_data.user_id}")
        print(f"   Plan ID: {query_data.plan_id}")
        print(f"   Context: {query_data.context}")
        print(f"   Question: {query_data.query}")
        print(f"{'='*60}")
        
        # Build context based on plan_id and page context
        system_context = ""
        study_context = ""
        
        # If plan_id provided, get study-specific context
        if query_data.plan_id:
            study_plan = db.query(StudyPlan).filter(
                StudyPlan.id == query_data.plan_id
            ).first()
            
            if study_plan:
                # Get uploaded files for context
                uploaded_files = db.query(UploadedFile).filter(
                    UploadedFile.plan_id == query_data.plan_id
                ).all()
                
                if uploaded_files:
                    study_context += "\n**Available Study Materials:**\n"
                    for file in uploaded_files[:3]:
                        if file.extracted_text:
                            study_context += f"\n--- {file.filename} ---\n"
                            study_context += file.extracted_text[:1500]
                
                # Get topics
                topics = db.query(Topic).filter(
                    Topic.plan_id == query_data.plan_id
                ).all()
                
                if topics:
                    topics_list = ", ".join([t.name for t in topics])
                    study_context += f"\n\n**Topics in study plan:** {topics_list}"
                
                system_context = f"""You are helping a student prepare for their {study_plan.exam_type} exam in {study_plan.subject}.
Target grade: {study_plan.target_grade}
Exam date: {study_plan.exam_date}"""
        
        # Add page context
        if query_data.context:
            if "placement" in query_data.context.lower():
                system_context += "\n\nUser is currently on placement preparation page. Focus on interview prep, DSA, system design, and behavioral questions."
            elif "exam" in query_data.context.lower():
                system_context += "\n\nUser is currently on exam preparation page. Focus on concepts, theory, and exam strategies."
            elif "peer" in query_data.context.lower():
                system_context += "\n\nUser is on peer learning page. Help with collaborative study, group activities, and peer discussion topics."
        
        # Get conversation history
        conversation_key = f"{query_data.user_id}_{query_data.plan_id or 'global'}"
        history = conversation_histories.get(conversation_key, [])
        
        # Build conversation history text
        history_text = ""
        if history:
            history_text = "\n**Recent conversation:**\n"
            for msg in history[-4:]:  # Last 4 messages
                history_text += f"Student: {msg['question']}\nYou: {msg['answer'][:100]}...\n"
        
        # Build complete system prompt
        system_prompt = f"""You are an expert AI study tutor and mentor. You help students with:
- Exam preparation (concepts, examples, practice)
- Placement/interview preparation (DSA, system design, behavioral)
- Peer learning and collaboration
- General academic help

{system_context}

{study_context}

**Your Response Style:**
- Clear and concise (under 200 words unless complex topic)
- Use examples and analogies
- Provide code snippets when relevant
- Be encouraging and supportive
- Use bullet points for clarity
- If you don't know something, say so honestly

{history_text}"""

        full_prompt = f"{system_prompt}\n\n**Student Question:** {query_data.query}\n\n**Your Answer:**"
        
        # Call LLM (prefer Groq for speed in chatbot)
        result = llm_service.generate_content(
            prompt=full_prompt,
            temperature=0.7,
            max_tokens=500,
            preferred_provider='groq'
        )
        
        if not result['success']:
            return {
                "response": "I'm having trouble processing that. Could you rephrase or try again?",
                "error": True
            }
        
        answer = result['text'].strip()
        
        # Store in conversation history
        if conversation_key not in conversation_histories:
            conversation_histories[conversation_key] = []
        
        conversation_histories[conversation_key].append({
            "question": query_data.query,
            "answer": answer,
            "provider": result['provider']
        })
        
        # Limit history to last 20 messages
        if len(conversation_histories[conversation_key]) > 20:
            conversation_histories[conversation_key] = conversation_histories[conversation_key][-20:]
        
        print(f"✓ Response generated ({len(answer)} chars)")
        print(f"   Provider: {result['provider']}")
        
        return {
            "response": answer,
            "provider": result['provider'],
            "has_context": bool(study_context),
            "conversation_length": len(conversation_histories.get(conversation_key, []))
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "response": "Sorry, I encountered an error. Please try again.",
            "error": True
        }

# ============================================================================
# LEGACY ENDPOINT (for backward compatibility)
# ============================================================================

@router.post("/ask")
async def ask_question(
    question: str,
    plan_id: int,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint - redirects to new query endpoint
    Maintains backward compatibility with existing code
    """
    query_data = ChatQuery(
        query=question,
        plan_id=plan_id,
        user_id=user_id
    )
    
    result = await chat_query(query_data, db)
    
    return {
        "question": question,
        "answer": result.get("response", ""),
        "provider_used": result.get("provider", "unknown"),
        "has_context": result.get("has_context", False),
        "conversation_length": result.get("conversation_length", 0)
    }

# ============================================================================
# QUICK HELP & UTILITIES
# ============================================================================

@router.post("/quick-help")
async def get_quick_help(request: QuickHelpRequest):
    """Quick help prompts for specific topics"""
    
    prompts = {
        "explain": f"Explain {request.topic} in simple terms with a practical example. Keep it under 150 words.",
        "example": f"Provide a step-by-step example problem for {request.topic} with solution.",
        "tips": f"Give 3 study tips and memory tricks for learning {request.topic}.",
        "mistakes": f"What are the top 3 common mistakes students make when learning {request.topic}?"
    }
    
    question = prompts.get(request.help_type, f"Tell me about {request.topic}")
    
    result = llm_service.generate_content(
        prompt=question,
        temperature=0.7,
        max_tokens=400,
        preferred_provider='groq'
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])
    
    return {
        "topic": request.topic,
        "help_type": request.help_type,
        "answer": result['text'],
        "provider": result['provider']
    }

@router.post("/explain-code")
async def explain_code(
    code: str,
    language: str = "python"
):
    """Explain code snippet in simple terms"""
    
    prompt = f"""Explain this {language} code in simple terms:

Break it down:
1. What does it do? (1-2 sentences)
2. How does it work? (step by step)
3. Time & space complexity (if applicable)
4. Any potential improvements?

Keep it under 200 words."""

    result = llm_service.generate_content(
        prompt=prompt,
        temperature=0.5,
        max_tokens=500,
        preferred_provider='groq'
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])
    
    return {
        "code": code,
        "language": language,
        "explanation": result['text'],
        "provider": result['provider']
    }

@router.post("/solve-doubt")
async def solve_doubt(
    doubt: str,
    topic: str,
    difficulty: str = "medium"
):
    """
    Solve a specific doubt with detailed explanation
    """
    
    prompt = f"""A student has a doubt about {topic} (difficulty: {difficulty}).

Doubt: {doubt}

Provide a clear, detailed answer that:
1. Directly addresses their confusion
2. Explains the concept step-by-step
3. Gives a practical example
4. Suggests related topics to study

Keep it friendly and encouraging."""

    result = llm_service.generate_content(
        prompt=prompt,
        temperature=0.7,
        max_tokens=600,
        preferred_provider='groq'
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])
    
    return {
        "doubt": doubt,
        "topic": topic,
        "solution": result['text'],
        "provider": result['provider']
    }

# ============================================================================
# CONVERSATION MANAGEMENT
# ============================================================================

@router.get("/history/{user_id}/{plan_id}")
async def get_conversation_history(
    user_id: int,
    plan_id: int
):
    """Get conversation history for a specific plan"""
    conversation_key = f"{user_id}_{plan_id}"
    history = conversation_histories.get(conversation_key, [])
    
    return {
        "conversation_id": conversation_key,
        "message_count": len(history),
        "messages": history
    }

@router.delete("/history/{user_id}/{plan_id}")
async def clear_conversation_history(
    user_id: int,
    plan_id: int
):
    """Clear conversation history"""
    conversation_key = f"{user_id}_{plan_id}"
    if conversation_key in conversation_histories:
        del conversation_histories[conversation_key]
    
    return {"message": "Conversation history cleared"}

@router.delete("/history/all/{user_id}")
async def clear_all_history(user_id: int):
    """Clear all conversation history for a user"""
    keys_to_delete = [k for k in conversation_histories.keys() if k.startswith(f"{user_id}_")]
    for key in keys_to_delete:
        del conversation_histories[key]
    
    return {
        "message": f"Cleared {len(keys_to_delete)} conversation histories",
        "count": len(keys_to_delete)
    }

# ============================================================================
# SYSTEM INFO
# ============================================================================

@router.get("/providers")
async def get_available_providers():
    """Get list of available LLM providers and their status"""
    return {
        "available": llm_service.get_available_providers(),
        "default": llm_service.default_provider,
        "order": llm_service.provider_order,
        "active_conversations": len(conversation_histories)
    }

@router.get("/stats")
async def get_chatbot_stats():
    """Get chatbot usage statistics"""
    total_conversations = len(conversation_histories)
    total_messages = sum(len(msgs) for msgs in conversation_histories.values())
    
    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "avg_messages_per_conversation": total_messages / total_conversations if total_conversations > 0 else 0,
        "active_users": len(set(k.split('_')[0] for k in conversation_histories.keys()))
    }

@router.get("/health")
async def chatbot_health():
    """Check chatbot health"""
    providers = llm_service.get_available_providers()
    
    return {
        "status": "healthy" if providers else "degraded",
        "providers_available": len(providers),
        "providers": providers,
        "conversations_active": len(conversation_histories)
    }