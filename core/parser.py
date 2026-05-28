import re
import json
import urllib.parse
from bs4 import BeautifulSoup
import extruct
from w3lib.html import get_base_url
from core.utils import setup_logger

logger = setup_logger("core.parser")

class HTMLParser:
    @staticmethod
    def parse_page(page_data, url):
        """Perform comprehensive raw data parsing on a page's HTML and intercept data."""
        html = page_data.get('html', '')
        network_data = page_data.get('network_data', [])
        storage_data = page_data.get('storage_data', {})
        
        soup = BeautifulSoup(html, 'html.parser')
        
        parsed_data = {
            "url": url,
            "title": HTMLParser.extract_title(soup),
            "meta_description": HTMLParser.extract_meta_description(soup),
            "headings": HTMLParser.extract_headings(soup),
            "emails": HTMLParser.extract_emails(soup, html),
            "phone_numbers": HTMLParser.extract_phones(soup, html),
            "addresses": HTMLParser.extract_addresses(soup, html),
            "social_links": HTMLParser.extract_socials(soup),
            "schema_ld": HTMLParser.extract_structured_data(html, url),
            "geo_coordinates": HTMLParser.extract_geo(soup, html),
            "hidden_json_data": HTMLParser.extract_hidden_json(soup),
            "business_hours": HTMLParser.extract_business_hours(soup, html),
            "ctas": HTMLParser.extract_ctas(soup, url),
            "forms": HTMLParser.extract_forms(soup),
            "has_testimonials": HTMLParser.has_testimonials(soup),
            "page_summary": HTMLParser.extract_page_summary(soup)
        }
        
        # Merge network data
        network_contacts = HTMLParser.extract_from_network(network_data)
        parsed_data["emails"].extend(network_contacts["emails"])
        parsed_data["phone_numbers"].extend(network_contacts["phones"])
        parsed_data["addresses"].extend(network_contacts["addresses"])

        hidden_contacts = parsed_data["hidden_json_data"]
        parsed_data["emails"].extend(hidden_contacts.get("emails", []))
        parsed_data["phone_numbers"].extend(hidden_contacts.get("phones", []))
        parsed_data["addresses"].extend(hidden_contacts.get("addresses", []))
        
        return parsed_data

    @staticmethod
    def _traverse_json_for_contacts(data, results):
        """Recursively traverse JSON to find contacts."""
        if isinstance(data, dict):
            for k, v in data.items():
                k_lower = str(k).lower()
                if 'email' in k_lower and isinstance(v, str) and '@' in v:
                    results['emails'].add(v)
                elif ('phone' in k_lower or 'tel' in k_lower) and isinstance(v, str):
                    results['phones'].add(v)
                elif 'address' in k_lower and isinstance(v, str):
                    results['addresses'].add(v)
                elif k_lower in ['lat', 'lng', 'latitude', 'longitude'] and isinstance(v, (int, float, str)):
                    results['geo'].add(f"{k}: {v}")
                else:
                    HTMLParser._traverse_json_for_contacts(v, results)
        elif isinstance(data, list):
            for item in data:
                HTMLParser._traverse_json_for_contacts(item, results)

    @staticmethod
    def extract_hidden_json(soup):
        """Phase 2: Hidden JSON Extraction"""
        results = {'emails': set(), 'phones': set(), 'addresses': set(), 'geo': set()}
        for script in soup.find_all('script'):
            if script.string:
                content = script.string.strip()
                # Look for common hydration patterns
                try:
                    if content.startswith('{') or content.startswith('['):
                        data = json.loads(content)
                        HTMLParser._traverse_json_for_contacts(data, results)
                    else:
                        # Try to extract JSON assigned to window variables
                        json_match = re.search(r'window\.__[A-Z_]+__\s*=\s*({.*});', content, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            HTMLParser._traverse_json_for_contacts(data, results)
                except Exception:
                    pass
        return {k: list(v) for k, v in results.items()}

    @staticmethod
    def extract_from_network(network_data):
        """Extract contacts from intercepted API/GraphQL JSON."""
        results = {'emails': set(), 'phones': set(), 'addresses': set()}
        for req in network_data:
            try:
                data = json.loads(req.get('body', '{}'))
                HTMLParser._traverse_json_for_contacts(data, results)
            except Exception:
                pass
        return {k: list(v) for k, v in results.items()}

    @staticmethod
    def extract_structured_data(html, url):
        """Phase 5: Structured Data Extraction via extruct"""
        try:
            base_url = get_base_url(html, url)
            data = extruct.extract(html, base_url=base_url, syntaxes=['json-ld', 'microdata', 'rdfa'])
            return data
        except Exception as e:
            logger.debug(f"extruct failed: {e}")
            return {}

    @staticmethod
    def extract_geo(soup, html):
        """Phase 10: Geo & Map Extraction"""
        coords = set()
        # Regex for maps coordinates
        for match in re.finditer(r'@(-?\d+\.\d+),(-?\d+\.\d+)', html):
            coords.add(f"{match.group(1)},{match.group(2)}")
        
        # iframe maps
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if 'google.com/maps' in src or 'maps.google' in src:
                # Try to extract pb parameter or q parameter
                q = urllib.parse.parse_qs(urllib.parse.urlparse(src).query).get('q')
                if q:
                    coords.add(q[0])
        return list(coords)

    @staticmethod
    def extract_title(soup):
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title['content'].strip()
        return ""

    @staticmethod
    def extract_meta_description(soup):
        meta = soup.find('meta', attrs={"name": "description"}) or soup.find('meta', attrs={"property": "og:description"})
        if meta and meta.get('content'):
            return meta['content'].strip()
        return ""

    @staticmethod
    def extract_headings(soup):
        headings = {f"h{i}": [] for i in range(1, 7)}
        for i in range(1, 7):
            for h in soup.find_all(f"h{i}"):
                text = h.get_text(separator=' ').strip()
                if text:
                    headings[f"h{i}"].append(re.sub(r'\s+', ' ', text))
        return headings

    @staticmethod
    def extract_emails(soup, html):
        emails = set()
        for a in soup.find_all('a', href=re.compile(r'^mailto:', re.I)):
            email = a.get('href').replace('mailto:', '').replace('MAILTO:', '').strip().split('?')[0]
            if email:
                emails.add(email.lower())
                
        # Phase 4: Better Regex on raw HTML
        pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
        for match in re.findall(pattern, html):
            if not any(match.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', 'email.com', 'example.com', '.js', '.css']):
                emails.add(match.lower())
        return list(emails)

    @staticmethod
    def extract_phones(soup, html):
        phones = set()
        for a in soup.find_all('a', href=re.compile(r'^tel:', re.I)):
            phone = a.get('href').replace('tel:', '').replace('TEL:', '').strip().split('?')[0]
            phone = urllib.parse.unquote(phone)
            if phone:
                phones.add(phone)
                
        # Phase 4: Better Regex on raw HTML
        pattern = r'(\+?\d[\d\-\(\)\.\s]{7,}\d)'
        for match in re.findall(pattern, html):
            clean_match = match.strip()
            digits_only = re.sub(r'\D', '', clean_match)
            if 9 <= len(digits_only) <= 15:
                # filter simple year ranges
                if not (len(digits_only) == 10 and digits_only.startswith(('202', '201'))):
                    phones.add(clean_match)
        return list(phones)

    @staticmethod
    def extract_addresses(soup, html):
        addresses = set()
        for elem in soup.find_all(class_=re.compile(r'address|location|contact-info', re.I)):
            text = elem.get_text(separator=' ').strip()
            if text and 10 < len(text) < 150:
                addresses.add(re.sub(r'\s+', ' ', text))
                
        # Phase 4: Robust Regex
        street_pattern = r'\d+\s+[A-Za-z0-9#\.\s]{3,40}(?:Street|St|Avenue|Ave|Road|Rd|Highway|Hwy|Boulevard|Blvd|Drive|Dr|Way|Court|Ct|Circle|Cir|Lane|Ln|Suite|Ste|Floor|Fl)\.?,?\s+[A-Za-z\s]{3,20},?\s+[A-Z]{2}\s+\d{5}'
        for match in re.finditer(street_pattern, html, re.I):
            addresses.add(re.sub(r'\s+', ' ', match.group(0)))
            
        return list(addresses)

    @staticmethod
    def extract_socials(soup):
        socials = {}
        social_platforms = {
            "LinkedIn": "linkedin.com",
            "Facebook": "facebook.com",
            "Instagram": "instagram.com",
            "Twitter": "twitter.com",
            "Twitter_X": "x.com",
            "YouTube": "youtube.com",
            "TikTok": "tiktok.com"
        }
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            for platform, domain in social_platforms.items():
                if domain in href.lower():
                    clean_href = href.split('?')[0]
                    if not any(x in clean_href.lower() for x in ['share', 'intent', 'status', 'privacy', 'help']):
                        mapped_platform = "Twitter" if platform in ["Twitter", "Twitter_X"] else platform
                        socials[mapped_platform] = clean_href
        return socials

    @staticmethod
    def extract_business_hours(soup, html):
        """Extract operating hours from schema-like text and visible page copy."""
        hours = set()
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                payload = json.loads(script.string or "{}")
                items = payload if isinstance(payload, list) else [payload]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    opening_hours = item.get("openingHours")
                    if isinstance(opening_hours, list):
                        hours.update(str(x) for x in opening_hours)
                    elif opening_hours:
                        hours.add(str(opening_hours))
                    specs = item.get("openingHoursSpecification")
                    specs = specs if isinstance(specs, list) else ([specs] if specs else [])
                    for spec in specs:
                        if isinstance(spec, dict):
                            days = spec.get("dayOfWeek")
                            opens = spec.get("opens")
                            closes = spec.get("closes")
                            if days and opens and closes:
                                day_text = ", ".join(days) if isinstance(days, list) else str(days)
                                hours.add(f"{day_text}: {opens}-{closes}")
            except Exception:
                continue

        day_pattern = re.compile(r"\b(mon|monday|tue|tues|tuesday|wed|wednesday|thu|thur|thurs|thursday|fri|friday|sat|saturday|sun|sunday|daily|everyday)\b", re.I)
        time_pattern = re.compile(r"(\d{1,2}:\d{2}\s*(am|pm|a\.m\.|p\.m\.)?|\d{1,2}\s*(am|pm|a\.m\.|p\.m\.)|closed|open 24)", re.I)
        text = soup.get_text(separator="\n")
        for line in text.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if 8 < len(line) < 120 and day_pattern.search(line) and time_pattern.search(line):
                hours.add(line)
        return sorted(hours)

    @staticmethod
    def extract_ctas(soup, page_url):
        """Extract likely conversion actions for outreach personalization."""
        cta_keywords = [
            "book", "schedule", "contact", "demo", "quote", "consultation",
            "reserve", "order", "shop", "pricing", "get started", "call"
        ]
        ctas = []
        for node in soup.find_all(["a", "button"]):
            text = re.sub(r"\s+", " ", node.get_text(separator=" ")).strip()
            href = node.get("href", "")
            haystack = f"{text} {href}".lower()
            if text and len(text) <= 80 and any(keyword in haystack for keyword in cta_keywords):
                ctas.append({
                    "text": text,
                    "href": urllib.parse.urljoin(page_url, href) if href else ""
                })
        return ctas[:25]

    @staticmethod
    def extract_forms(soup):
        """Summarize forms without storing visitor-entered values."""
        forms = []
        for form in soup.find_all("form"):
            inputs = form.find_all(["input", "select", "textarea"])
            labels = []
            for field in inputs:
                label = field.get("aria-label") or field.get("name") or field.get("placeholder") or field.get("type")
                if label:
                    labels.append(str(label)[:60])
            forms.append({
                "input_count": len(inputs),
                "method": (form.get("method") or "get").lower(),
                "action": form.get("action", ""),
                "fields": labels[:12]
            })
        return forms

    @staticmethod
    def has_testimonials(soup):
        text = soup.get_text(" ", strip=True).lower()
        if any(term in text for term in ["testimonial", "what our customers say", "case study", "trusted by", "reviews"]):
            return True
        return soup.find(class_=re.compile(r"testimonial|review|case-study|trusted", re.I)) is not None

    @staticmethod
    def extract_page_summary(soup):
        """Capture concise visible page signals useful for report and draft generation."""
        title = HTMLParser.extract_title(soup)
        description = HTMLParser.extract_meta_description(soup)
        h1s = HTMLParser.extract_headings(soup).get("h1", [])
        paragraphs = []
        for p in soup.find_all("p"):
            text = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
            if 50 <= len(text) <= 260:
                paragraphs.append(text)
            if len(paragraphs) >= 3:
                break
        return {
            "title": title,
            "description": description,
            "h1": h1s[:3],
            "paragraphs": paragraphs
        }
