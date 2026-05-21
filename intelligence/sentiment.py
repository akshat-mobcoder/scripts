from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from core.utils import setup_logger

logger = setup_logger("intelligence.sentiment")

class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        
    def analyze_text(self, text):
        """Analyze sentiment polarity and intensity of text."""
        if not text:
            return {"polarity": 0.0, "subjectivity": 0.0, "compound": 0.0, "label": "neutral"}
            
        # 1. TextBlob analysis
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # 2. VADER analysis (better for social/outreach context)
        vader_scores = self.analyzer.polarity_scores(text)
        compound = vader_scores.get("compound", 0.0)
        
        # Determine label
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
            
        return {
            "polarity": polarity,
            "subjectivity": subjectivity,
            "compound": compound,
            "label": label
        }
        
    def summarize_reviews(self, reviews_list):
        """Aggregate sentiment scores for a list of reviews/testimonials."""
        if not reviews_list:
            return {
                "average_rating": 4.0, # default neutral positive estimate
                "sentiment_label": "Neutral/No reviews found",
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "common_praise": [],
                "common_complaints": []
            }
            
        total_polarity = 0
        total_compound = 0
        pos = 0
        neg = 0
        neu = 0
        
        praises = []
        complaints = []
        
        praise_keywords = {
            "responsive": ["fast", "quick", "responsive", "helpful", "support", "service", "customer service"],
            "professional": ["professional", "expert", "quality", "clean", "beautiful"],
            "efficient": ["smooth", "easy", "efficient", "automated", "value", "great results"]
        }
        
        complaint_keywords = {
            "slow response": ["slow", "delayed", "waiting", "no response", "call back", "ignore"],
            "expensive": ["expensive", "pricey", "overpriced", "costly"],
            "poor UI / bugs": ["bug", "crash", "broken", "hard to use", "confusing", "error"]
        }
        
        for rev in reviews_list:
            text = rev.get("text", "")
            res = self.analyze_text(text)
            
            total_polarity += res["polarity"]
            total_compound += res["compound"]
            
            if res["label"] == "positive":
                pos += 1
                # Check praise
                for label, kws in praise_keywords.items():
                    if any(kw in text.lower() for kw in kws) and label not in praises:
                        praises.append(label)
            elif res["label"] == "negative":
                neg += 1
                # Check complaints
                for label, kws in complaint_keywords.items():
                    if any(kw in text.lower() for kw in kws) and label not in complaints:
                        complaints.append(label)
            else:
                neu += 1
                
        count = len(reviews_list)
        avg_polarity = total_polarity / count
        avg_compound = total_compound / count
        
        # Calculate rating mapping from compound (range -1 to 1 mapped to 1 to 5)
        # e.g., compound 0.8 -> rating 4.6
        avg_rating = round(((avg_compound + 1.0) / 2.0) * 4.0 + 1.0, 1)
        
        if avg_compound >= 0.2:
            sentiment_label = "Positive"
        elif avg_compound <= -0.2:
            sentiment_label = "Negative"
        else:
            sentiment_label = "Neutral"
            
        return {
            "average_rating": avg_rating,
            "sentiment_label": sentiment_label,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "common_praise": praises if praises else ["Good service"],
            "common_complaints": complaints if complaints else ["None detected"]
        }
