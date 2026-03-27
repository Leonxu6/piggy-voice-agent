"""
LLM Client - MiniMax M2.7
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
API_URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2"


class LLMClient:
    """Simple LLM client"""
    
    def __init__(self):
        self.api_key = MINIMAX_API_KEY
        self.api_url = API_URL
    
    async def chat(self, prompt: str) -> str:
        """Send prompt, get response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "MiniMax-M2.7",
            "messages": [{"role": "user", "content": prompt}]
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
                logger.error(f"LLM error: {error}")
                return f"抱歉，发生了错误: {error}"
            
            choices = data.get("choices", [{}])
            if choices:
                return choices[0].get("messages", [{}])[0].get("content", "")
            
            return "抱歉，没有得到回复。"
            
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return f"抱歉，请求失败了: {str(e)}"
