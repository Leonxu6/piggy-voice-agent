"""
Memory - Persistent conversation memory for each user
"""

import json
import os
from pathlib import Path
from datetime import datetime


class Memory:
    """Persistent memory for user conversations"""
    
    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def get_file_path(self, user_id: str) -> Path:
        """Get storage file path for user"""
        return self.storage_dir / f"{user_id}.json"
    
    def get_conversation(self, user_id: str) -> list:
        """Load conversation history for user"""
        file_path = self.get_file_path(user_id)
        
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("messages", [])
            except Exception:
                return []
        
        return []
    
    def save_conversation(self, user_id: str, messages: list):
        """Save conversation history for user"""
        file_path = self.get_file_path(user_id)
        
        data = {
            "user_id": user_id,
            "updated_at": datetime.now().isoformat(),
            "messages": messages[-100:]  # Keep last 100 messages
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_message(self, user_id: str, role: str, content: str):
        """Add a single message to conversation"""
        messages = self.get_conversation(user_id)
        messages.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
        self.save_conversation(user_id, messages)
    
    def get_user_info(self, user_id: str) -> dict:
        """Get stored user info"""
        file_path = self.get_file_path(user_id)
        
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        
        return {}
    
    def set_user_preference(self, user_id: str, key: str, value):
        """Set user preference"""
        info = self.get_user_info(user_id)
        
        if "preferences" not in info:
            info["preferences"] = {}
        
        info["preferences"][key] = value
        info["updated_at"] = datetime.now().isoformat()
        
        with open(self.get_file_path(user_id), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    
    def add_research(self, user_id: str, topic: str, result):
        """Save research result for user"""
        from datetime import datetime
        file_path = self.storage_dir / f"{user_id}_research.json"
        
        research_history = []
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    research_history = json.load(f)
            except:
                pass
        
        research_history.append({
            "topic": topic,
            "summary": getattr(result, 'summary', str(result)),
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep last 50 researches
        research_history = research_history[-50:]
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(research_history, f, ensure_ascii=False, indent=2)
