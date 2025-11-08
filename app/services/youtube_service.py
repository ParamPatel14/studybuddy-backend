import json
from pathlib import Path
from typing import List, Dict, Optional

class YouTubeResourceService:
    """
    Simple YouTube resource service using curated JSON files
    100% FREE - No API needed
    """
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data" / "youtube_resources"
        self.resources_cache = {}
        self._load_all_resources()
    
    def _load_all_resources(self):
        """Load all YouTube resource files"""
        
        if not self.data_dir.exists():
            print(f"⚠️  YouTube resources directory not found: {self.data_dir}")
            print(f"   Creating directory...")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            return
        
        loaded_count = 0
        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    topic = data.get("topic", "").lower()
                    self.resources_cache[topic] = data.get("resources", [])
                    loaded_count += 1
                    print(f"  ✓ Loaded: {data.get('topic')} ({len(data.get('resources', []))} videos)")
            except Exception as e:
                print(f"  ✗ Error loading {json_file.name}: {e}")
        
        if loaded_count > 0:
            print(f"✓ Loaded YouTube resources for {loaded_count} topics")
        else:
            print("⚠️  No YouTube resource files found. Create JSON files in app/data/youtube_resources/")
    
    def get_topic_videos(
        self, 
        topic: str, 
        max_results: int = 3,
        difficulty: Optional[str] = None
    ) -> List[Dict]:
        """
        Get YouTube videos for a topic
        """
        
        topic_lower = topic.lower().replace(' ', '_')
        
        print(f"\n🔍 Searching for: {topic}")
        print(f"   Looking for key: {topic_lower}")
        print(f"   Available topics: {list(self.resources_cache.keys())}")
        
        # Try exact match
        if topic_lower in self.resources_cache:
            print(f"   ✓ Found exact match!")
            videos = self.resources_cache[topic_lower]
        else:
            # Try fuzzy match
            print(f"   Trying fuzzy match...")
            videos = self._fuzzy_search(topic)
        
        if not videos:
            print(f"   ✗ No videos found for: {topic}")
            return []
        
        # Filter by difficulty if specified
        if difficulty:
            videos = [v for v in videos if difficulty.lower() in v.get('difficulty', '')]
        
        print(f"   ✓ Returning {min(len(videos), max_results)} videos")
        
        # Limit results
        return videos[:max_results]
    
    def _fuzzy_search(self, topic: str) -> List[Dict]:
        """Search for topic with fuzzy matching"""
        
        topic_lower = topic.lower()
        
        # Try partial matches
        for key in self.resources_cache.keys():
            if topic_lower in key or key in topic_lower:
                print(f"   ✓ Fuzzy match found: {key}")
                return self.resources_cache[key]
        
        # Try word-by-word match
        topic_words = topic_lower.split()
        for key in self.resources_cache.keys():
            if any(word in key for word in topic_words):
                print(f"   ✓ Word match found: {key}")
                return self.resources_cache[key]
        
        return []
    
    def get_all_topics(self) -> List[str]:
        """Get list of all topics with resources"""
        return [topic.replace('_', ' ').title() for topic in self.resources_cache.keys()]
