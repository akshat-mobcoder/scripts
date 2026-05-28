from core.utils import setup_logger

logger = setup_logger("ai.outreach")

class OutreachGenerator:
    @staticmethod
    def generate_messages(data):
        """Build channel-specific outreach drafts from permitted company-level data."""
        logger.info("Drafting personalized outreach templates...")
        
        name = data.get("business_name") or "your business"
        clean_name = name.split('|')[0].split('-')[0].strip()
        url = data.get("website_url") or "your website"
        description = data.get("description") or ""
        
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

        ctas = data.get("conversion_actions", [])
        cta_text = ""
        if ctas:
            top_cta = ctas[0].get("text", "")
            if top_cta:
                cta_text = f"I noticed your primary website action is '{top_cta}', so I focused the audit on reducing friction around that path."

        hours = data.get("business_hours", [])
        hours_text = ""
        if hours:
            hours_text = f"Your visible hours include {hours[0]}, which makes fast response time especially important when prospects are ready to act."

        # Social media context
        socials = list(data.get("social_links", {}).keys())
        social_text = ""
        if socials:
            social_text = f"We saw your active profiles on {', '.join(socials[:-1]) + ' and ' + socials[-1] if len(socials) > 1 else socials[0]}."
        else:
            social_text = "We also noticed you don't have active links to social media platforms in your main menu, which is a great way to build client trust."
            
        issues_formatted = "\n\n".join([f"- {iss}" for iss in issues])
        description_hook = ""
        if description:
            snippet = description if len(description) <= 160 else description[:157].rstrip() + "..."
            description_hook = f"I saw that {clean_name} positions itself around: \"{snippet}\""
        
        email_body = f"""Subject: Quick growth audit for {clean_name}

Hi {clean_name} Team,

I recently ran a quick performance and conversion audit on {url}. {social_text}

{description_hook}

{cta_text} {hours_text}

You have a great foundation, but I noticed a couple of technical adjustments that are likely costing you leads and sales:

{issues_formatted}

These are relatively straightforward adjustments that can increase your conversion rates by 15-30%.

I've put together a 10-minute video showing exactly how to fix these gaps. Would it be alright if I sent that video over? No strings attached.

If this is not relevant, reply "not interested" and I will not follow up.

Best regards,

[Your Name]
[Your Contact Info]"""

        whatsapp_body = f"""Hi {clean_name} Team, I reviewed {url} and found a few quick conversion opportunities:

1. {issues[0]}
{f"2. {issues[1]}" if len(issues) > 1 else ""}

{cta_text or "The fixes look practical and focused on getting more website visitors to take action."}

Would you like me to send a short video audit with 3 specific improvements? Reply STOP if you do not want messages."""

        sms_body = f"""Hi {clean_name}, I reviewed {url} and found quick website conversion wins. Can I send a short video audit with 3 fixes? Reply STOP to opt out."""

        return {
            "email": email_body,
            "whatsapp": whatsapp_body,
            "sms": sms_body
        }

    @staticmethod
    def generate_email(data):
        """Backward-compatible helper for existing reports."""
        return OutreachGenerator.generate_messages(data)["email"]
