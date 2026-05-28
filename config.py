import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Output directories
OUTPUT_JSON_DIR = os.path.join(BASE_DIR, "outputs", "json")
OUTPUT_REPORTS_DIR = os.path.join(BASE_DIR, "outputs", "reports")
OUTPUT_SCREENSHOTS_DIR = os.path.join(BASE_DIR, "outputs", "screenshots")
OUTPUT_AUDITS_DIR = os.path.join(BASE_DIR, "outputs", "audits")
OUTPUT_EVIDENCE_DIR = os.path.join(BASE_DIR, "outputs", "evidence")

# Ensure all output directories exist
for directory in [OUTPUT_JSON_DIR, OUTPUT_REPORTS_DIR, OUTPUT_SCREENSHOTS_DIR, OUTPUT_AUDITS_DIR, OUTPUT_EVIDENCE_DIR]:
    os.makedirs(directory, exist_ok=True)

# Crawler Settings
CRAWLER_SETTINGS = {
    "max_depth": 2,
    "max_pages_per_domain": 10,
    "concurrency_limit": 3,
    "timeout_ms": 15000,
    "rate_limit_seconds": 1.0,
    "max_retries": 3,
    "backoff_factor": 2.0,
    "respect_robots_txt": True
}

# Browser Settings
BROWSER_SETTINGS = {
    "headless": True,
    "viewport_desktop": {"width": 1280, "height": 800},
    "viewport_mobile": {"width": 375, "height": 667},
    "default_timeout_ms": 20000,
    "stealth_mode": True
}

# Scoring Engine Weights (must sum to 1.0)
SCORING_WEIGHTS = {
    "seo": 0.25,
    "performance": 0.15,
    "conversion": 0.25,
    "trust": 0.15,
    "social": 0.10,
    "growth": 0.10
}

# User-Agent List for Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
]

# AI / LLM Configuration
# Supports OpenAI-compatible endpoints or Gemini API keys.
AI_CONFIG = {
    "api_provider": os.environ.get("AI_PROVIDER", "local"),  # 'local', 'openai', or 'gemini'
    "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
    "openai_base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "openai_model": os.environ.get("OPENAI_MODEL", "gpt-4-turbo"),
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "gemini_model": os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
}
