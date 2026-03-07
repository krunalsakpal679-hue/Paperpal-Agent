# backend/app/agents/interpretation/scraper.py
"""
JournalScraper: Scrapes journal websites using Playwright and BeautifulSoup.
Extracts author guidelines and formatting instructions.
"""

import logging
import hashlib
import asyncio
from typing import Optional, Tuple
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
            # TRY FASTEST FIRST: HTTPX
            text, login_wall = await self._fallback_scrape(url)
            if text and not login_wall:
                return text, login_wall
                
            # FALLBACK TO Playwright only if needed
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                page = await context.new_page()
                
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    content = await page.content()
                    await browser.close()
                    return self._process_html(content)
                except Exception as e:
                    logger.warning("Playwright also failed for %s: %s", url, e)
                    await browser.close()
                    return text, login_wall
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
                # Use a more realistic browser User-Agent to avoid immediate blocks
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return self._process_html(response.text)
            except Exception as e:
                logger.error("Fallback scrape failed for %s: %s", url, e)
                return "", False

    def _process_html(self, html: str) -> Tuple[str, bool]:
        """Clean HTML and extract main instruction content."""
        try:
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
            if not main_content:
                return "", login_wall
                
            text = main_content.get_text(separator='\n', strip=True)
            if len(text) > self.MAX_CHARS:
                text = text[:self.MAX_CHARS] + "... [truncated]"
                
            return text, login_wall
        except Exception as e:
            logger.error("Error processing HTML: %s", e)
            return "", False
