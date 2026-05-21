from config import SCORING_WEIGHTS
from core.utils import setup_logger

logger = setup_logger("intelligence.scoring")

class BusinessScoringEngine:
    @staticmethod
    def calculate_scores(seo_results, perf_results, cro_results, reviews_results, social_results, hiring_results):
        """Aggregate scores into a weighted overall opportunity rating."""
        logger.info("Aggregating individual intelligence scores...")
        
        # 1. Map scores
        seo_score = seo_results.get("score", 70)
        perf_score = perf_results.get("score_performance", 70)
        cro_score = cro_results.get("score", 70)
        trust_score = reviews_results.get("reputation_score", 75)
        social_score = social_results.get("score", 50)
        
        # Growth Score mapping (0 open roles = 40, > 5 roles = 95)
        role_count = hiring_results.get("role_count", 0)
        if role_count == 0:
            growth_score = 40
        elif role_count < 3:
            growth_score = 65
        elif role_count < 7:
            growth_score = 85
        else:
            growth_score = 95
            
        # 2. Apply weights
        w = SCORING_WEIGHTS
        weighted_sum = (
            seo_score * w.get("seo", 0.25) +
            perf_score * w.get("performance", 0.15) +
            cro_score * w.get("conversion", 0.25) +
            trust_score * w.get("trust", 0.15) +
            social_score * w.get("social", 0.10) +
            growth_score * w.get("growth", 0.10)
        )
        
        overall_score = round(weighted_sum)
        
        # Lead Quality and Opportunity Level
        # High Opportunity = Low Score (needs a lot of help!)
        # Low Opportunity = High Score (site is already optimized)
        if overall_score < 50:
            opportunity_tier = "High"
            lead_quality = "Hot Lead (Requires Urgent Help)"
        elif overall_score < 75:
            opportunity_tier = "Medium"
            lead_quality = "Warm Lead (Optimize Gaps)"
        else:
            opportunity_tier = "Low"
            lead_quality = "Cold Lead (Highly Optimized)"
            
        return {
            "overall": overall_score,
            "opportunity_tier": opportunity_tier,
            "lead_quality": lead_quality,
            "scores": {
                "seo": seo_score,
                "performance": perf_score,
                "conversion": cro_score,
                "trust": trust_score,
                "social": social_score,
                "growth": growth_score
            }
        }
