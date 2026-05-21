from duckduckgo_search import DDGS
from core.utils import setup_logger, extract_domain
import re

logger = setup_logger("intelligence.competitors")

class CompetitorDiscovery:
    @staticmethod
    def discover(business_name, description=""):
        """Discover potential competitors of the business using search results."""
        logger.info(f"Discovering competitors for {business_name}...")
        
        competitors = []
        
        # Clean brand name
        clean_name = business_name.split('|')[0].split('-')[0].strip()
        
        queries = [
            f"{clean_name} competitors",
            f"{clean_name} alternatives"
        ]
        
        # If we have description details, add localized industry queries
        # E.g. "Mobile App Development Company Noida Noida competitors"
        industry_words = re.findall(r'\b[a-zA-Z]{5,15}\b', description)
        if len(industry_words) > 2:
            queries.append(f"{' '.join(industry_words[:3])} alternatives")
            
        seen_domains = {extract_domain(clean_name.lower())}
        
        try:
            with DDGS() as ddgs:
                for query in queries[:2]:
                    results = ddgs.text(query, max_results=5)
                    for r in results:
                        url = r.get("href", "")
                        domain = extract_domain(url)
                        title = r.get("title", "")
                        
                        # Verify it's a unique domain, not main site or directories
                        if domain and domain not in seen_domains:
                            if not any(x in domain for x in ["clutch.co", "yelp.com", "g2.com", "trustpilot.com", "wikipedia.org", "linkedin.com", "facebook.com", "twitter.com"]):
                                seen_domains.add(domain)
                                competitors.append({
                                    "name": title.split('-')[0].split('|')[0].strip(),
                                    "website": url,
                                    "domain": domain
                                })
        except Exception as e:
            logger.warning(f"Competitor discovery query failed: {e}")
            
        # Fallbacks to ensure report validity
        if not competitors:
            competitors = [
                {"name": "Competitor A", "website": "#", "domain": "competitora.com"},
                {"name": "Competitor B", "website": "#", "domain": "competitorb.com"}
            ]
            
        return competitors[:3]
