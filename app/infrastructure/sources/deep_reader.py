"""
Deep content reader — extracts full article text from URLs.

Tries multiple strategies in order:
1. Crawl4AI (headless browser, best quality)
2. newspaper3k (fast, no browser needed)
3. GNews full article helper
4. Basic requests + BeautifulSoup fallback

Single responsibility: URL → full article text.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from app.domain.ports import DeepReader

MAX_CONTENT_LENGTH = 3000


class MultiStrategyReader(DeepReader):
    """Extracts article content using multiple fallback strategies."""

    def extract(self, url: str) -> Optional[str]:
        """Try all strategies in order. Return the best content or None."""

        strategies = [
            ("Crawl4AI", self._try_crawl4ai),
            ("newspaper3k", self._try_newspaper),
            ("gnews", self._try_gnews_article),
            ("requests+bs4", self._try_requests),
        ]

        for name, strategy in strategies:
            try:
                content = strategy(url)
                if content and len(content.strip()) > 100:
                    return content.strip()[:MAX_CONTENT_LENGTH]
            except Exception as e:
                print(f"  ⚠️ {name} error: {e}")

        return None

    # ── Strategy implementations ─────────────────────────────

    @staticmethod
    def _try_crawl4ai(url: str) -> Optional[str]:
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        except ImportError:
            return None

        async def _crawl() -> Optional[str]:
            config = CrawlerRunConfig()
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url, config=config)
                if result.success and result.markdown:
                    return result.markdown
            return None

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(lambda: asyncio.run(_crawl())).result(timeout=30)
            return asyncio.run(_crawl())
        except Exception:
            return None

    @staticmethod
    def _try_newspaper(url: str) -> Optional[str]:
        try:
            from newspaper import Article
        except ImportError:
            return None

        article = Article(url, language="es")
        article.download()
        article.parse()
        return article.text if article.text else None

    @staticmethod
    def _try_gnews_article(url: str) -> Optional[str]:
        try:
            from gnews import GNews
            g = GNews()
            article = g.get_full_article(url)
            if article and article.text:
                return article.text
        except Exception:
            pass
        return None

    @staticmethod
    def _try_requests(url: str) -> Optional[str]:
        import requests
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return None

        response = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; CostcoMonitor/1.0)"
        })
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Try article or main content
        article = soup.find("article") or soup.find("main") or soup.find("body")
        if article:
            paragraphs = article.find_all("p")
            text = "\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
            if len(text) > 100:
                return text

        return None
