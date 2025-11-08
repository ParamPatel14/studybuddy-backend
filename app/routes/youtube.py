from fastapi import APIRouter, HTTPException
from app.services.youtube_service import YouTubeResourceService
from typing import Optional

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

# Initialize service
try:
    youtube_service = YouTubeResourceService()
    print("✓ YouTube service initialized")
except Exception as e:
    print(f"✗ Failed to initialize YouTube service: {e}")
    youtube_service = None

@router.get("/recommend/{topic}")
async def recommend_videos(
    topic: str,
    max_results: int = 3,
    difficulty: Optional[str] = None
):
    """
    Get recommended YouTube videos for a topic
    Uses curated JSON files - 100% FREE
    """
    
    if not youtube_service:
        return {
            "error": "YouTube service not available",
            "topic": topic,
            "videos": []
        }
    
    try:
        print(f"\n{'='*60}")
        print(f"📺 YouTube Request")
        print(f"   Topic: {topic}")
        print(f"   Max Results: {max_results}")
        print(f"{'='*60}")
        
        videos = youtube_service.get_topic_videos(
            topic=topic,
            max_results=max_results,
            difficulty=difficulty
        )
        
        if not videos:
            return {
                "topic": topic,
                "videos": [],
                "message": f"No videos found for '{topic}'. Available topics: {', '.join(youtube_service.get_all_topics())}",
                "available_topics": youtube_service.get_all_topics()
            }
        
        return {
            "topic": topic,
            "videos": videos,
            "count": len(videos),
            "source": "curated"
        }
        
    except Exception as e:
        print(f"❌ Error in recommend_videos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topics")
async def get_all_topics():
    """Get list of all topics with YouTube resources"""
    
    if not youtube_service:
        return {"topics": [], "count": 0}
    
    topics = youtube_service.get_all_topics()
    return {
        "topics": topics,
        "count": len(topics)
    }
