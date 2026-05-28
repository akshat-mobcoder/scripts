import asyncio
import urllib.parse
from bs4 import BeautifulSoup
import aiohttp
import xmltodict
from config import CRAWLER_SETTINGS, USER_AGENTS
from core.utils import setup_logger, extract_domain, check_robots_txt, get_base_url
import random
from collections import deque
import json
import re

logger = setup_logger("core.crawler")

class AsyncCrawler:
    def __init__(self, browser_manager=None):
        self.browser_manager = browser_manager
        self.max_depth = CRAWLER_SETTINGS["max_depth"]
        self.max_pages = CRAWLER_SETTINGS["max_pages_per_domain"]
        self.concurrency = CRAWLER_SETTINGS["concurrency_limit"]
        self.respect_robots = CRAWLER_SETTINGS["respect_robots_txt"]
        
    async def _fetch_static(self, session, url, user_agent):
        """Fetch static page content using aiohttp."""
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        try:
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                if response.status == 200:
                    html = await response.text()
                    # Check if it looks like a JavaScript-heavy blank app
                    soup = BeautifulSoup(html, 'html.parser')
                    body_text = soup.body.get_text().strip() if soup.body else ""
                    js_keywords = ['noscript', 'enable javascript', 'loading...', 'you need to enable javascript']
                    if len(body_text) < 300 and any(kw in html.lower() for kw in js_keywords):
                        logger.info(f"Page appears to be SPA: {url}. Falling back to browser...")
                        return None, True # Fall back
                    return html, False
                elif response.status in [403, 401]:
                    logger.info(f"Static fetch returned {response.status} for {url}. Falling back to browser...")
                    return None, True # Fall back to browser
        except Exception as e:
            logger.debug(f"Static fetch failed for {url}: {e}")
        return None, True # Fall back to browser on failure

    async def _probe_apis(self, session, base_url):
        """Phase 3: API Endpoint Discovery"""
        endpoints = [
            '/api/locations', '/locations.json', '/stores.json', 
            '/api/stores', '/store-locator', '/locations', 
            '/graphql', '/wp-json', '/api/contact', '/api/v1/locations'
        ]
        api_payloads = []
        for ep in endpoints:
            url = urllib.parse.urljoin(base_url, ep)
            try:
                # We do a quick GET
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            data = await response.json()
                            if data:
                                api_payloads.append({
                                    "url": url,
                                    "method": "GET",
                                    "content_type": content_type,
                                    "body": json.dumps(data)
                                })
                                logger.info(f"Discovered valid JSON API endpoint: {url}")
            except Exception:
                pass
        return api_payloads

    async def _discover_sitemap_urls(self, session, base_url):
        """Phase 6: Sitemap Discovery"""
        sitemap_url = urllib.parse.urljoin(base_url, '/sitemap.xml')
        discovered_urls = []
        try:
            async with session.get(sitemap_url, timeout=5) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    try:
                        parsed = xmltodict.parse(xml_data)
                        urls = []
                        # Handle sitemap index
                        if 'sitemapindex' in parsed and 'sitemap' in parsed['sitemapindex']:
                            sitemaps = parsed['sitemapindex']['sitemap']
                            if not isinstance(sitemaps, list):
                                sitemaps = [sitemaps]
                            for sm in sitemaps:
                                loc = sm.get('loc')
                                if loc and any(kw in loc.lower() for kw in ['location', 'store', 'page', 'contact']):
                                    # Fetch sub-sitemap
                                    async with session.get(loc, timeout=5) as sub_res:
                                        if sub_res.status == 200:
                                            sub_xml = await sub_res.text()
                                            sub_parsed = xmltodict.parse(sub_xml)
                                            if 'urlset' in sub_parsed and 'url' in sub_parsed['urlset']:
                                                s_urls = sub_parsed['urlset']['url']
                                                if not isinstance(s_urls, list):
                                                    s_urls = [s_urls]
                                                urls.extend([u.get('loc') for u in s_urls if u.get('loc')])
                        # Handle urlset directly
                        elif 'urlset' in parsed and 'url' in parsed['urlset']:
                            s_urls = parsed['urlset']['url']
                            if not isinstance(s_urls, list):
                                s_urls = [s_urls]
                            urls.extend([u.get('loc') for u in s_urls if u.get('loc')])
                            
                        # Filter prioritized URLs
                        for u in urls:
                            if any(kw in u.lower() for kw in ['contact', 'locations', 'stores', 'cafes', 'branches', 'offices', 'dealers', 'showrooms', 'about']):
                                discovered_urls.append(u)
                        logger.info(f"Discovered {len(discovered_urls)} priority URLs from sitemap.")
                    except Exception as parse_e:
                        logger.debug(f"Failed to parse sitemap XML: {parse_e}")
        except Exception:
            pass
        return discovered_urls

    def _score_link(self, url):
        """Phase 7: Intelligent Link Prioritization"""
        score = 0
        url_lower = url.lower()
        
        # High priority keywords
        high_priority = ['contact', 'locations', 'stores', 'cafes', 'find-us', 'offices', 'support', 'about', 'visit']
        # Low priority keywords
        avoid = ['products', 'blogs', 'collections', 'careers', 'legal', 'policies', 'terms', 'privacy', 'tag', 'category']
        
        for kw in high_priority:
            if kw in url_lower:
                score += 10
        for kw in avoid:
            if kw in url_lower:
                score -= 10
                
        # Shorter URLs often better
        score -= len(url_lower) * 0.01
        
        return score

    async def crawl_domain(self, start_url):
        """Orchestrate crawl for a single domain."""
        domain = extract_domain(start_url)
        base_url = get_base_url(start_url)
        
        # Check robots.txt
        if self.respect_robots:
            allowed = await check_robots_txt(start_url)
            if not allowed:
                logger.warning(f"Robots.txt restricts crawling on {start_url}. Skipping crawl.")
                return {}
                
        visited = set()
        to_visit = [(start_url, 0)] # list of (url, depth)
        
        pages_data = {} # url -> dict(html, network_data, storage_data)
        
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async with aiohttp.ClientSession() as session:
            # Phase 3 & 6: Discovery
            sitemap_urls = await self._discover_sitemap_urls(session, base_url)
            api_payloads = await self._probe_apis(session, base_url)
            
            for s_url in sitemap_urls[:5]: # Limit to top 5 sitemap urls
                if s_url not in visited:
                    to_visit.append((s_url, 1))
                    
            while to_visit and len(visited) < self.max_pages:
                # Sort by priority score (Phase 7)
                to_visit.sort(key=lambda x: self._score_link(x[0]), reverse=True)
                
                # Group next batch
                batch = []
                while to_visit and len(batch) < self.concurrency:
                    curr_url, curr_depth = to_visit.pop(0) # Pop highest score
                    
                    # Normalize URL
                    parsed_curr = urllib.parse.urlparse(curr_url)
                    normalized_url = f"{parsed_curr.scheme}://{parsed_curr.netloc}{parsed_curr.path}"
                    if normalized_url.endswith("/"):
                        normalized_url = normalized_url[:-1]
                        
                    if normalized_url not in visited:
                        visited.add(normalized_url)
                        batch.append((curr_url, normalized_url, curr_depth))
                        
                if not batch:
                    break
                    
                async def worker(url, norm_url, depth):
                    async with semaphore:
                        ua = random.choice(USER_AGENTS)
                        logger.info(f"Crawling: {url} (Depth: {depth})")
                        
                        html, fallback = await self._fetch_static(session, url, ua)
                        page_data = {"html": "", "network_data": [], "storage_data": {}}
                        
                        if fallback and self.browser_manager:
                            page_data = await self.browser_manager.get_page_content(url, user_agent=ua)
                            html = page_data.get('html', '')
                        else:
                            page_data["html"] = html
                            
                        # Add discovered API payloads to homepage data
                        if depth == 0 and api_payloads:
                            page_data["network_data"].extend(api_payloads)
                            
                        if html:
                            pages_data[url] = page_data
                            
                            # Parse links for next depth
                            if depth < self.max_depth:
                                new_links = self._extract_links(html, base_url, domain)
                                for link in new_links:
                                    if link not in visited:
                                        # Deduplicate in queue
                                        if not any(x[0] == link for x in to_visit):
                                            to_visit.append((link, depth + 1))
                                        
                        # Rate limit delay
                        await asyncio.sleep(CRAWLER_SETTINGS["rate_limit_seconds"])

                tasks = [worker(url, norm_url, depth) for url, norm_url, depth in batch]
                await asyncio.gather(*tasks)
                
        return pages_data
        
    def _extract_links(self, html, base_url, domain):
        """Extract valid internal links from page HTML."""
        links = set()
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                # Skip mailto, tel, javascript, anchors
                if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                    continue
                    
                # Parse absolute URL
                absolute = urllib.parse.urljoin(base_url, href)
                parsed_abs = urllib.parse.urlparse(absolute)
                
                # Verify internal link
                abs_domain = extract_domain(absolute)
                if abs_domain == domain:
                    # Clean up URL (strip query parameters and fragments)
                    cleaned = f"{parsed_abs.scheme}://{parsed_abs.netloc}{parsed_abs.path}"
                    if cleaned.endswith("/"):
                        cleaned = cleaned[:-1]
                    # Exclude assets
                    if not any(cleaned.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.xml', '.css', '.js']):
                        links.add(cleaned)
        except Exception as e:
            logger.debug(f"Failed to parse links: {e}")
        return list(links)
