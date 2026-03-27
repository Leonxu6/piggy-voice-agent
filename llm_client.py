"""
LLM Client - Connects to MiniMax M2.7 for chat
"""

import os
import logging

logger = logging.getLogger(__name__)

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_API_URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
MODEL = "MiniMax-M2.7"


class LLMClient:
    """Client for MiniMax LLM API"""
    
    def __init__(self):
        self.api_key = MINIMAX_API_KEY
        self.api_url = MINIMAX_API_URL
        self.model = MODEL
        self.conversation_history = {}
    
    async def chat(self, prompt: str, user_id: str = None) -> str:
        """
        Send a chat request to MiniMax LLM
        """
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": self.model,
            "messages": messages
        }
        
        try:
            resp = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            data = resp.json()
            
            if data.get("base_resp", {}).get("status_code") != 0:
                error = data.get("base_resp", {}).get("status_msg", "Unknown error")
                logger.error(f"LLM API error: {error}")
                return f"抱歉，处理失败了: {error}"
            
            choices = data.get("choices", [{}])
            if choices:
                return choices[0].get("messages", [{}])[0].get("content", "")
            
            return "抱歉，没有得到回复。"
            
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return f"抱歉，请求失败了: {str(e)}"
    
    async def chat_with_history(self, user_id: str, user_message: str) -> str:
        """
        Chat with conversation history
        """
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        history = self.conversation_history[user_id]
        history.append({"role": "user", "content": user_message})
        
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": history[-10:]  # Last 10 messages
        }
        
        try:
            resp = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            data = resp.json()
            
            if data.get("base_resp", {}).get("status_code") != 0:
                return f"抱歉，处理失败了"
            
            choices = data.get("choices", [{}])
            if choices:
                assistant_reply = choices[0].get("messages", [{}])[0].get("content", "")
                history.append({"role": "assistant", "content": assistant_reply})
                return assistant_reply
            
            return "抱歉，没有得到回复。"
            
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return f"抱歉，请求失败了: {str(e)}"
