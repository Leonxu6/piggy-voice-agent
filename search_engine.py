"""
Search Engine - Multi-source search (no page reading needed)
Uses LLM to synthesize directly from search results.
"""

import asyncio
import requests
import re
import json
from typing import List, Dict

import logging
logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Multi-source search optimized for LLM synthesis.
    The LLM can understand search snippets without needing full page content.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    async def search(self, query: str) -> List[Dict]:
        """Search multiple sources and return comprehensive results"""
        results = []
        
        tasks = [
            self._search_hackernews(query),
            self._search_news(query),
        ]
        
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for task_result in task_results:
            if isinstance(task_result, list):
                results.extend(task_result)
        
        return results
    
    async def _search_hackernews(self, query: str) -> List[Dict]:
        """Search HackerNews"""
        try:
            url = f'https://hn.algolia.com/api/v1/search?query={quote(query)}&tags=story&hitsPerPage=10'
            resp = await asyncio.to_thread(self.session.get, url, timeout=10)
            data = resp.json()
            
            results = []
            for hit in data.get('hits', [])[:8]:
                results.append({
                    'source': 'HackerNews',
                    'title': hit.get('title', ''),
                    'url': hit.get('url', '') or f'https://news.ycombinator.com/item?id={hit.get("objectID")}',
                    'score': hit.get('points', 0),
                    'snippet': f"{hit.get('title', '')} - {hit.get('points', 0)} points",
                    'content': hit.get('title', '') + '. ' + hit.get('author', '')
                })
            return results
        except Exception as e:
            logger.warning(f"HN failed: {e}")
            return []
    
    async def _search_reddit(self, query: str) -> List[Dict]:
        """Search Reddit"""
        try:
            url = f'https://www.reddit.com/search.json?q={quote(query)}&sort=top&limit=8'
            resp = await asyncio.to_thread(self.session.get, url, timeout=10)
            data = resp.json()
            
            results = []
            for post in data.get('data', {}).get('children', []):
                post_data = post.get('data', {})
                results.append({
                    'source': 'Reddit',
                    'title': post_data.get('title', ''),
                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                    'score': post_data.get('score', 0),
                    'snippet': f"{post_data.get('title', '')} (↑{post_data.get('score', 0)})",
                    'content': post_data.get('selftext', '')[:500] or post_data.get('title', '')
                })
            return results
        except Exception as e:
            logger.warning(f"Reddit failed: {e}")
            return []
    
    async def _search_news(self, query: str) -> List[Dict]:
        """Search Google News via RSS"""
        try:
            url = f'https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en'
            resp = await asyncio.to_thread(self.session.get, url, timeout=10)
            
            titles = re.findall(r'<title><!\[CDATA\[([^\]]+)\]\]></title>', resp.text)
            links = re.findall(r'<link>([^<]+)</link>', resp.text)
            
            results = []
            for i, title in enumerate(titles[1:9]):
                if i < len(links):
                    results.append({
                        'source': 'News',
                        'title': title,
                        'url': links[i],
                        'snippet': title,
                        'content': title
                    })
            return results
        except Exception as e:
            logger.warning(f"News failed: {e}")
            return []
    
    def format_results_for_llm(self, results: List[Dict], query: str) -> str:
        """Format search results for LLM analysis"""
        if not results:
            return f"No search results found for: {query}"
        
        text = f"Search results for '{query}':\n\n"
        
        for i, r in enumerate(results[:10], 1):
            text += f"{i}. [{r.get('source', 'Unknown')}] {r.get('title', '')}\n"
            text += f"   URL: {r.get('url', '')}\n"
            if r.get('score'):
                text += f"   Score: {r.get('score')}\n"
            if r.get('snippet'):
                text += f"   Summary: {r.get('snippet')}\n"
            text += "\n"
        
        return text


def quote(s):
    import urllib.parse
    return urllib.parse.quote(s)
