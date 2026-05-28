from bs4 import BeautifulSoup
from core.utils import setup_logger

logger = setup_logger("intelligence.cro")

class CROAnalyzer:
    @staticmethod
    def analyze(homepage_html, parsed_pages_data, crawled_pages=None):
        """Analyze Conversion Rate Optimization (CRO) indices across the website."""
        soup = BeautifulSoup(homepage_html, 'html.parser')
        
        # 1. Check CTA above the fold
        has_cta_above_fold = False
        # Find first container / header
        header = soup.find('header') or soup.find(class_=lambda x: x and any(kw in x.lower() for kw in ['hero', 'banner', 'nav', 'header']))
        if header:
            cta_keywords = ['book', 'schedule', 'reserve', 'contact', 'hire', 'buy', 'shop', 'order', 'pricing', 'sign up', 'register', 'get started', 'try for free', 'demo']
            buttons = header.find_all(['button', 'a'])
            for btn in buttons:
                text = btn.get_text().strip().lower()
                if any(kw in text for kw in cta_keywords) and len(text) < 25:
                    has_cta_above_fold = True
                    break
                    
        # 2. Check for Booking Widget / Booking Option
        has_booking = False
        booking_keywords = ['calendly.com', 'acuityscheduling', 'book-online', 'schedule', 'booking', 'appointment']
        for page_url, data in parsed_pages_data.items():
            # Check script schemas or CTAs
            ctas = data.get("ctas", [])
            for cta in ctas:
                if any(kw in cta.get("href", "").lower() for kw in booking_keywords) or any(kw in cta.get("text", "").lower() for kw in ['book', 'appointment']):
                    has_booking = True
                    break
            if has_booking:
                break
                
        # 3. Check for Chat / Interaction Widgets
        has_chat = False
        chat_keywords = ['intercom', 'drift', 'zendesk', 'hubspot-messages', 'zopim', 'livechat']
        pages_to_check = crawled_pages if crawled_pages else { "home": homepage_html }
        for page_url, page_data in pages_to_check.items():
            html = page_data.get("html", "") if isinstance(page_data, dict) else str(page_data)
            if any(term in html.lower() for term in chat_keywords):
                has_chat = True
                break

                
        # 4. Check Form Field Complexity
        has_complex_forms = False
        max_form_fields = 0
        for page_url, data in parsed_pages_data.items():
            forms = data.get("forms", [])
            for form in forms:
                field_count = form.get("input_count", 0)
                if field_count > max_form_fields:
                    max_form_fields = field_count
                if field_count > 5:
                    has_complex_forms = True
                    
        # 5. Check Testimonials / Reviews (Social Proof)
        has_social_proof = False
        for page_url, data in parsed_pages_data.items():
            if data.get("has_testimonials", False):
                has_social_proof = True
                break
                
        # 6. Check Trust Signals
        has_trust_signals = False
        trust_keywords = ['secure', 'guarantee', 'ssl', 'certified', 'trusted by', 'partner', 'badge', 'privacy compliance', 'stripe secure']
        text = soup.get_text().lower()
        if any(term in text for term in trust_keywords) or soup.find(class_=lambda x: x and any(t in x.lower() for t in ['badge', 'trust', 'security'])):
            has_trust_signals = True
            
        # 7. Sticky CTA
        has_sticky_cta = False
        # Sticky styling check in tags
        for tag in soup.find_all(class_=lambda x: x and any(term in x.lower() for term in ['sticky', 'fixed-nav', 'fixed-header'])):
            has_sticky_cta = True
            break
            
        # Calculate Heuristics Score
        score = 100
        friction_points = []
        recommendations = []
        
        if not has_cta_above_fold:
            score -= 15
            friction_points.append("No prominent Call-to-Action (CTA) visible above the fold.")
            recommendations.append("Place a clear, high-contrast CTA button in the hero section above the fold (e.g., 'Book a Call', 'Get Started').")
            
        if not has_booking:
            score -= 15
            friction_points.append("No direct appointment booking or scheduler link found.")
            recommendations.append("Integrate a scheduling tool like Calendly or HubSpot Meetings to reduce friction for inbound leads.")
            
        if not has_social_proof:
            score -= 15
            friction_points.append("Lacks customer reviews, testimonials, or logos on-site.")
            recommendations.append("Add a testimonials section or trust logos to establish credibility and social proof on the homepage.")
            
        if not has_trust_signals:
            score -= 10
            friction_points.append("Few trust badges, security statements, or satisfaction guarantees.")
            recommendations.append("Incorporate trust badges, SSL icons, or satisfaction statements near forms to reassure prospects.")
            
        if has_complex_forms:
            score -= 10
            friction_points.append(f"High-friction contact form detected with {max_form_fields} fields.")
            recommendations.append(f"Simplify contact forms by reducing fields (currently max {max_form_fields} fields, aim for 3-4 fields).")
            
        if not has_chat:
            score -= 5
            friction_points.append("No live chat or interactive lead capture widgets.")
            recommendations.append("Install an interactive chat widget (e.g., HubSpot Chat, Drift) to capture visitors before they bounce.")
            
        score = max(20, score)
        
        return {
            "score": score,
            "has_cta_above_fold": has_cta_above_fold,
            "has_booking": has_booking,
            "has_chat": has_chat,
            "max_form_fields": max_form_fields,
            "has_complex_forms": has_complex_forms,
            "has_social_proof": has_social_proof,
            "has_trust_signals": has_trust_signals,
            "has_sticky_cta": has_sticky_cta,
            "friction_points": friction_points,
            "recommendations": recommendations
        }
