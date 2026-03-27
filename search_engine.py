"""
Search Engine - Multi-source async search (EN + CN)
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
    Multi-source async search: English (HN, Reddit, News) + Chinese (Zhihu, Weibo, Baidu).
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
        Search EN + CN sources in parallel.
        Returns up to 20 results across all sources.
        """
        results = []

        if status_callback:
            await status_callback("🔍 正在搜索多语言来源...")

        tasks = [
            self._search_hackernews(query),
            self._search_reddit(query),
            self._search_news(query),
            self._search_zhihu(query),
            self._search_weibo(query),
            self._search_baidu_news(query),
        ]

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        source_map = {
            0: 'HackerNews',
            1: 'Reddit',
            2: 'News',
            3: '知乎',
            4: '微博',
            5: '百度新闻',
        }

        for idx, task_result in enumerate(task_results):
            src_name = source_map.get(idx, f'Source{idx}')
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
        """
        Format search results for LLM analysis.
        Includes source, credibility, and content.
        """
        if not results:
            return f"No search results found for: {query}"

        # Group by source
        by_source: dict = {}
        for r in results:
            src = r.get('source', 'Unknown')
            by_source.setdefault(src, []).append(r)

        cred_labels = {
            'high': '⭐高可信',
            'medium': '中可信',
            'verify': '⚠️需验证',
        }

        text = f"关于「{query}」的搜索结果（共 {len(results)} 条，来自 {len(by_source)} 个来源）:\n\n"

        for source, items in by_source.items():
            cred = items[0].get('credibility', 'medium')
            cred_label = cred_labels.get(cred, '')
            text += f"【{source}】（{len(items)}条，{cred_label}）\n"
            for r in items[:4]:
                text += f"  • {r.get('title', '')}\n"
                if r.get('score'):
                    text += f"    热度: {r.get('score')}\n"
                if r.get('snippet') and r.get('snippet') != r.get('title'):
                    text += f"    摘要: {r.get('snippet')[:150]}\n"
            text += "\n"

        return text

    async def _search_zhihu(self, query: str) -> List[Dict]:
        """Search Zhihu (Chinese Q&A platform) via Bing-like API"""
        try:
            client = await self._get_client()
            url = f'https://www.zhihu.com/api/v4/search_v3?t=general&q={self._quote(query)}&correction=1&offset=0&limit=10&filter_fields=&lc_idx=0&show_all_topics=0'
            resp = await client.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Referer': 'https://www.zhihu.com',
                    'Cookie': '',  # Zhihu may need cookie for API; fallback gracefully
                },
                timeout=10,
            )
            data = resp.json()
            results = []
            for item in data.get('data', [])[:6]:
                obj = item.get('object', {})
                title = obj.get('title', '') or obj.get('question', {}).get('title', '') or item.get('highlight', {}).get('title', '')
                if not title:
                    continue
                excerpt = obj.get('excerpt', '') or item.get('highlight', {}).get('description', '')
                url_val = obj.get('url', '') or f"https://www.zhihu.com/question/{obj.get('question', {}).get('id', '')}"
                results.append({
                    'source': '知乎',
                    'title': title,
                    'url': url_val,
                    'score': obj.get('voteup_count', 0),
                    'snippet': excerpt[:200] if excerpt else title,
                    'content': excerpt[:400] if excerpt else title,
                    'credibility': 'high' if obj.get('voteup_count', 0) > 100 else 'medium',
                })
            return results
        except Exception as e:
            logger.warning(f"Zhihu failed: {e}")
            return []

    async def _search_weibo(self, query: str) -> List[Dict]:
        """Search Weibo (Chinese social media) via public search"""
        try:
            client = await self._get_client()
            # Weibo search page (no auth API) - extract via mobile search
            url = f'https://m.weibo.cn/api/container/getIndex?q={self._quote(query)}&type=wb&containerid=100103type%3D1%26q%3D{self._quote(query)}'
            resp = await client.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
                    'Accept': 'application/json',
                    'Referer': 'https://m.weibo.cn',
                },
                timeout=10,
            )
            data = resp.json()
            results = []
            cards = data.get('data', {}).get('cards', [])
            for card in cards:
                if card.get('card_type') != 9:
                    continue
                mblog = card.get('mblog', {})
                title = mblog.get('text', '')[:100] or mblog.get('raw_text', '')[:100]
                if not title:
                    continue
                user = mblog.get('user', {})
                reposts = mblog.get('reposts_count', 0)
                comments = mblog.get('comments_count', 0)
                results.append({
                    'source': f'微博 @{user.get("screen_name", "用户")}',
                    'title': title,
                    'url': f"https://weibo.com/{mblog.get('id', '')}",
                    'score': reposts + comments,
                    'snippet': f"转发{reposts} 评论{comments}：{title}",
                    'content': mblog.get('text', '')[:400],
                    'credibility': 'verify',  # Social media - lower weight
                })
            return results[:5]
        except Exception as e:
            logger.warning(f"Weibo failed: {e}")
            return []

    async def _search_baidu_news(self, query: str) -> List[Dict]:
        """Search Baidu News (Chinese news aggregator)"""
        try:
            client = await self._get_client()
            url = f'https://www.baidu.com/s?wd={self._quote(query)}&tn=news&rtt=4&bsst=1&cl=2&wd=&medium=0'
            resp = await client.get(url, timeout=10)
            # Extract title + link from Baidu news results
            titles = re.findall(r'class="news-title[^"]*"[^>]*>([^<]+)', resp.text)
            links = re.findall(r'class="news-title[^"]*"[^>]*href="([^"]+)"', resp.text)
            urls_raw = re.findall(r'href="(https?://www\.baidu\.com/link\?url=[^"]+)"', resp.text)

            results = []
            seen_urls = set()
            for i, title in enumerate(titles[:8]):
                title = title.strip()
                if not title or title in seen_urls:
                    continue
                seen_urls.add(title)
                url_val = urls_raw[i] if i < len(urls_raw) else ''
                results.append({
                    'source': '百度新闻',
                    'title': title,
                    'url': url_val,
                    'snippet': title,
                    'content': title,
                    'credibility': 'medium',
                })
            return results
        except Exception as e:
            logger.warning(f"Baidu failed: {e}")
            return []

    @staticmethod
    def _quote(s: str) -> str:
        import urllib.parse
        return urllib.parse.quote(s)
