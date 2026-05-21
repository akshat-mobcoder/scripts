from core.utils import setup_logger

logger = setup_logger("ai.outreach")

class OutreachGenerator:
    @staticmethod
    def generate_email(data):
        """Build a personalized sales outreach email highlighting key gaps found in the audit."""
        logger.info("Drafting personalized outreach templates...")
        
        name = data.get("business_name") or "your business"
        clean_name = name.split('|')[0].split('-')[0].strip()
        url = data.get("website_url") or "your website"
        
        scores = data.get("scores", {}).get("scores", {})
        seo = scores.get("seo", 70)
        perf = scores.get("performance", 70)
        cro = scores.get("conversion", 70)
        
        # Identify specific issues to highlight
        issues = []
        if perf < 70:
            load_time = data.get("performance", {}).get("lcp_s", 5.0)
            issues.append(f"Mobile Performance: The website takes around {load_time:.1f} seconds to fully load, which is likely causing mobile visitors to bounce before they contact you.")
        if cro < 70:
            issues.append("Lead Conversion Friction: There's no direct booking scheduler (like Calendly) or sticky call-to-action on the header, making it harder for prospects to initiate a call.")
        if seo < 70:
            issues.append("Search Visibility gaps: We noted alt text gaps on images and heading structure issues, which limits your organic search ranking opportunities.")
            
        if not issues:
            issues.append("Mobile Lead Capture: Adding conversational widgets and interactive elements could further optimize your client intake funnel.")
            
        # Social media context
        socials = list(data.get("social_links", {}).keys())
        social_text = ""
        if socials:
            social_text = f"We saw your active profiles on {', '.join(socials[:-1]) + ' and ' + socials[-1] if len(socials) > 1 else socials[0]}."
        else:
            social_text = "We also noticed you don't have active links to social media platforms in your main menu, which is a great way to build client trust."
            
        issues_formatted = "\n\n".join([f"- {iss}" for iss in issues])
        
        email_body = f"""Subject: Quick growth audit for {clean_name}

Hi {clean_name} Team,

I recently ran a quick performance and conversion audit on {url}. {social_text}

You have a great foundation, but I noticed a couple of technical adjustments that are likely costing you leads and sales:

{issues_formatted}

These are relatively straightforward adjustments that can increase your conversion rates by 15-30%.

I've put together a 10-minute video showing exactly how to fix these gaps. Would it be alright if I sent that video over? No strings attached.

Best regards,

[Your Name]
[Your Contact Info]"""
        return email_body
