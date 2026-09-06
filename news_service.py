"""
Naver News Collection Service
Handles news fetching from Naver Search API and URL shortening
"""

import os
import time
import requests
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NAVER_API_BASE = "https://naverapihub.apigw.ntruss.com/search/v1/news"
TINYURL_API_BASE = "https://tinyurl.com/api-create.php"


def _get_config(key: str, default: str = "") -> str:
    """Read a config value from the environment (.env, local dev) first,
    falling back to Streamlit's secrets store (st.secrets) when running on
    Streamlit Community Cloud, where no .env file is deployed."""
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


class NaverNewsService:
    """Service for collecting news from Naver Search API"""

    def __init__(self):
        self.client_id = _get_config("NAVER_CLIENT_ID")
        self.client_secret = _get_config("NAVER_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "NAVER_CLIENT_ID and NAVER_CLIENT_SECRET must be set in .env "
                "(local) or Streamlit secrets (cloud)"
            )

    def _get_headers(self) -> Dict[str, str]:
        """Return headers for Naver API request"""
        return {
            "X-NCP-APIGW-API-KEY-ID": self.client_id,
            "X-NCP-APIGW-API-KEY": self.client_secret
        }

    def search_news(
        self,
        query: str,
        sort: str = "date",
        display: int = 10,
        start: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search news articles from Naver News API

        Args:
            query: Search keyword
            sort: Sort method ('date' or 'sim' for similarity)
            display: Number of results (1-100, default: 10)
            start: Starting position (1-1000, default: 1)

        Returns:
            List of news articles with title, link, source, and publication date
        """
        params = {
            "query": query,
            "sort": sort,
            "display": min(display, 100),
            "start": start,
            "format": "json"
        }

        try:
            response = requests.get(
                NAVER_API_BASE,
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            articles = []

            for item in data.get("items", []):
                original_url = item.get("originallink") or item.get("link", "")
                article = {
                    "title": self._clean_html(item.get("title", "")),
                    "original_url": original_url,
                    "source": self._extract_source(original_url),
                    "published_date": self._parse_date(item.get("pubDate", "")),
                    "description": self._clean_html(item.get("description", ""))
                }
                articles.append(article)

            return articles

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch news from Naver API: {str(e)}")

    @staticmethod
    def _clean_html(text: str) -> str:
        """Remove HTML tags from text"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)

    @staticmethod
    def _extract_source(url: str) -> str:
        """Derive press/source name from the article's domain (API provides no source field)"""
        from urllib.parse import urlparse
        if not url:
            return "Unknown"
        domain = urlparse(url).netloc
        return domain.replace("www.", "") if domain else "Unknown"

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse and format publication date"""
        try:
            if date_str:
                dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            pass
        return date_str


class URLShortener:
    """Service for shortening URLs using TinyURL's free create API (no
    account/API key required)."""

    def shorten_url_verbose(
        self, long_url: str, retries: int = 1, timeout: float = 6.0
    ) -> tuple[str, str | None]:
        """
        Shorten a URL using the TinyURL API and report *why* it failed, if it did.

        Returns the result as a local tuple (not shared instance state) so
        this stays safe under Streamlit's cache_resource, where a single
        URLShortener instance can be used concurrently across sessions.

        Args:
            long_url: Original URL to shorten
            retries: Extra attempts on timeout errors (transient network
                hiccups are common on cloud-hosted deployments).
            timeout: Per-request timeout in seconds.

        Returns:
            (url, error): `url` is the shortened link, or `long_url` if the
            service was unavailable. `error` is None on success, otherwise a
            human-readable reason for the fallback.
        """
        if not long_url:
            return "", None

        params = {"url": long_url}

        attempts = max(1, retries + 1)
        last_error = None
        for attempt in range(attempts):
            try:
                response = requests.get(TINYURL_API_BASE, params=params, timeout=timeout)

                if response.status_code == 200:
                    short_url = response.text.strip()
                    if short_url.startswith("http") and "tinyurl.com" in short_url:
                        return short_url, None
                    return long_url, f"TinyURL 응답 실패: {short_url[:200]}"

                return long_url, f"TinyURL HTTP {response.status_code}: {response.text[:200]}"

            except requests.exceptions.Timeout:
                last_error = f"TinyURL 요청 시간 초과({timeout}s, 시도 {attempt + 1}/{attempts})"
                if attempt < attempts - 1:
                    time.sleep(1.5)  # brief backoff before retrying
                continue  # worth a retry — transient
            except requests.exceptions.RequestException as e:
                return long_url, f"TinyURL 요청 오류: {type(e).__name__}: {e}"

        return long_url, last_error

    def shorten_url(self, long_url: str) -> str:
        """
        Shorten a URL using the TinyURL API

        Args:
            long_url: Original URL to shorten

        Returns:
            Shortened URL or original URL if service is unavailable
        """
        url, _ = self.shorten_url_verbose(long_url)
        return url

    def batch_shorten_urls(self, urls: List[str]) -> Dict[str, str]:
        """
        Shorten multiple URLs

        Args:
            urls: List of original URLs

        Returns:
            Dictionary mapping original URLs to shortened URLs
        """
        result = {}
        for url in urls:
            result[url] = self.shorten_url(url)
        return result


def get_news_with_short_urls(query: str, num_articles: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch news articles and shorten their URLs

    Args:
        query: Search keyword
        num_articles: Number of articles to fetch

    Returns:
        List of articles with shortened URLs
    """
    news_service = NaverNewsService()
    shortener = URLShortener()

    articles = news_service.search_news(query=query, display=num_articles)

    for article in articles:
        article["short_url"] = shortener.shorten_url(article["original_url"])

    return articles


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    # Example usage
    try:
        articles = get_news_with_short_urls("파이썬", num_articles=5)
        for idx, article in enumerate(articles, 1):
            print(f"\n[{idx}] {article['title']}")
            print(f"    Source: {article['source']}")
            print(f"    Date: {article['published_date']}")
            print(f"    URL: {article['original_url']}")
            print(f"    Short URL: {article['short_url']}")
    except Exception as e:
        print(f"Error: {e}")
