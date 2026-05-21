import os
import asyncio
import json
from playwright.async_api import async_playwright
from config import BROWSER_SETTINGS, USER_AGENTS
from core.utils import setup_logger
import random

logger = setup_logger("core.browser")

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        
    async def start(self):
        """Initialize Playwright and launch the Chromium browser."""
        if not self.browser:
            logger.info("Initializing Playwright and launching browser...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=BROWSER_SETTINGS.get("headless", True),
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--disable-web-security"
                ]
            )
            
    async def stop(self):
        """Shut down the browser and close Playwright."""
        if self.browser:
            logger.info("Closing browser...")
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            
    async def get_page_content(self, url, user_agent=None, is_mobile=False, timeout_ms=None):
        """Fetch the fully rendered HTML page using Playwright."""
        await self.start()
        
        ua = user_agent or random.choice(USER_AGENTS)
        viewport = BROWSER_SETTINGS["viewport_mobile"] if is_mobile else BROWSER_SETTINGS["viewport_desktop"]
        timeout = timeout_ms or BROWSER_SETTINGS["default_timeout_ms"]
        
        context = None
        page = None
        html = ""
        network_data = []
        
        async def handle_response(response):
            try:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    url_lower = response.url.lower()
                    
                    is_json_api = 'application/json' in content_type or 'graphql' in url_lower
                    has_keywords = any(kw in url_lower for kw in ['api', 'location', 'store', 'cafe', 'branch', 'contact', 'office', 'dealer'])
                    
                    if is_json_api or has_keywords:
                        body = await response.text()
                        if body:
                            network_data.append({
                                'url': response.url,
                                'method': response.request.method,
                                'content_type': content_type,
                                'body': body
                            })
            except Exception as e:
                pass
        
        try:
            context = await self.browser.new_context(
                user_agent=ua,
                viewport=viewport,
                ignore_https_errors=True,
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1"
                }
            )
            page = await context.new_page()
            page.set_default_timeout(timeout)
            
            # Attach response interceptor
            page.on("response", handle_response)
            
            # Go to page
            logger.info(f"Playwright navigating to: {url}")
            try:
                await page.goto(url, wait_until="commit", timeout=timeout)
                # Give dynamic javascript some time to render
                await page.wait_for_timeout(3000)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout reached while loading {url}. Halting loading and attempting to extract DOM...")
                # Stop loading and proceed with what's loaded
                await page.evaluate("window.stop()")
                
            html = await page.content()
            
            # Extract Local and Session Storage
            storage_data = {}
            try:
                storage_data['localStorage'] = await page.evaluate("() => JSON.stringify(window.localStorage)")
                storage_data['sessionStorage'] = await page.evaluate("() => JSON.stringify(window.sessionStorage)")
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Playwright failed to fetch content for {url}: {e}")
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
                
        return {
            "html": html,
            "network_data": network_data,
            "storage_data": storage_data
        }

    async def capture_screenshot(self, url, output_path, is_mobile=False):
        """Capture a full-page screenshot of a URL."""
        await self.start()
        
        ua = random.choice(USER_AGENTS)
        viewport = BROWSER_SETTINGS["viewport_mobile"] if is_mobile else BROWSER_SETTINGS["viewport_desktop"]
        timeout = BROWSER_SETTINGS["default_timeout_ms"]
        
        context = None
        page = None
        success = False
        
        try:
            logger.info(f"Capturing screenshot for: {url}")
            context = await self.browser.new_context(
                user_agent=ua,
                viewport=viewport,
                ignore_https_errors=True
            )
            page = await context.new_page()
            page.set_default_timeout(timeout)
            
            # Use longer timeouts for screenshots to ensure CSS is loaded
            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout)
            except Exception:
                # If networkidle fails, stop window loading to proceed
                await page.evaluate("window.stop()")
                await page.wait_for_timeout(2000)
                
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            await page.screenshot(path=output_path, full_page=True)
            logger.info(f"Saved screenshot to {output_path}")
            success = True
        except Exception as e:
            logger.error(f"Failed to capture screenshot for {url}: {e}")
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
                
        return success
