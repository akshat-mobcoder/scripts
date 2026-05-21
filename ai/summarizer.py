import os
import requests
from config import AI_CONFIG
from core.utils import setup_logger

logger = setup_logger("ai.summarizer")

class AISummarizer:
    @staticmethod
    def get_summary(data):
        """Generate a high-quality executive summary using LLMs or local template heuristics."""
        provider = AI_CONFIG.get("api_provider", "local")
        
        # Check online APIs first
        if provider == "openai" and AI_CONFIG.get("openai_api_key"):
            summary = AISummarizer._query_openai(data)
            if summary:
                return summary
        elif provider == "gemini" and AI_CONFIG.get("gemini_api_key"):
            summary = AISummarizer._query_gemini(data)
            if summary:
                return summary
                
        # Offline rule-based template engine fallback
        logger.info("Using local template heuristics for summary generation...")
        return AISummarizer._generate_local_summary(data)

    @staticmethod
    def _generate_local_summary(data):
        """Create highly contextual, professional, data-driven local summaries."""
        name = data.get("business_name") or "the business"
        clean_name = name.split('|')[0].split('-')[0].strip()
        
        scores = data.get("scores", {}).get("scores", {})
        seo = scores.get("seo", 70)
        perf = scores.get("performance", 70)
        cro = scores.get("conversion", 70)
        trust = scores.get("trust", 70)
        social = scores.get("social", 50)
        
        tech = data.get("tech_stack", [])
        tech_list = ", ".join(tech) if tech else "no tracking or CRM scripts detected"
        
        # Build sentences dynamically based on actual scores
        findings = []
        if perf < 60:
            findings.append("significant mobile performance bottlenecks, which may increase bounce rates")
        if cro < 65:
            findings.append("missing critical trust factors and Call-to-Action (CTA) anchors above the fold")
        if seo < 70:
            findings.append("unoptimized heading structures and alt image tags")
            
        findings_str = ", alongside ".join(findings) if findings else "a solid technical framework with minor adjustments needed"
        
        summary = (
            f"An executive review was performed on {clean_name}'s web operations and marketing readiness. "
            f"The site utilizes a tech stack consisting of {tech_list}. "
            f"We identified {findings_str}. "
            f"Addressing these core metrics can increase visitor conversion and lead intake."
        )
        return summary

    @staticmethod
    def _query_openai(data):
        """Query OpenAI API."""
        try:
            url = f"{AI_CONFIG['openai_base_url']}/chat/completions"
            headers = {
                "Authorization": f"Bearer {AI_CONFIG['openai_api_key']}",
                "Content-Type": "application/json"
            }
            prompt = f"Write a professional executive summary (2-3 sentences) for this business audit data: {str(data)}"
            payload = {
                "model": AI_CONFIG["openai_model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Failed to query OpenAI API: {e}")
        return None

    @staticmethod
    def _query_gemini(data):
        """Query Gemini API."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{AI_CONFIG['gemini_model']}:generateContent?key={AI_CONFIG['gemini_api_key']}"
            headers = {"Content-Type": "application/json"}
            prompt = f"Write a professional executive summary (2-3 sentences) for this business audit data: {str(data)}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.warning(f"Failed to query Gemini API: {e}")
        return None
