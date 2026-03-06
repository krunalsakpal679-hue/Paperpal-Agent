# backend/app/agents/interpretation/scraper.py
"""
JournalScraper: Scrapes journal websites using Playwright and BeautifulSoup.
Extracts author guidelines and formatting instructions.
"""

import logging
import asyncio
from typing import Tuple
from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger(__name__)

class JournalScraper:
    """
    Scrapes journal guidelines pages and extracts relevant content.
    Uses Playwright for dynamic pages and falls back to HTTPX for static ones.
    """

    MAX_CHARS = 8000

    async def scrape(self, url: str) -> Tuple[str, bool]:
        """
        Scrape the given URL.
        Returns (cleaned_text, login_wall_detected).
        """
        logger.info("Scraping journal guidelines from %s", url)
        
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                page = await context.new_page()
                
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    content = await page.content()
                    await browser.close()
                    return self._process_html(content)
                except Exception as e:
                    logger.warning("Playwright failed for %s: %s. Falling back to HTTPX.", url, e)
                    await browser.close()
                    return await self._fallback_scrape(url)
        except ImportError:
            logger.warning("Playwright not installed. Falling back to HTTPX.")
            return await self._fallback_scrape(url)
        except Exception as e:
            logger.error("Unexpected error in scraper: %s", e)
            return "", False

    async def _fallback_scrape(self, url: str) -> Tuple[str, bool]:
        """Fallback to simple HTTP request if Playwright fails or is unavailable."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            try:
                # Nature or other sites might block simple User-Agent
                headers = {"User-Agent": "Mozilla/5.0"}
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return self._process_html(response.text)
            except Exception as e:
                logger.error("Fallback scrape failed for %s: %s", url, e)
                return "", False

    def _process_html(self, html: str) -> Tuple[str, bool]:
        """Clean HTML and extract main instruction content."""
        soup = BeautifulSoup(html, 'lxml')
        
        # 1. Detect login wall
        login_indicators = ["login required", "sign in to", "subscribe", "create account", "access restricted"]
        page_text_lower = soup.get_text().lower()
        login_wall = any(ind in page_text_lower for ind in login_indicators)
        
        # 2. Remove noise
        for tag in soup(["nav", "header", "footer", "aside", "script", "style", "iframe"]):
            tag.decompose()
            
        # 3. Target specific selectors
        content_selectors = [
            'main', 'article', '.content', '#author-instructions', 
            '.submission-guidelines', '.author-guidelines', '#instructions'
        ]
        
        main_content = None
        for selector in content_selectors:
            found = soup.select_one(selector)
            if found:
                main_content = found
                break
        
        if not main_content:
            main_content = soup.find('body') or soup

        # 4. Extract text and truncate
        text = main_content.get_text(separator='\n', strip=True)
        if len(text) > self.MAX_CHARS:
            text = text[:self.MAX_CHARS] + "... [truncated]"
            
        return text, login_wall
