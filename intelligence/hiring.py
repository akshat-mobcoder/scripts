import re
from bs4 import BeautifulSoup
from core.utils import setup_logger

logger = setup_logger("intelligence.hiring")

class HiringAnalyzer:
    @staticmethod
    def analyze(parsed_pages_data):
        """Analyze careers/jobs pages to extract open roles and growth signals."""
        logger.info("Analyzing hiring and growth signals...")
        
        has_careers_page = False
        careers_url = ""
        careers_html = ""
        
        # 1. Locate careers page
        for url, data in parsed_pages_data.items():
            if any(kw in url.lower() for kw in ["careers", "jobs", "join-us", "work-at", "careers-at"]):
                has_careers_page = True
                careers_url = url
                break
                
        open_roles = []
        ats_detected = []
        
        # Check ATS patterns
        ats_signatures = {
            "Greenhouse": ["boards.greenhouse.io"],
            "Lever": ["lever.co", "jobs.lever.co"],
            "Workable": ["workable.com", "jobs.workable.com"],
            "BreezyHR": ["breezy.hr"],
            "BambooHR": ["bamboohr.com"]
        }
        
        # Scan pages for links to ATS
        for url, data in parsed_pages_data.items():
            for link in data.get("social_links", {}).values():
                for ats, sigs in ats_signatures.items():
                    if any(sig in link.lower() for sig in sigs) and ats not in ats_detected:
                        ats_detected.append(ats)
                        
        # 2. Extract job roles from text
        # Look for headers or bullet points on careers/jobs page
        if has_careers_page:
            # Let's inspect raw HTML if we saved it in a separate crawl
            # (We will pass the crawled pages from the main orchestrator)
            pass
            
        # Common job titles keywords
        role_pattern = r'\b[A-Za-z\-/\s]{3,30}\b\s+(?:Engineer|Developer|Manager|Executive|Specialist|Associate|Lead|Representative|Analyst|Consultant|Director|Intern|Designer)\b'
        
        # Scan headings and parsed elements of careers pages
        role_sets = set()
        for url, data in parsed_pages_data.items():
            is_careers = any(kw in url.lower() for kw in ["careers", "jobs", "join-us", "work-at"])
            if is_careers:
                # Scan headings first
                headings = data.get("headings", {})
                for h_list in headings.values():
                    for h in h_list:
                        # Exclude general headers
                        if len(h) < 50 and any(kw in h.lower() for kw in ["engineer", "developer", "manager", "executive", "specialist", "sales", "marketing", "operations"]):
                            role_sets.add(h)
                
                # Regex match on text block
                # Just get a snippet of roles to avoid massive lists
                pass
                
        open_roles = list(role_sets)
        
        # Categorize roles
        departments = {
            "Engineering & Product": 0,
            "Sales & Marketing": 0,
            "Operations & Support": 0
        }
        
        for role in open_roles:
            role_l = role.lower()
            if any(x in role_l for x in ["engineer", "developer", "programmer", "architect", "designer", "product", "qa", "test"]):
                departments["Engineering & Product"] += 1
            elif any(x in role_l for x in ["sales", "marketing", "outreach", "growth", "business development", "seo", "account", "social"]):
                departments["Sales & Marketing"] += 1
            elif any(x in role_l for x in ["hr", "operations", "recruiting", "support", "finance", "admin", "legal"]):
                departments["Operations & Support"] += 1
                
        # Deduce operational growth focus
        growth_focus = "Stable"
        if len(open_roles) > 0:
            max_dept = max(departments, key=departments.get)
            if departments[max_dept] > 0:
                if max_dept == "Sales & Marketing":
                    growth_focus = "Sales Expansion & Revenue Growth"
                elif max_dept == "Engineering & Product":
                    growth_focus = "Product Development & Tech Scaling"
                else:
                    growth_focus = "Operations & Scale Optimization"
            else:
                growth_focus = "General Team Expansion"
                
        return {
            "has_careers_page": has_careers_page,
            "careers_url": careers_url,
            "ats_detected": ats_detected,
            "open_roles": open_roles[:12], # limit count
            "role_count": len(open_roles),
            "departments": departments,
            "growth_focus": growth_focus
        }
