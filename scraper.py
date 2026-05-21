#!/usr/bin/env python3
"""
Business Information Scraper

This script accepts a business name from the command line, searches for it on
DuckDuckGo, navigates to the first organic business website, and extracts contact
and business information.

Dependencies:
    pip install requests beautifulsoup4 selenium webdriver-manager ddgs

Usage:
    python scraper.py "Business Name"
"""

import sys
import os
import json
import re
import time
import urllib.parse
from bs4 import BeautifulSoup
import requests

LOG_FILE = None
LOG_BUFFER = []

# Helper function to print logs to file (or stderr if log file not set)
def log(message):
    msg = f"[*] {message}\n"
    LOG_BUFFER.append(msg)
    if LOG_FILE:
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(msg)
        except Exception:
            pass
    else:
        sys.stderr.write(msg)
        sys.stderr.flush()

def log_error(message):
    msg = f"[ERROR] {message}\n"
    LOG_BUFFER.append(msg)
    if LOG_FILE:
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(msg)
        except Exception:
            pass
    else:
        sys.stderr.write(msg)
        sys.stderr.flush()

# Common reference, directory, and social media domains to skip in order to prioritize the actual business website
EXCLUDED_DOMAINS = {
    'wikipedia.org', 'en.wikipedia.org',
    'wikimedia.org', 'wiktionary.org',
    'grokipedia.com', 'britannica.com',
    'facebook.com', 'm.facebook.com',
    'twitter.com', 'x.com',
    'linkedin.com', 'instagram.com',
    'youtube.com', 'youtu.be',
    'pinterest.com', 'tiktok.com',
    'yelp.com', 'tripadvisor.com',
    'yellowpages.com', 'mapquest.com',
    'foursquare.com', 'crunchbase.com',
    'glassdoor.com', 'indeed.com',
    'groupon.com', 'grubhub.com',
    'ubereats.com', 'doordash.com',
    'seamless.com', 'menuism.com',
    'opentable.com', 'zomato.com',
    'local.yahoo.com', 'maps.google.com',
    'duckduckgo.com', 'github.com',
    'reddit.com', 'quora.com', 'medium.com'
}

def get_website_score(url, query):
    """
    Calculates a match score for the URL based on the business name query.
    Higher score means it's a better candidate for the official website.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # 1. Direct exclusions check
        for ext in EXCLUDED_DOMAINS:
            if domain == ext or domain.endswith('.' + ext):
                return -1000
                
        # 2. Score calculation
        score = 0
        clean_query = re.sub(r'[^a-zA-Z0-9]', '', query).lower()
        # Extract main domain name (e.g. 'stripe' from 'stripe.com' or 'stripe.co.uk')
        domain_parts = domain.split('.')
        clean_domain = domain_parts[0] if domain_parts else ""
        
        # Exact match (e.g. query "Stripe" matches domain "stripe.com")
        if clean_query == clean_domain:
            score += 100
        # Substring match (e.g. query "Joe's Pizza" matches domain "joespizzanyc.com")
        elif clean_query in clean_domain or clean_domain in clean_query:
            score += 50
        # Multi-word substring matching (e.g. parts of query match domain parts)
        else:
            query_words = [w for w in re.split(r'[^a-zA-Z0-9]', query.lower()) if len(w) > 2]
            match_count = sum(1 for w in query_words if w in clean_domain)
            score += match_count * 20
            
        return score
    except Exception:
        return -1000

def search_duckduckgo(query):
    """
    Searches DuckDuckGo for the business name.
    Tries the 'ddgs' package first, then falls back to 'duckduckgo_search' package.
    """
    log(f"Searching DuckDuckGo for: '{query}'")
    
    # Try importing ddgs first
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=10))
            if results:
                return results
    except Exception as e:
        log(f"DDGS module failed or not installed, trying duckduckgo_search fallback... ({e})")
        
    # Try importing duckduckgo_search
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=10))
            if results:
                return results
    except Exception as e:
        log_error(f"Both DDGS and duckduckgo_search packages failed or are unavailable: {e}")
        
    return []

def fetch_html(url):
    """
    Fetches the HTML of a URL.
    Attempts requests with a browser User-Agent first.
    Falls back to Headless Selenium if the page looks like a Javascript SPA or request fails.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    log(f"Fetching URL: {url}")
    
    # 1. Try lightweight Requests first
    try:
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check if page is mostly empty (SPA detection)
            body_text = soup.body.get_text() if soup.body else ""
            js_keywords = ['noscript', 'enable javascript', 'loading...', 'you need to enable javascript']
            is_spa = len(body_text.strip()) < 300 and any(kw in html.lower() for kw in js_keywords)
            
            if not is_spa:
                log("Successfully fetched page content via Requests.")
                return html
            else:
                log("Page content appears to be empty/JS-dependent. Falling back to Headless Selenium...")
        else:
            log(f"Requests returned status code {response.status_code}. Falling back to Headless Selenium...")
    except Exception as e:
        log(f"Requests failed ({e}). Falling back to Headless Selenium...")
        
    # 2. Selenium Headless Fallback
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.common.exceptions import TimeoutException
        from webdriver_manager.chrome import ChromeDriverManager
        
        log("Launching Headless Chrome...")
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(20)
        
        try:
            driver.get(url)
            # Give JS elements time to load
            time.sleep(4)
        except TimeoutException:
            log("Selenium page load timed out, stopping loading and extracting available page source...")
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
        
        html = driver.page_source
        driver.quit()
        log("Successfully fetched page content via Headless Selenium.")
        return html
    except Exception as se:
        log_error(f"Headless Selenium failed: {se}")
        return ""

def clean_emails(emails):
    """Filters out template boilerplates and false-positive asset links from emails."""
    valid = set()
    for email in emails:
        email = email.strip().lower()
        # Skip standard web templates placeholders
        if any(kw in email for kw in ['example.com', 'yourname', 'placeholder', 'domain.com', 'email@', 'yoursite']):
            continue
        # Exclude false positives ending with common assets extensions
        if any(email.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.webp', '.svg']):
            continue
        valid.add(email)
    return list(valid)

def clean_phones(phones):
    """Validates phone matches, filtering out dates and non-phone digit blocks."""
    valid = set()
    for phone in phones:
        phone = phone.strip()
        # Extract only digits to check length
        digits = re.sub(r'\D', '', phone)
        # Valid numbers are usually 7 to 15 digits
        if 7 <= len(digits) <= 15:
            # Exclude date formats like 2026-05-20 or 2026/05/20
            if re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}$', phone):
                continue
            # Exclude repeating fake patterns (e.g. 111-111-1111)
            if len(set(digits)) <= 2 and len(digits) > 8:
                continue
            valid.add(phone)
    return list(valid)

def extract_business_name(soup):
    """Extracts business name using metadata, title tags, and page headers."""
    # 1. JSON-LD metadata
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get('name'):
                    return item.get('name').strip()
        except Exception:
            continue
            
    # 2. Meta tags
    for tag_name in ['property="og:site_name"', 'property="og:title"', 'name="application-name"']:
        tag = soup.find('meta', attrs=dict([t.split('=') for t in tag_name.replace('"', '').split()]))
        if tag and tag.get('content'):
            return tag.get('content').strip()
            
    # 3. Cleaned page title
    title_tag = soup.find('title')
    if title_tag and title_tag.text:
        title_text = title_tag.text.strip()
        # Strip common title page endings
        for suffix in [' | Home', ' - Home', ' | Welcome', ' - Welcome', ' - Official Site', ' | Official Website', ' | Contact', ' - Contact']:
            if title_text.endswith(suffix):
                title_text = title_text[:-len(suffix)]
        return title_text
        
    # 4. First H1 tag
    h1 = soup.find('h1')
    if h1 and h1.text:
        return h1.text.strip()
        
    return ""

def extract_description(soup):
    """Extracts business description from page metadata or header tags."""
    # 1. Meta tag descriptions
    for tag in [{'name': 'description'}, {'property': 'og:description'}]:
        meta = soup.find('meta', attrs=tag)
        if meta and meta.get('content'):
            return meta.get('content').strip()
            
    # 2. JSON-LD description
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get('description'):
                    return item.get('description').strip()
        except Exception:
            continue
            
    # 3. Heuristic: Paragraph containing 'we are', 'founded in', 'specializes in', etc.
    for p in soup.find_all('p'):
        text = p.text.strip()
        if 50 < len(text) < 300:
            if any(kw in text.lower() for kw in ['we are', 'established in', 'founded in', 'specializes in', 'our mission', 'welcome to']):
                return text
                
    # 4. Fallback to first long paragraph
    for p in soup.find_all('p'):
        text = p.text.strip()
        if len(text) > 30:
            return text
            
    return ""

def extract_addresses(soup):
    """Extracts physical addresses from JSON-LD, address tags, and schema markers."""
    addresses = []
    
    # 1. JSON-LD PostalAddress
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                address_data = item.get('address')
                if address_data:
                    if isinstance(address_data, str):
                        addresses.append(address_data.strip())
                    elif isinstance(address_data, dict):
                        parts = []
                        for key in ['streetAddress', 'addressLocality', 'addressRegion', 'postalCode', 'addressCountry']:
                            val = address_data.get(key)
                            if val:
                                parts.append(str(val))
                        if parts:
                            addresses.append(', '.join(parts))
        except Exception:
            continue
            
    # 2. Address tag
    for addr in soup.find_all('address'):
        addr_text = addr.get_text(separator=' ', strip=True)
        if addr_text:
            addresses.append(addr_text)
            
    # 3. itemprop="address"
    for elem in soup.find_all(attrs={"itemprop": "address"}):
        text = elem.get_text(separator=' ', strip=True)
        if text:
            addresses.append(text)
            
    # 4. Heuristics: elements with address/location classes
    for class_name in ['address', 'location', 'contact-address']:
        for elem in soup.find_all(class_=re.compile(class_name, re.I)):
            text = elem.get_text(separator=' ', strip=True)
            # Ensure it is reasonably short and contains digits (streets/zip)
            if 15 < len(text) < 150 and any(c.isdigit() for c in text):
                addresses.append(text)
                
    # Clean duplicates while maintaining order
    unique_addresses = []
    for addr in addresses:
        cleaned = re.sub(r'\s+', ' ', addr).strip()
        if cleaned and cleaned not in unique_addresses:
            unique_addresses.append(cleaned)
            
    return unique_addresses

def extract_socials(soup):
    """Filters all links on the page for common social media platforms."""
    socials = {}
    social_platforms = {
        'facebook.com': 'Facebook',
        'twitter.com': 'Twitter',
        'x.com': 'Twitter',
        'linkedin.com': 'LinkedIn',
        'instagram.com': 'Instagram',
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'pinterest.com': 'Pinterest',
        'tiktok.com': 'TikTok',
        'yelp.com': 'Yelp'
    }
    
    for a in soup.find_all('a', href=True):
        href = a.get('href').strip()
        for domain, platform_name in social_platforms.items():
            if domain in href.lower():
                # Clean up query trackers from link
                clean_href = href.split('?')[0]
                # Exclude share intents
                if any(x in clean_href.lower() for x in ['share', 'intent', 'status', 'help', 'privacy']):
                    continue
                socials[platform_name] = clean_href
                
    return socials

def extract_hours(soup):
    """Extracts business operation hours from JSON-LD schema or text elements."""
    hours = []
    
    # 1. JSON-LD openingHours
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                oh = item.get('openingHours')
                if oh:
                    if isinstance(oh, list):
                        hours.extend(oh)
                    else:
                        hours.append(str(oh))
                oh_spec = item.get('openingHoursSpecification')
                if oh_spec:
                    specs = oh_spec if isinstance(oh_spec, list) else [oh_spec]
                    for spec in specs:
                        if isinstance(spec, dict):
                            days = spec.get('dayOfWeek')
                            opens = spec.get('opens')
                            closes = spec.get('closes')
                            if days and opens and closes:
                                day_str = ', '.join(days) if isinstance(days, list) else str(days)
                                hours.append(f"{day_str}: {opens} - {closes}")
        except Exception:
            continue
            
    if hours:
        return list(set(hours))
        
    # 2. Text heuristics matching hour elements
    hour_keywords = ['opening hours', 'hours of operation', 'business hours', 'open daily', 'mon-fri', 'mon - fri', 'saturday - sunday', 'hours:']
    candidates = []
    for tag in ['p', 'div', 'li', 'td', 'span', 'section']:
        for elem in soup.find_all(tag):
            text = elem.text.strip()
            # Look for reasonable length content that contains the keywords
            if len(text) < 150 and any(kw in text.lower() for kw in hour_keywords):
                # Search for weekday or timing identifiers in the text line by line
                for line in text.split('\n'):
                    line = line.strip()
                    if any(day in line.lower() for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'daily', 'everyday', 'closed']) and any(c.isdigit() for c in line):
                        candidates.append(line)
                        
    # Deduplicate candidates
    unique_hours = []
    for c in candidates:
        if c not in unique_hours:
            unique_hours.append(c)
            
    return unique_hours

def find_subpages(soup, base_url):
    """Finds links to 'Contact Us', 'About Us', or 'Locations' subpages on the homepage."""
    subpages = set()
    keywords = ['contact', 'about', 'location', 'hour', 'find-us', 'reach-us', 'support']
    
    for a in soup.find_all('a', href=True):
        href = a.get('href').strip()
        text = a.text.lower().strip()
        
        # Skip non-navigational links
        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')) or not href:
            continue
            
        # Match keywords in text or href
        if any(k in text or k in href.lower() for k in keywords):
            abs_url = urllib.parse.urljoin(base_url, href)
            # Ensure the subpage belongs to the same domain to prevent external redirects
            parsed_base = urllib.parse.urlparse(base_url)
            parsed_sub = urllib.parse.urlparse(abs_url)
            if parsed_base.netloc == parsed_sub.netloc:
                subpages.add(abs_url)
                if len(subpages) >= 3:  # Limit subpages to avoid rate-limiting
                    break
    return list(subpages)

def scrape_page(html, url):
    """
    Parses HTML content of a page and extracts relevant information.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Emails
    emails = []
    # Scan mailto hrefs
    for a in soup.find_all('a', href=re.compile(r'^mailto:', re.I)):
        href = a.get('href').strip()
        email_clean = href.split('?')[0].replace('mailto:', '').replace('MAILTO:', '').strip()
        if email_clean:
            emails.append(email_clean)
    # Scan text with regex
    email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', soup.get_text(separator=' '))
    emails.extend(email_matches)
    emails = clean_emails(emails)
    
    # 2. Phones
    phones = []
    # Scan tel hrefs
    for a in soup.find_all('a', href=re.compile(r'^tel:', re.I)):
        href = a.get('href').strip()
        phone_clean = href.split('?')[0].replace('tel:', '').replace('TEL:', '').strip()
        # Decode URL encoding (e.g. %20 or +)
        phone_clean = urllib.parse.unquote(phone_clean)
        if phone_clean:
            phones.append(phone_clean)
    # Scan text with regex
    phone_matches = re.findall(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', soup.get_text(separator=' '))
    phones.extend(phone_matches)
    phones = clean_phones(phones)
    
    # 3. Addresses
    addresses = extract_addresses(soup)
    
    # 4. Social Links
    social_links = extract_socials(soup)
    
    # 5. Hours
    hours = extract_hours(soup)
    
    # 6. Description
    description = extract_description(soup)
    
    # 7. Name
    name = extract_business_name(soup)
    
    return {
        "business_name": name,
        "description": description,
        "emails": emails,
        "phone_numbers": phones,
        "addresses": addresses,
        "social_links": social_links,
        "business_hours": hours
    }

def scrape_business(business_name):
    """
    Main orchestrator function. Searches DDG, finds domain, crawls homepage and subpages, and returns merged data.
    """
    # Result container initialized with default/fallback empty structures
    data = {
        "business_name": business_name,
        "website_url": "",
        "description": "",
        "emails": [],
        "phone_numbers": [],
        "addresses": [],
        "social_links": {},
        "business_hours": [],
        "other_contact_info": []
    }
    
    # 1. Search DDG
    search_results = search_duckduckgo(business_name)
    if not search_results:
        log_error("Could not find any search results on DuckDuckGo.")
        data["error"] = "No search results found on DuckDuckGo"
        return data
        
    # 2. Select first organic business website
    target_url = None
    log("Parsing search results for candidate business website...")
    
    # Grade each candidate URL
    scored_candidates = []
    for r in search_results:
        href = r.get('href')
        if href:
            score = get_website_score(href, business_name)
            # Only consider candidates that are not hard-excluded (score > -500)
            if score > -500:
                scored_candidates.append((score, href, r.get('title')))
                
    # Sort candidates by score descending (highest matches first)
    if scored_candidates:
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_match = scored_candidates[0]
        target_url = best_match[1]
        log(f"Selected target business URL: {target_url} (Title: '{best_match[2]}', Score: {best_match[0]})")
            
    if not target_url:
        if search_results:
            # Fallback to the first result domain if all were excluded or scored poorly
            target_url = search_results[0].get('href')
            log(f"No custom business website identified. Falling back to top result: {target_url}")
        else:
            log_error("No search results found to select a URL.")
            data["error"] = "No search results found"
            return data
        
    data["website_url"] = target_url
    
    # 3. Fetch homepage
    home_html = fetch_html(target_url)
    if not home_html:
        log_error(f"Could not load content from {target_url}.")
        data["error"] = f"Failed to retrieve content from {target_url}"
        return data
        
    # 4. Scrape homepage
    log("Scraping homepage...")
    home_data = scrape_page(home_html, target_url)
    
    # Update results with homepage content
    data["business_name"] = home_data["business_name"] or data["business_name"]
    data["description"] = home_data["description"]
    data["emails"] = home_data["emails"]
    data["phone_numbers"] = home_data["phone_numbers"]
    data["addresses"] = home_data["addresses"]
    data["social_links"] = home_data["social_links"]
    data["business_hours"] = home_data["business_hours"]
    
    # 5. Check for contact/about/locations subpages
    home_soup = BeautifulSoup(home_html, 'html.parser')
    subpages = find_subpages(home_soup, target_url)
    
    # Scrape found subpages to fill in missing gaps
    for idx, subpage in enumerate(subpages):
        log(f"Crawling subpage [{idx+1}/{len(subpages)}]: {subpage}")
        subpage_html = fetch_html(subpage)
        if subpage_html:
            sub_data = scrape_page(subpage_html, subpage)
            
            # Merge lists (emails, phone numbers, addresses, business hours)
            data["emails"] = list(set(data["emails"] + sub_data["emails"]))
            data["phone_numbers"] = list(set(data["phone_numbers"] + sub_data["phone_numbers"]))
            data["addresses"] = list(set(data["addresses"] + sub_data["addresses"]))
            data["business_hours"] = list(set(data["business_hours"] + sub_data["business_hours"]))
            
            # Merge social links
            data["social_links"].update(sub_data["social_links"])
            
            # Fill description or business name if missing
            if not data["description"] and sub_data["description"]:
                data["description"] = sub_data["description"]
            if data["business_name"] == business_name and sub_data["business_name"]:
                data["business_name"] = sub_data["business_name"]
                
    # final formatting cleanup
    data["emails"] = clean_emails(data["emails"])
    data["phone_numbers"] = clean_phones(data["phone_numbers"])
    
    return data

def generate_outreach_email(data):
    business_name = data.get("business_name") or "your business"
    clean_name = business_name.split('|')[0].split('-')[0].strip()
    
    website_url = data.get("website_url") or "your website"
    description = data.get("description") or ""
    
    # 1. Address / Locality Hook
    locality_text = ""
    addresses = data.get("addresses", [])
    if addresses:
        first_addr = addresses[0]
        # Try to extract City, State or similar
        match = re.search(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', first_addr)
        if match:
            city_state = f"{match.group(1).strip()}, {match.group(2).strip()}"
            locality_text = f"Since you have a physical presence in {city_state},"
        else:
            addr_snippet = first_addr if len(first_addr) < 40 else first_addr[:37] + "..."
            locality_text = f"Since you are located at {addr_snippet},"
            
    # 2. Contact channels hook
    contact_channels = []
    phones = data.get("phone_numbers", [])
    emails = data.get("emails", [])
    if phones:
        contact_channels.append(f"phone ({phones[0]})")
    if emails:
        contact_channels.append(f"email ({emails[0]})")
        
    contact_text = ""
    if contact_channels:
        contact_text = " or ".join(contact_channels)
        contact_hook = f"I noticed you make it easy for prospects to reach out via {contact_text}."
    else:
        contact_hook = "I checked out your website's contact options."

    # 3. Hours hook
    hours = data.get("business_hours", [])
    hours_hook = ""
    if hours:
        hours_snippet = hours[0]
        hours_hook = f" Seeing that you operate on {hours_snippet}, timing and responsiveness are critical to capturing leads when they are active."

    # 4. Social Media presence hook
    socials_dict = data.get("social_links", {})
    socials = list(socials_dict.keys())
    social_hook = ""
    if socials:
        if "Instagram" in socials_dict:
            social_hook = f"I also loved looking at your Instagram feed—great visual presentation!"
        elif "LinkedIn" in socials_dict:
            social_hook = f"I also noted your professional presence on LinkedIn, which is a great trust factor."
        else:
            social_hook = f"I noticed your active social media presence on {socials[0]}."
    else:
        social_hook = "I also noticed you have a clean website design, which is a great foundation."

    # 5. Industry / Business Type detection
    industry_type = "general"
    desc_lower = description.lower()
    name_lower = clean_name.lower()
    
    # Food/Bakery/Restaurant keywords
    food_keywords = ['bakery', 'coffee', 'cafe', 'restaurant', 'food', 'bread', 'pastry', 'dining', 'kitchen', 'pizza', 'brewery']
    # Tech/SaaS keywords
    tech_keywords = ['saas', 'software', 'tech', 'platform', 'app', 'api', 'digital product', 'developer', 'cloud', 'data']
    # Professional Services keywords
    service_keywords = ['consulting', 'law', 'legal', 'agency', 'financial', 'insurance', 'marketing', 'advisor', 'clinic', 'dentist', 'medical']
    
    if any(k in desc_lower or k in name_lower for k in food_keywords):
        industry_type = "food"
    elif any(k in desc_lower or k in name_lower for k in tech_keywords):
        industry_type = "tech"
    elif any(k in desc_lower or k in name_lower for k in service_keywords):
        industry_type = "services"

    # Custom hooks and pain points per industry
    if industry_type == "food":
        industry_intro = f"For culinary businesses like {clean_name}, driving local foot traffic and streamlining online ordering is the key to growth."
        pain_points = """1. Local SEO optimization to dominate "near me" Google searches in your area.
2. Mobile Menu & Ordering Streamlining: Making it effortless for customers to order directly from their phone.
3. Review Acquisition: Setting up automated flows to get customers to write 5-star reviews on Google and Yelp."""
    elif industry_type == "tech":
        industry_intro = f"For technology platforms like {clean_name}, minimizing self-serve signup friction and optimizing user onboarding are the highest leverage growth opportunities."
        pain_points = """1. Interactive Demos: Giving visitors an immediate, hands-on feel of your product on the landing page.
2. Sign-up Funnel Optimization: Eliminating fields and styling form elements to boost conversions.
3. Behavior-Based Retargeting: Implementing automated drip emails/SMS to re-engage users who drop off."""
    elif industry_type == "services":
        industry_intro = f"In the professional services space, building initial trust and reducing speed-to-lead are everything. Getting prospects to schedule a consultation immediately is the main goal."
        pain_points = """1. Frictionless Booking: Replacing contact forms with an embedded, real-time scheduler (like Calendly or Acuity).
2. Specialized Landing Pages: Creating dedicated, high-converting pages for each service vertical you offer.
3. Automated Instant Follow-Ups: Launching auto-replies so that new inquiries get a text or email within 60 seconds."""
    else:
        # General/Default
        industry_intro = f"For businesses like {clean_name}, optimizing the digital user journey and converting website traffic into inquiries is key to scaling sales."
        pain_points = """1. Conversion Rate Optimization: Streamlining layout and calls-to-action on your key pages.
2. Speed-to-Lead Automation: Ensuring every inquiry gets an immediate automated response before they contact a competitor.
3. Targeted Search Acquisition: Running high-yield local or industry campaigns to find prospects ready to buy."""

    # Build personalized hook based on description
    if description:
        desc_snippet = description
        if len(desc_snippet) > 150:
            desc_snippet = desc_snippet[:147] + "..."
        mission_hook = f"I was exploring your website ({website_url}) and reading about how {clean_name} is '{desc_snippet}'. {social_hook}"
    else:
        mission_hook = f"I was exploring your website ({website_url}) and learning more about the services offered at {clean_name}. {social_hook}"

    email_body = f"""Subject: Strategic Growth & Conversion Audit for {clean_name}

Dear {clean_name} Team,

{mission_hook}

{locality_text} {contact_hook}{hours_hook}

I'm reaching out because we specialize in helping companies optimize their digital conversion rates and scale their sales. {industry_intro}

Looking at your setup, we identified a few key areas where you might be leaving money on the table:
{pain_points}

We've helped similar businesses increase their sales pipeline and conversion rates by 25-40% using these exact strategies.

If you are open to it, I would love to share a short 10-minute video audit of your website with 3 actionable improvements you can implement immediately to boost your sales.

Would you be open to a quick call next Tuesday or Wednesday?

Best regards,

[Your Name]
[Your Contact Information]"""
    return email_body

def format_readable_report(results):
    report_lines = []
    for data in results:
        report_lines.append("=" * 60)
        report_lines.append(f"BUSINESS REPORT: {data.get('business_name', 'Unknown')}")
        report_lines.append("=" * 60)
        report_lines.append(f"Website URL: {data.get('website_url', 'N/A')}")
        report_lines.append(f"Description: {data.get('description', 'N/A')}")
        report_lines.append("")
        
        report_lines.append("Contact Emails:")
        emails = data.get('emails', [])
        if emails:
            for email in emails:
                report_lines.append(f"  - {email}")
        else:
            report_lines.append("  - None found")
        report_lines.append("")
        
        report_lines.append("Phone Numbers:")
        phones = data.get('phone_numbers', [])
        if phones:
            for phone in phones:
                report_lines.append(f"  - {phone}")
        else:
            report_lines.append("  - None found")
        report_lines.append("")
        
        report_lines.append("Physical Addresses:")
        addresses = data.get('addresses', [])
        if addresses:
            for addr in addresses:
                report_lines.append(f"  - {addr}")
        else:
            report_lines.append("  - None found")
        report_lines.append("")
        
        socials = data.get('social_links', {})
        report_lines.append("Social Media Links:")
        if socials:
            for platform, link in socials.items():
                report_lines.append(f"  - {platform}: {link}")
        else:
            report_lines.append("  - None found")
        report_lines.append("")
        
        report_lines.append("Business Hours:")
        hours = data.get('business_hours', [])
        if hours:
            for hr in hours:
                report_lines.append(f"  - {hr}")
        else:
            report_lines.append("  - None found")
            
        if "error" in data:
            report_lines.append(f"\n[Error occurred during scraping: {data['error']}]")
            
        report_lines.append("")
        report_lines.append("=" * 60)
        report_lines.append("PERSONALIZED OUTREACH EMAIL TEMPLATE")
        report_lines.append("=" * 60)
        report_lines.append(generate_outreach_email(data))
        report_lines.append("=" * 60)
        report_lines.append("\n")
        
    return "\n".join(report_lines)

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Error: Missing parameter.\n")
        sys.stderr.write(f"Usage: python {sys.argv[0]} \"Business Name\" OR python {sys.argv[0]} input_file.txt\n")
        sys.exit(1)
        
    input_arg = sys.argv[1]
    
    # 1. Determine input list
    if os.path.exists(input_arg):
        try:
            with open(input_arg, 'r') as f:
                businesses = [line.strip() for line in f if line.strip()]
        except Exception as e:
            sys.stderr.write(f"[ERROR] Failed to read input file {input_arg}: {e}\n")
            sys.exit(1)
    else:
        businesses = [input_arg]
        
    # Determine base name for output files
    if len(businesses) == 1:
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', businesses[0].lower()).strip('_')
        base_name = f"scraped_{sanitized}"
    else:
        base_name = "scraped_businesses"

    # Set up global log file path to write step-by-step info to
    global LOG_FILE
    LOG_FILE = f"{base_name}.txt"
    
    try:
        with open(LOG_FILE, 'w') as f:
            f.write(f"=== SCRAPING RUN STARTED AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"Target Businesses: {businesses}\n\n")
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to initialize log file {LOG_FILE}: {e}\n")
        sys.exit(1)

    log(f"Businesses to scrape: {businesses}")
    results = []
    
    # 2. Scrape each business
    for biz in businesses:
        log(f"\n=== Starting scrape for: {biz} ===")
        try:
            scraped_data = scrape_business(biz)
            # Add outreach email to JSON result
            scraped_data["outreach_email"] = generate_outreach_email(scraped_data)
            results.append(scraped_data)
        except Exception as e:
            log_error(f"Failed to scrape {biz}: {e}")
            results.append({
                "business_name": biz,
                "error": str(e),
                "website_url": "",
                "emails": [],
                "phone_numbers": [],
                "addresses": [],
                "social_links": {},
                "business_hours": [],
                "outreach_email": ""
            })
            
    # 3. Save output files
    json_file = f"{base_name}.json"
    
    try:
        # Save JSON
        with open(json_file, 'w') as f:
            json.dump(results[0] if len(businesses) == 1 else results, f, indent=2)
        
        # Save Human-readable report containing scraped details and customized email outreach
        readable_content = format_readable_report(results)
        with open(LOG_FILE, 'a') as f:
            f.write("\n\n" + "=" * 60 + "\n")
            f.write("=== FINAL SCRAPED RESULTS AND OUTREACH EMAIL ===\n")
            f.write("=" * 60 + "\n\n")
            f.write(readable_content)
            
        # Inform user in terminal of success and where to find verification files
        print(f"\n[DONE] Scraping completed successfully.")
        print(f"  - Verification log and report: {LOG_FILE}")
        print(f"  - Structured JSON data:         {json_file}\n")
        
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to save output files: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
