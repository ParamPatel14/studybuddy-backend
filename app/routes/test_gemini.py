from fastapi import APIRouter
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/test", tags=["testing"])
ai_service = AIService()

@router.post("/gemini-test")
async def test_gemini(prompt: str):
    """Test Gemini API connection"""
    try:
        from google import genai
        from app.config.settings import settings
        
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model="gemini-2.5-pro-preview-03-25",
            contents=prompt
        )
        
        return {
            "status": "success",
            "model": "gemini-2.5-pro",
            "response": response.text,
            "usage": {
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/gemini-models")
async def list_available_models():
    """List available Gemini models"""
    try:
        from google import genai
        from app.config.settings import settings
        
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        models = []
        for model in client.models.list():
            models.append({
                "name": model.name,
                "display_name": model.display_name if hasattr(model, 'display_name') else model.name,
            })
        
        return {
            "status": "success",
            "available_models": models
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
