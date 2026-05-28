import os
import sys
import asyncio
import re
import json
import urllib.parse
import aiohttp
# Import modular services
from config import CRAWLER_SETTINGS, OUTPUT_JSON_DIR, OUTPUT_REPORTS_DIR, OUTPUT_SCREENSHOTS_DIR, OUTPUT_AUDITS_DIR, OUTPUT_EVIDENCE_DIR
from core.utils import setup_logger, extract_domain
from core.browser import BrowserManager
from core.crawler import AsyncCrawler
from core.parser import HTMLParser
from core.cleaner import clean_emails, clean_phones, clean_addresses

from intelligence.seo import SEOAnalyzer
from intelligence.techstack import TechStackDetector
from intelligence.performance import PerformanceAnalyzer
from intelligence.cro import CROAnalyzer
from intelligence.hiring import HiringAnalyzer
from intelligence.social import SocialAnalyzer
from intelligence.reviews import ReviewsAnalyzer
from intelligence.scoring import BusinessScoringEngine

from ai.summarizer import AISummarizer
from ai.insights import InsightsGenerator
from ai.outreach import OutreachGenerator
from ai.report_generator import ReportGenerator

logger = setup_logger("main")

def build_domain_candidates(business_name):
    """Build likely official website candidates when search providers fail."""
    slug = re.sub(r'[^a-z0-9]', '', business_name.lower())
    if not slug or business_name.startswith(("http://", "https://")):
        return []

    candidates = []
    for tld in ["com", "io", "co", "net", "org", "in"]:
        candidates.extend([
            f"https://{slug}.{tld}",
            f"https://www.{slug}.{tld}",
        ])
    return candidates

def should_try_direct_domain_first(business_name):
    """Use direct-domain probing first for short brand names like Nike or Stripe."""
    if business_name.startswith(("http://", "https://")):
        return False
    words = re.findall(r'\b[a-z0-9]+\b', business_name.lower())
    slug = re.sub(r'[^a-z0-9]', '', business_name.lower())
    return 1 <= len(words) <= 2 and 3 <= len(slug) <= 18

async def probe_official_domain_candidates(business_name):
    """Try likely official domains as a fallback to search result APIs."""
    candidates = build_domain_candidates(business_name)
    if not candidates:
        return None

    words = [w for w in re.findall(r'\b[a-z0-9]{3,}\b', business_name.lower())]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    timeout = aiohttp.ClientTimeout(total=8)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        for candidate in candidates:
            try:
                async with session.get(candidate, allow_redirects=True) as response:
                    candidate_domain = extract_domain(candidate).lower()
                    if response.status in [401, 403] and candidate_domain.endswith(".com"):
                        logger.info(f"Resolved target URL by exact protected domain match: {candidate}")
                        return candidate
                    if response.status >= 400:
                        continue
                    final_url = str(response.url)
                    html = await response.text(errors="ignore")
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
                    title = re.sub(r"\s+", " ", title_match.group(1)).strip().lower() if title_match else ""
                    final_domain = extract_domain(final_url).lower()
                    if any(word in title or word in final_domain for word in words) or extract_domain(candidate) == final_domain:
                        logger.info(f"Resolved target URL by probing likely official domain: {final_url}")
                        return final_url
            except Exception as exc:
                logger.debug(f"Candidate domain probe failed for {candidate}: {exc}")
    return None

async def search_business_url(business_name):
    """Search for the business website using DuckDuckGo search."""
    logger.info(f"Searching DuckDuckGo for: '{business_name}'")

    if should_try_direct_domain_first(business_name):
        direct_url = await probe_official_domain_candidates(business_name)
        if direct_url:
            return direct_url

    results = []
    
    # Try importing ddgs first
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(business_name, max_results=10))
    except Exception as e:
        logger.debug(f"ddgs package failed or not installed: {e}. Trying fallback...")
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(business_name, max_results=10))
        except Exception as ex:
            logger.error(f"Both DDGS search packages failed: {ex}")
            
    if not results:
        logger.warning(f"No search results returned for {business_name}")
        return await probe_official_domain_candidates(business_name)
        
    # Find the best candidate link
    for r in results:
        url = r.get("href", "")
        title = r.get("title", "")
        domain = extract_domain(url)
        
        # Filter directories and social platforms
        if domain and not any(x in domain for x in ["facebook.com", "instagram.com", "linkedin.com", "twitter.com", "yelp.com", "clutch.co", "wikipedia.org", "grokipedia.com", "g2.com"]):
            # Simple heuristic match
            score = 0
            words = re.findall(r'\b\w+\b', business_name.lower())
            for w in words:
                if w in title.lower() or w in domain.lower():
                    score += 10
                    
            if score > 0 or len(words) == 1:
                logger.info(f"Resolved target URL: {url} (Title: '{title}')")
                return url
                
    # Fallback to first result's URL
    fallback_url = results[0].get("href")
    logger.info(f"Fallback to first result URL: {fallback_url}")
    return fallback_url


async def audit_business(business_name, browser_manager):
    """Run the complete lead intelligence audit for a single business."""
    logger.info(f"=== Starting Lead Intelligence Audit for: {business_name} ===")
    
    # 1. Resolve URL
    url = await search_business_url(business_name)
    if not url:
        # Check if argument is already a URL
        if business_name.startswith(("http://", "https://")):
            url = business_name
        else:
            raise ValueError(f"Could not resolve a valid website URL for business: {business_name}")
            
    sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', business_name.lower()).strip('_')
    
    # 2. Capture Screenshot
    desktop_screenshot_path = os.path.join(OUTPUT_SCREENSHOTS_DIR, f"{sanitized_name}_desktop.png")
    await browser_manager.capture_screenshot(url, desktop_screenshot_path, is_mobile=False)
    
    # 3. Crawl Website Pages
    crawler = AsyncCrawler(browser_manager)
    crawled_pages = await crawler.crawl_domain(url)
    
    if not crawled_pages:
        raise ValueError(f"Failed to crawl any content from {url}")
        
    # Get homepage HTML. The crawler stores page metadata dictionaries, while
    # analyzers consume raw HTML strings.
    homepage_page = crawled_pages.get(url) or list(crawled_pages.values())[0]
    homepage_html = homepage_page.get("html", "") if isinstance(homepage_page, dict) else str(homepage_page)
    
    # 4. Parse pages
    parsed_pages_data = {}
    emails_raw = []
    phones_raw = []
    addresses_raw = []
    socials_raw = {}
    schemas_raw = []
    business_hours_raw = []
    geo_raw = []
    ctas_raw = []
    
    for page_url, page_data in crawled_pages.items():
        if not isinstance(page_data, dict):
            page_data = {"html": str(page_data), "network_data": [], "storage_data": {}}
        data = HTMLParser.parse_page(page_data, page_url)
        parsed_pages_data[page_url] = data
        
        emails_raw.extend(data.get("emails", []))
        phones_raw.extend(data.get("phone_numbers", []))
        addresses_raw.extend(data.get("addresses", []))
        socials_raw.update(data.get("social_links", {}))
        business_hours_raw.extend(data.get("business_hours", []))
        geo_raw.extend(data.get("geo_coordinates", []))
        ctas_raw.extend(data.get("ctas", []))
        schema_data = data.get("schema_ld", {})
        if isinstance(schema_data, dict):
            for schema_items in schema_data.values():
                if isinstance(schema_items, list):
                    schemas_raw.extend(schema_items)
        elif isinstance(schema_data, list):
            schemas_raw.extend(schema_data)
        
    # Clean parsed contacts
    emails = clean_emails(emails_raw)
    phones = clean_phones(phones_raw)
    addresses = clean_addresses(addresses_raw)
    business_hours = sorted(set(x for x in business_hours_raw if x))
    geo_coordinates = sorted(set(x for x in geo_raw if x))
    ctas = ctas_raw[:25]

    evidence_pages = []
    for page_url, data in parsed_pages_data.items():
        evidence_pages.append({
            "url": page_url,
            "title": data.get("title", ""),
            "meta_description": data.get("meta_description", ""),
            "headings": data.get("headings", {}),
            "emails": clean_emails(data.get("emails", [])),
            "phone_numbers": clean_phones(data.get("phone_numbers", [])),
            "addresses": clean_addresses(data.get("addresses", [])),
            "business_hours": data.get("business_hours", []),
            "social_links": data.get("social_links", {}),
            "geo_coordinates": data.get("geo_coordinates", []),
            "ctas": data.get("ctas", []),
            "forms": data.get("forms", []),
            "has_testimonials": data.get("has_testimonials", False),
            "page_summary": data.get("page_summary", {}),
            "hidden_json_data": data.get("hidden_json_data", {}),
        })
    
    # 5. Run Intelligence Analysis
    logger.info("Executing intelligence checks...")
    seo_results = SEOAnalyzer.analyze(homepage_html, parsed_pages_data)
    tech_stack = TechStackDetector.detect(homepage_html, url)
    performance = await PerformanceAnalyzer.analyze(url, browser_manager)
    cro_results = CROAnalyzer.analyze(homepage_html, parsed_pages_data, crawled_pages)
    hiring_results = HiringAnalyzer.analyze(parsed_pages_data)
    social_results = SocialAnalyzer.analyze(socials_raw, business_name)
    reviews_results = ReviewsAnalyzer.analyze(parsed_pages_data, schemas_raw)
    
    # Calculate overall opportunity scoring
    scores = BusinessScoringEngine.calculate_scores(
        seo_results, performance, cro_results, reviews_results, social_results, hiring_results
    )
    
    # Assemble comprehensive business profile
    business_profile = {
        "business_name": business_name,
        "website_url": url,
        "description": seo_results.get("meta_description") or parsed_pages_data[list(parsed_pages_data.keys())[0]].get("title", ""),
        "emails": emails,
        "phone_numbers": phones,
        "addresses": addresses,
        "business_hours": business_hours,
        "geo_coordinates": geo_coordinates,
        "conversion_actions": ctas,
        "social_links": socials_raw,
        "tech_stack": tech_stack,
        "seo": seo_results,
        "performance": performance,
        "cro": cro_results,
        "hiring": hiring_results,
        "social": social_results,
        "reviews": reviews_results,
        "scores": scores
    }

    evidence_bundle = {
        "business_name": business_name,
        "website_url": url,
        "crawler_settings": CRAWLER_SETTINGS,
        "pages": evidence_pages,
        "final_extracted_data": {
            "emails": emails,
            "phone_numbers": phones,
            "addresses": addresses,
            "business_hours": business_hours,
            "geo_coordinates": geo_coordinates,
            "conversion_actions": ctas,
            "social_links": socials_raw,
            "tech_stack": tech_stack,
        },
        "analysis_basis": {
            "seo": seo_results,
            "performance": performance,
            "cro": cro_results,
            "hiring": hiring_results,
            "social": social_results,
            "reviews": reviews_results,
            "scores": scores,
        },
    }
    business_profile["evidence_file"] = os.path.join(OUTPUT_EVIDENCE_DIR, f"{sanitized_name}_evidence.md")
    business_profile["evidence_json_file"] = os.path.join(OUTPUT_EVIDENCE_DIR, f"{sanitized_name}_evidence.json")
    
    # 6. Generate AI Copies
    logger.info("Generating copywriting templates...")
    summary = AISummarizer.get_summary(business_profile)
    business_profile["summary"] = summary
    
    swot = InsightsGenerator.generate_swot_and_gaps(business_profile)
    business_profile["swot"] = swot
    
    outreach_messages = OutreachGenerator.generate_messages(business_profile)
    business_profile["outreach"] = outreach_messages
    business_profile["outreach_email"] = outreach_messages["email"]
    
    # 7. Write outputs to disk
    # Save structured JSON
    json_path = os.path.join(OUTPUT_JSON_DIR, f"{sanitized_name}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(business_profile, f, indent=2)
    logger.info(f"Saved audit JSON database to {json_path}")

    # Save manager-readable evidence and raw evidence JSON
    evidence_json_path = os.path.join(OUTPUT_EVIDENCE_DIR, f"{sanitized_name}_evidence.json")
    with open(evidence_json_path, 'w', encoding='utf-8') as f:
        json.dump(evidence_bundle, f, indent=2)
    logger.info(f"Saved raw evidence JSON to {evidence_json_path}")

    evidence_report = ReportGenerator.generate_evidence_markdown(business_profile, evidence_bundle)
    evidence_md_path = os.path.join(OUTPUT_EVIDENCE_DIR, f"{sanitized_name}_evidence.md")
    with open(evidence_md_path, 'w', encoding='utf-8') as f:
        f.write(evidence_report)
    logger.info(f"Saved manager evidence report to {evidence_md_path}")
    
    # Save Markdown report
    md_report = ReportGenerator.generate_markdown(business_profile)
    md_path = os.path.join(OUTPUT_AUDITS_DIR, f"{sanitized_name}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_report)
    logger.info(f"Saved executive Markdown audit to {md_path}")
    
    # Save HTML report
    html_path = os.path.join(OUTPUT_REPORTS_DIR, f"{sanitized_name}.html")
    ReportGenerator.generate_html(business_profile, html_path, desktop_screenshot_path)
    
    logger.info(f"=== Successfully completed audit for: {business_name} ===\n")
    return business_profile

async def main_async():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} \"Business Name\" OR python {sys.argv[0]} companies.txt")
        sys.exit(1)
        
    input_arg = sys.argv[1]
    
    # Parse inputs (batch file or single business)
    if os.path.exists(input_arg):
        logger.info(f"Reading target business list from file: {input_arg}")
        try:
            with open(input_arg, 'r', encoding='utf-8') as f:
                businesses = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Failed to read batch input file: {e}")
            sys.exit(1)
    else:
        businesses = [input_arg]
        
    # Launch browser manager context
    bm = BrowserManager()
    await bm.start()
    
    results = []
    
    try:
        for biz in businesses:
            try:
                profile = await audit_business(biz, bm)
                results.append(profile)
            except Exception as e:
                logger.error(f"Failed to audit target business '{biz}': {e}")
    finally:
        await bm.stop()
        
    logger.info("All lead intelligence operations successfully concluded.")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
