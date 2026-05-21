from bs4 import BeautifulSoup
from core.utils import setup_logger

logger = setup_logger("intelligence.techstack")

class TechStackDetector:
    @staticmethod
    def detect(html, page_url=""):
        """Detect underlying technologies from raw HTML contents."""
        soup = BeautifulSoup(html, 'html.parser')
        html_lower = html.lower()
        
        detected_tech = []
        
        # Define signature tests
        signatures = {
            # CMS & E-commerce
            "Shopify": {
                "scripts": ["shopify.com", "cdn.shopify.com"],
                "html": ["shopify-payment-button", "shopify-section"]
            },
            "WooCommerce": {
                "scripts": ["woocommerce", "wc-ajax"],
                "html": ["woocommerce-page", "woocommerce-layout"]
            },
            "WordPress": {
                "scripts": ["wp-content", "wp-includes"],
                "html": ["generator\" content=\"wordpress"]
            },
            "Wix": {
                "scripts": ["wix.com", "static.wixstatic.com"],
                "html": ["generator\" content=\"wix.com"]
            },
            "Squarespace": {
                "scripts": ["squarespace.com"],
                "html": ["generator\" content=\"squarespace"]
            },
            
            # Analytics & Tracking
            "Google Analytics (GA4)": {
                "scripts": ["googletagmanager.com/gtag/js", "ga4"],
                "html": ["gtag("]
            },
            "Google Tag Manager (GTM)": {
                "scripts": ["googletagmanager.com/gtm.js"],
                "html": ["gtm-t5mgj3l", "gtm.start"]
            },
            "Meta Pixel": {
                "scripts": ["connect.facebook.net"],
                "html": ["fbq(", "fbq('init'"]
            },
            "TikTok Pixel": {
                "scripts": ["tiktok.com/i18n/pixel"],
                "html": ["ttq.load("]
            },
            "Hotjar": {
                "scripts": ["static.hotjar.com", "hj("],
                "html": ["_hjsettings"]
            },
            
            # Chat & Inbound Leads
            "HubSpot": {
                "scripts": ["js.hs-scripts.com", "js.hs-analytics.net", "hubspot.com"],
                "html": ["hubspot-messages-iframe-container", "hs-script-loader"]
            },
            "Intercom": {
                "scripts": ["widget.intercom.io", "intercomsettings"],
                "html": ["window.intercom"]
            },
            "Drift": {
                "scripts": ["drift.com", "js.driftt.com"],
                "html": ["drift.load("]
            },
            "Zendesk Chat": {
                "scripts": ["assets.zendesk.com", "zopim.com"],
                "html": ["$zopim"]
            },
            "Calendly": {
                "scripts": ["calendly.com/assets/external/widget.js"],
                "html": ["calendly-inline-widget", "calendly.com/"]
            },
            
            # Marketing & CRM
            "Klaviyo": {
                "scripts": ["klaviyo.com", "static.klaviyo.com"],
                "html": ["klaviyo.push"]
            },
            "Mailchimp": {
                "scripts": ["mailchimp.com/embedcode", "chimpstatic.com"],
                "html": ["mc-embedded-subscribe-form"]
            },
            "Stripe": {
                "scripts": ["js.stripe.com"],
                "html": ["stripe.com/js", "stripe-payment-element"]
            }
        }
        
        # 1. Run detection rules
        for tech, sigs in signatures.items():
            found = False
            
            # Check script tags
            for script in soup.find_all('script', src=True):
                src = script['src'].lower()
                if any(term in src for term in sigs.get("scripts", [])):
                    found = True
                    break
                    
            if not found:
                # Check raw HTML
                if any(term in html_lower for term in sigs.get("html", [])):
                    found = True
                    
            if found:
                detected_tech.append(tech)
                
        return detected_tech
