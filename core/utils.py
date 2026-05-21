import logging
import os
import urllib.parse
from urllib.robotparser import RobotFileParser
import aiohttp
import asyncio

# Setup global logger
def setup_logger(name="lead_intelligence"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s', '%Y-%m-%d %H:%M:%S')
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

logger = setup_logger("core.utils")

def extract_domain(url):
    """Extract clean domain name from a URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc or parsed.path
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # Remove port if present
        return netloc.split(":")[0]
    except Exception:
        return ""

def get_base_url(url):
    """Get base protocol + domain from URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    return url

async def check_robots_txt(url, user_agent="*"):
    """Check if robots.txt allows crawling the given URL."""
    base_url = get_base_url(url)
    robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
    
    parser = RobotFileParser()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(robots_url, timeout=5) as response:
                if response.status == 200:
                    content = await response.text()
                    parser.parse(content.splitlines())
                    allowed = parser.can_fetch(user_agent, url)
                    return allowed
    except Exception as e:
        # Default to True on connection failures or missing robots.txt
        logger.debug(f"Failed to fetch robots.txt from {robots_url}: {e}")
    return True
