import re
from bs4 import BeautifulSoup
from core.utils import setup_logger

logger = setup_logger("intelligence.seo")

class SEOAnalyzer:
    @staticmethod
    def analyze(homepage_html, all_pages_data):
        """Analyze SEO indicators for the crawled pages."""
        soup = BeautifulSoup(homepage_html, 'html.parser')
        
        # 1. Title Analysis
        title = ""
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else ""
        title_length = len(title)
        
        # 2. Meta Description Analysis
        meta_desc = ""
        meta_node = soup.find('meta', attrs={"name": "description"})
        if meta_node:
            meta_desc = meta_node.get('content', '').strip()
        meta_length = len(meta_desc)
        
        # 3. Canonical Tag
        canonical_node = soup.find('link', rel='canonical')
        has_canonical = canonical_node is not None
        
        # 4. OpenGraph tags
        og_tags = {}
        for m in soup.find_all('meta', property=re.compile(r'^og:')):
            og_tags[m.get('property')] = m.get('content', '')
            
        # 5. Heading Structure
        h1_count = len(soup.find_all('h1'))
        h2_count = len(soup.find_all('h2'))
        h3_count = len(soup.find_all('h3'))
        
        # 6. Alt Text Coverage
        images = soup.find_all('img')
        total_images = len(images)
        missing_alt = 0
        for img in images:
            if not img.get('alt') or not img.get('alt').strip():
                missing_alt += 1
        alt_coverage_pct = 100.0 if total_images == 0 else ((total_images - missing_alt) / total_images) * 100
        
        # 7. Keyword Density & Readability
        body_text = soup.body.get_text(separator=' ') if soup.body else soup.get_text(separator=' ')
        keywords = SEOAnalyzer.calculate_keyword_density(body_text)
        readability_score = SEOAnalyzer.calculate_readability(body_text)
        
        # Determine SEO recommendations
        recommendations = []
        score = 100
        
        if title_length == 0:
            recommendations.append("Add a webpage <title> tag.")
            score -= 15
        elif title_length < 30 or title_length > 60:
            recommendations.append(f"Optimize title length (currently {title_length} chars, ideal is 30-60).")
            score -= 5
            
        if meta_length == 0:
            recommendations.append("Add a meta description for search engine result snippets.")
            score -= 15
        elif meta_length < 70 or meta_length > 160:
            recommendations.append(f"Optimize meta description length (currently {meta_length} chars, ideal is 70-160).")
            score -= 5
            
        if not has_canonical:
            recommendations.append("Add a rel='canonical' link to prevent duplicate content issues.")
            score -= 5
            
        if h1_count == 0:
            recommendations.append("Missing H1 heading on the homepage.")
            score -= 10
        elif h1_count > 1:
            recommendations.append(f"Multiple H1 headings found ({h1_count}). Use exactly one H1 for page structure.")
            score -= 5
            
        if alt_coverage_pct < 80 and total_images > 0:
            recommendations.append(f"Improve alt text coverage on images (currently {alt_coverage_pct:.1f}% covered).")
            score -= 10
            
        score = max(10, score)
        
        return {
            "score": score,
            "title": title,
            "title_length": title_length,
            "meta_description": meta_desc,
            "meta_length": meta_length,
            "has_canonical": has_canonical,
            "h1_count": h1_count,
            "h2_count": h2_count,
            "h3_count": h3_count,
            "total_images": total_images,
            "missing_alt_images": missing_alt,
            "alt_text_coverage_pct": alt_coverage_pct,
            "top_keywords": keywords,
            "readability_score": readability_score,
            "recommendations": recommendations
        }
        
    @staticmethod
    def calculate_keyword_density(text):
        """Analyze keyword frequency in body text."""
        # Simple stop words
        stopwords = {
            'the', 'and', 'a', 'to', 'of', 'in', 'is', 'i', 'that', 'it', 'on', 'you', 'this', 'for', 'but', 
            'with', 'as', 'are', 'we', 'our', 'us', 'your', 'my', 'their', 'they', 'them', 'an', 'at', 'by', 
            'from', 'or', 'be', 'an', 'has', 'have', 'was', 'were', 'will', 'would', 'can', 'should'
        }
        words = re.findall(r'\b[a-zA-Z]{3,15}\b', text.lower())
        total_words = len(words)
        if total_words == 0:
            return []
            
        freq = {}
        for w in words:
            if w not in stopwords:
                freq[w] = freq.get(w, 0) + 1
                
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [{"keyword": k, "count": c, "density_pct": (c / total_words) * 100} for k, c in sorted_freq]

    @staticmethod
    def calculate_readability(text):
        """Calculate basic Flesch Reading Ease score using syllables approximation."""
        sentences = len(re.split(r'[.!?]+', text))
        words = len(re.findall(r'\b\w+\b', text))
        if sentences == 0 or words == 0:
            return 100.0
            
        # Syllables count approximation
        def count_syllables(word):
            word = word.lower()
            count = 0
            vowels = "aeiouy"
            if len(word) == 0:
                return 0
            if word[0] in vowels:
                count += 1
            for index in range(1, len(word)):
                if word[index] in vowels and word[index - 1] not in vowels:
                    count += 1
            if word.endswith("e"):
                count -= 1
            if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
                count += 1
            if count == 0:
                count = 1
            return count

        syllables = sum(count_syllables(w) for w in re.findall(r'\b\w+\b', text))
        
        # Flesch Reading Ease Formula: 206.835 - 1.015 * (total_words/total_sentences) - 84.6 * (total_syllables/total_words)
        asl = words / sentences
        asw = syllables / words
        score = 206.835 - 1.015 * asl - 84.6 * asw
        return max(0.0, min(100.0, score))
