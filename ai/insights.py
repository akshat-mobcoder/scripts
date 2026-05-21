from core.utils import setup_logger

logger = setup_logger("ai.insights")

class InsightsGenerator:
    @staticmethod
    def generate_swot_and_gaps(data):
        """Analyze business data to output a structured SWOT analysis and growth gaps."""
        logger.info("Building SWOT analysis and technical growth opportunities...")
        
        scores = data.get("scores", {}).get("scores", {})
        seo = scores.get("seo", 70)
        perf = scores.get("performance", 70)
        cro = scores.get("conversion", 70)
        trust = scores.get("trust", 70)
        social = scores.get("social", 50)
        growth = scores.get("growth", 40)
        
        # 1. Strengths
        strengths = []
        if seo >= 75:
            strengths.append("Structured search metadata, including descriptive title and header configurations.")
        else:
            strengths.append("Valid canonical setup and link crawl-paths.")
            
        if perf >= 75:
            strengths.append("Highly optimized load speeds and low Total Blocking Time (TBT).")
        if cro >= 75:
            strengths.append("High-converting call-to-actions and direct booking/interaction channels.")
        if trust >= 75:
            strengths.append("Strong social proof backed by visible client reviews and testimonials.")
        if social >= 60:
            strengths.append("Broad visibility across popular social channels.")
            
        # 2. Weaknesses
        weaknesses = []
        if seo < 70:
            weaknesses.append("Missing alt tags on images, unoptimized headers, or long titles.")
        if perf < 70:
            weaknesses.append("High page load latency, which increases visitor bounce rates.")
        if cro < 70:
            weaknesses.append("Friction in user intake flow; no direct booking option or sticky CTA headers.")
        if trust < 70:
            weaknesses.append("Limited visible customer testimonials or trust certificates.")
        if social < 50:
            weaknesses.append("Inconsistent social presence or missing high-value profile networks.")
            
        # 3. Opportunities
        opportunities = []
        if seo < 75:
            opportunities.append("Configure proper header styling sequences (single H1) and add image alt text.")
        if perf < 75:
            opportunities.append("Compress heavy images and optimize server script load order to increase mobile performance.")
        if cro < 75:
            opportunities.append("Integrate inline widgets (like Calendly) and floating CTA elements to increase signups.")
        if social < 60:
            opportunities.append("Establish a branded presence on missing social channels to capture local traffic.")
            
        # 4. Threats
        threats = []
        if perf < 60:
            threats.append("Competitors with faster mobile sites capturing organic traffic due to lower bounce rates.")
        if cro < 60:
            threats.append("Inbound paid ad traffic bouncing due to complicated contact forms.")
        if trust < 60:
            threats.append("Lack of visual validation causing visitors to choose competitors with verified social proof.")
            
        # Compile lists
        if not strengths:
            strengths = ["Solid baseline business structure."]
        if not weaknesses:
            weaknesses = ["No major technical blockers identified."]
        if not opportunities:
            opportunities = ["Maintain current configurations and monitor search engine updates."]
        if not threats:
            threats = ["Minimal competitive exposure."]
            
        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats
        }
