from core.utils import setup_logger, extract_domain

logger = setup_logger("intelligence.social")

class SocialAnalyzer:
    @staticmethod
    def analyze(social_links, business_name=""):
        """Analyze social media footprint and brand alignment."""
        logger.info("Analyzing social media footprint...")
        
        detected_platforms = list(social_links.keys())
        
        # 1. Base Score calculation
        # 20 points for each active platform (max 80)
        base_score = min(80, len(detected_platforms) * 20)
        
        # 2. Branding consistency check
        # Check if the brand name or domain slug exists inside social profile links
        # E.g., if domain is mobcoder.com, check if social urls contain "mobcoder"
        consistency_score = 0
        slugs_found = []
        
        # Get target identifier
        target = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
        if len(target) > 5:
            target = target[:15]
        else:
            target = "bizslugplaceholder"
            
        matching_count = 0
        for platform, url in social_links.items():
            url_lower = url.lower()
            if target in url_lower:
                matching_count += 1
                
        # If > 50% of channels match name, add 20 points
        if len(detected_platforms) > 0 and (matching_count / len(detected_platforms)) >= 0.5:
            consistency_score = 20
            
        final_score = base_score + consistency_score
        
        # 3. Recommendations
        recommendations = []
        if len(detected_platforms) == 0:
            final_score = 15
            recommendations.append("Establish a social media presence (e.g., LinkedIn, Instagram, Facebook).")
        else:
            missing = [p for p in ["LinkedIn", "Facebook", "Instagram", "Twitter"] if p not in detected_platforms]
            if missing:
                recommendations.append(f"Create profiles on missing high-value platforms: {', '.join(missing)}.")
            if consistency_score == 0:
                recommendations.append("Standardize social media profile slugs to match your brand name for better SEO.")
                
        return {
            "score": final_score,
            "platforms_detected": detected_platforms,
            "consistency_score": consistency_score,
            "recommendations": recommendations
        }
import re
