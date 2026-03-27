"""
Search Engine - Multi-source async search
Uses LLM to synthesize directly from search results.
"""

import asyncio
import re
from typing import List, Dict, Callable, Optional

import httpx
import logging

logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Multi-source async search optimized for LLM synthesis.
    All HTTP calls are truly async via httpx.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of async HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/html, */*',
                },
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search(
        self,
        query: str,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Dict]:
        """
        Search multiple sources in parallel and return comprehensive results.
        Calls HackerNews + Reddit + News concurrently.
        Optionally reports status via callback.
        """
        results = []

        if status_callback:
            status_callback(f"🔍 正在搜索 HackerNews...")

        tasks = [
            self._search_hackernews(query),
            self._search_reddit(query),
            self._search_news(query),
        ]

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        source_names = ['HackerNews', 'Reddit', 'News']
        for src_name, task_result in zip(source_names, task_results):
            if isinstance(task_result, list):
                results.extend(task_result)
                logger.info(f"{src_name}: {len(task_result)} results")
            elif isinstance(task_result, Exception):
                logger.warning(f"{src_name} failed: {task_result}")

        return results

    async def _search_hackernews(self, query: str) -> List[Dict]:
        """Search HackerNews via Algolia API"""
        try:
            client = await self._get_client()
            url = f'https://hn.algolia.com/api/v1/search?query={self._quote(query)}&tags=story&hitsPerPage=8'
            resp = await client.get(url)
            data = resp.json()

            results = []
            for hit in data.get('hits', [])[:8]:
                title = hit.get('title', '')
                if not title:
                    continue
                obj_id = hit.get('objectID', '')
                url_val = hit.get('url', '') or f'https://news.ycombinator.com/item?id={obj_id}'
                results.append({
                    'source': 'HackerNews',
                    'title': title,
                    'url': url_val,
                    'score': hit.get('points', 0),
                    'snippet': f"{title} — {hit.get('points', 0)} points, by {hit.get('author', 'unknown')}",
                    'content': title,
                })
            return results
        except Exception as e:
            logger.warning(f"HN failed: {e}")
            return []

    async def _search_reddit(self, query: str) -> List[Dict]:
        """Search Reddit via JSON API"""
        try:
            client = await self._get_client()
            url = f'https://www.reddit.com/search.json?q={self._quote(query)}&sort=top&limit=6'
            resp = await client.get(url, headers={'Accept-Language': 'en-US'})
            data = resp.json()

            results = []
            for post in data.get('data', {}).get('children', [])[:6]:
                post_data = post.get('data', {})
                title = post_data.get('title', '')
                if not title:
                    continue
                permalink = post_data.get('permalink', '')
                score = post_data.get('score', 0)
                num_comments = post_data.get('num_comments', 0)
                subreddit = post_data.get('subreddit', '')
                results.append({
                    'source': f'Reddit r/{subreddit}',
                    'title': title,
                    'url': f"https://reddit.com{permalink}",
                    'score': score,
                    'snippet': f"{title} (↑{score}, 💬{num_comments})",
                    'content': post_data.get('selftext', '')[:400] or title,
                })
            return results
        except Exception as e:
            logger.warning(f"Reddit failed: {e}")
            return []

    async def _search_news(self, query: str) -> List[Dict]:
        """Search Google News via RSS"""
        try:
            client = await self._get_client()
            url = f'https://news.google.com/rss/search?q={self._quote(query)}&hl=en-US&gl=US&ceid=US:en'
            resp = await client.get(url)

            titles = re.findall(r'<title><!\[CDATA\[([^\]]+)\]\]></title>', resp.text)
            links = re.findall(r'<link>([^<]+)</link>', resp.text)
            # Skip first title (search term itself) and last dummy link
            results = []
            for i, title in enumerate(titles[1:9]):
                if i < len(links) and title and title != 'https://news.google.com':
                    results.append({
                        'source': 'News',
                        'title': title,
                        'url': links[i],
                        'snippet': title,
                        'content': title,
                    })
            return results
        except Exception as e:
            logger.warning(f"News failed: {e}")
            return []

    def format_results_for_llm(self, results: List[Dict], query: str) -> str:
        """Format search results for LLM analysis"""
        if not results:
            return f"No search results found for: {query}"

        # Group by source
        by_source: Dict[str, List[Dict]] = {}
        for r in results:
            src = r.get('source', 'Unknown')
            by_source.setdefault(src, []).append(r)

        text = f"关于「{query}」的搜索结果（共 {len(results)} 条，来自 {len(by_source)} 个来源）:\n\n"

        for source, items in by_source.items():
            text += f"【{source}】（{len(items)}条）\n"
            for r in items[:4]:
                text += f"  • {r.get('title', '')}\n"
                if r.get('score'):
                    text += f"    热度: {r.get('score')}\n"
                text += f"    链接: {r.get('url', '')}\n"
                if r.get('snippet') and r.get('snippet') != r.get('title'):
                    text += f"    摘要: {r.get('snippet')}\n"
            text += "\n"

        return text

    @staticmethod
    def _quote(s: str) -> str:
        import urllib.parse
        return urllib.parse.quote(s)
