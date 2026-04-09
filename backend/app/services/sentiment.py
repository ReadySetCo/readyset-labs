"""
Sentiment Analyzer - Dual-mode sentiment classification.

Supports two modes:
1. RoBERTa (ML-based) - Best for social media (Twitter, TikTok, Instagram)
2. Keyword-based - Fast fallback when ML not available

The RoBERTa model used is 'cardiffnlp/twitter-roberta-base-sentiment-latest'
which is specifically trained on 124M tweets and handles:
- Sarcasm and irony
- Emoji and emoticons  
- Social media slang
- Informal language
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)

# Try to import transformers for RoBERTa
ROBERTA_AVAILABLE = False
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    ROBERTA_AVAILABLE = True
except ImportError:
    logger.warning("transformers/torch not installed. Using keyword-based sentiment only.")
    pipeline = None
    torch = None


class SentimentAnalyzer:
    """
    Simple sentiment analyzer using keyword matching.
    Fast and lightweight - no ML models required.
    """
    
    # Positive keywords with weights
    POSITIVE_WORDS = {
        # Strong positive (weight 2)
        "love": 2, "amazing": 2, "excellent": 2, "fantastic": 2, "outstanding": 2,
        "perfect": 2, "incredible": 2, "awesome": 2, "brilliant": 2, "exceptional": 2,
        "best": 2, "wonderful": 2, "superb": 2, "phenomenal": 2,
        
        # Medium positive (weight 1.5)
        "great": 1.5, "recommend": 1.5, "helpful": 1.5, "impressed": 1.5,
        "satisfied": 1.5, "happy": 1.5, "pleased": 1.5, "effective": 1.5,
        "reliable": 1.5, "quality": 1.5, "worth": 1.5,
        
        # Light positive (weight 1)
        "good": 1, "nice": 1, "like": 1, "enjoy": 1, "works": 1,
        "useful": 1, "easy": 1, "quick": 1, "fast": 1, "smooth": 1,
        "clean": 1, "simple": 1, "intuitive": 1, "friendly": 1,
        "professional": 1, "better": 1, "improved": 1
    }
    
    # Negative keywords with weights
    NEGATIVE_WORDS = {
        # Strong negative (weight -2)
        "hate": -2, "terrible": -2, "horrible": -2, "awful": -2, "worst": -2,
        "disgusting": -2, "scam": -2, "fraud": -2, "rip-off": -2, "ripoff": -2,
        "disaster": -2, "nightmare": -2, "useless": -2, "broken": -2,
        
        # Medium negative (weight -1.5)
        "bad": -1.5, "poor": -1.5, "disappointed": -1.5, "frustrating": -1.5,
        "annoying": -1.5, "waste": -1.5, "expensive": -1.5, "overpriced": -1.5,
        "slow": -1.5, "buggy": -1.5, "unreliable": -1.5, "difficult": -1.5,
        "confusing": -1.5, "complicated": -1.5, "unhelpful": -1.5,
        
        # Light negative (weight -1)
        "issue": -1, "problem": -1, "error": -1, "bug": -1, "crash": -1,
        "fail": -1, "failed": -1, "missing": -1, "lacking": -1, "wish": -1,
        "unfortunately": -1, "mediocre": -1, "average": -1, "okay": -0.5,
        "meh": -1, "disappointed": -1, "concern": -1, "worried": -1
    }
    
    # Negation words that flip sentiment
    NEGATION_WORDS = {
        "not", "no", "never", "don't", "doesn't", "didn't", "won't",
        "wouldn't", "couldn't", "can't", "cannot", "isn't", "aren't",
        "wasn't", "weren't", "hardly", "barely", "neither", "nor"
    }
    
    # Intensifiers that amplify sentiment
    INTENSIFIERS = {
        "very": 1.5, "really": 1.5, "extremely": 2, "incredibly": 2,
        "absolutely": 2, "totally": 1.5, "completely": 1.5, "highly": 1.5,
        "super": 1.5, "so": 1.3, "quite": 1.2, "fairly": 1.1
    }
    
    def __init__(self):
        pass
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with sentiment, score, confidence, and keywords found
        """
        if not text:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "positive_keywords": [],
                "negative_keywords": []
            }
        
        # Normalize text
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_score = 0.0
        negative_score = 0.0
        positive_keywords = []
        negative_keywords = []
        
        # Window for detecting negations (look back 3 words)
        for i, word in enumerate(words):
            # Check for negation in previous 3 words
            negated = False
            for j in range(max(0, i - 3), i):
                if words[j] in self.NEGATION_WORDS:
                    negated = True
                    break
            
            # Check for intensifier in previous word
            intensifier = 1.0
            if i > 0 and words[i - 1] in self.INTENSIFIERS:
                intensifier = self.INTENSIFIERS[words[i - 1]]
            
            # Score positive words
            if word in self.POSITIVE_WORDS:
                weight = self.POSITIVE_WORDS[word] * intensifier
                if negated:
                    negative_score += abs(weight)
                    negative_keywords.append(f"not {word}")
                else:
                    positive_score += weight
                    positive_keywords.append(word)
            
            # Score negative words
            elif word in self.NEGATIVE_WORDS:
                weight = abs(self.NEGATIVE_WORDS[word]) * intensifier
                if negated:
                    positive_score += weight * 0.5  # Negated negative = weak positive
                    positive_keywords.append(f"not {word}")
                else:
                    negative_score += weight
                    negative_keywords.append(word)
        
        # Calculate final score (-1 to 1)
        total = positive_score + negative_score
        if total == 0:
            score = 0.0
            confidence = 0.0
        else:
            score = (positive_score - negative_score) / max(total, 1)
            # Confidence based on number of sentiment words found
            confidence = min(1.0, total / 10)  # Max confidence at 10+ sentiment words
        
        # Classify sentiment
        if score > 0.2:
            sentiment = "positive"
        elif score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "positive_keywords": list(set(positive_keywords)),
            "negative_keywords": list(set(negative_keywords)),
            "positive_score": round(positive_score, 2),
            "negative_score": round(negative_score, 2)
        }
    
    def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment of multiple texts and aggregate results.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            Aggregated sentiment analysis
        """
        if not texts:
            return {
                "overall_sentiment": "neutral",
                "overall_score": 0.0,
                "distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "distribution_pct": {"positive": 0, "negative": 0, "neutral": 0},
                "top_positive_keywords": [],
                "top_negative_keywords": [],
                "individual_results": []
            }
        
        results = []
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        all_positive_keywords = []
        all_negative_keywords = []
        total_score = 0.0
        
        for text in texts:
            result = self.analyze(text)
            results.append(result)
            sentiment_counts[result["sentiment"]] += 1
            total_score += result["score"]
            all_positive_keywords.extend(result["positive_keywords"])
            all_negative_keywords.extend(result["negative_keywords"])
        
        # Calculate distribution percentages
        total = len(texts)
        distribution_pct = {
            k: round((v / total) * 100, 1) for k, v in sentiment_counts.items()
        }
        
        # Get top keywords by frequency
        from collections import Counter
        top_positive = Counter(all_positive_keywords).most_common(10)
        top_negative = Counter(all_negative_keywords).most_common(10)
        
        # Overall sentiment
        avg_score = total_score / total
        if avg_score > 0.1:
            overall_sentiment = "positive"
        elif avg_score < -0.1:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"
        
        return {
            "overall_sentiment": overall_sentiment,
            "overall_score": round(avg_score, 3),
            "distribution": sentiment_counts,
            "distribution_pct": distribution_pct,
            "top_positive_keywords": [kw for kw, _ in top_positive],
            "top_negative_keywords": [kw for kw, _ in top_negative],
            "total_analyzed": total
        }
    
    def classify_for_scraping(self, text: str) -> Tuple[str, float]:
        """
        Quick classification for scraped data.
        Returns just sentiment and score for efficiency.
        
        Args:
            text: Text to classify
            
        Returns:
            Tuple of (sentiment, score)
        """
        result = self.analyze(text)
        return result["sentiment"], result["score"]


class RoBERTaSentimentAnalyzer:
    """
    ML-based sentiment analyzer using RoBERTa trained on Twitter data.
    
    Uses 'cardiffnlp/twitter-roberta-base-sentiment-latest' which is
    trained on ~124M tweets and specifically designed for social media.
    
    Benefits over keyword-based:
    - Understands context and sarcasm
    - Handles emoji and emoticons
    - Trained on social media language (slang, abbreviations)
    - Much more accurate for Twitter, TikTok, Instagram content
    """
    
    MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    
    def __init__(self):
        self._pipeline = None
        self._available = False
        self._load_error = None
        
    def _ensure_loaded(self):
        """Lazy load the model on first use."""
        if self._pipeline is not None or self._load_error is not None:
            return
            
        if not ROBERTA_AVAILABLE:
            self._load_error = "transformers/torch not installed"
            return
            
        try:
            # Auto-detect GPU
            device = 0 if torch and torch.cuda.is_available() else -1
            device_name = torch.cuda.get_device_name(0) if device == 0 else "CPU"
            logger.info(f"Loading RoBERTa model: {self.MODEL_NAME} on {device_name}")
            self._pipeline = pipeline(
                "sentiment-analysis",
                model=self.MODEL_NAME,
                tokenizer=self.MODEL_NAME,
                device=device
            )
            self._available = True
            logger.info("RoBERTa model loaded successfully")
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"Failed to load RoBERTa model: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if RoBERTa model is loaded and available."""
        self._ensure_loaded()
        return self._available
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment using RoBERTa.
        
        Args:
            text: Text to analyze (max 512 tokens)
            
        Returns:
            Dict with sentiment, score, confidence, and model info
        """
        self._ensure_loaded()
        
        if not self._available:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "model": "none",
                "error": self._load_error
            }
        
        if not text or not text.strip():
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "model": "roberta"
            }
        
        try:
            # Truncate to max 512 chars (model limit is ~512 tokens)
            truncated = text[:512]
            result = self._pipeline(truncated)[0]
            
            # Map RoBERTa labels to our format
            # RoBERTa uses: positive, neutral, negative
            label = result["label"].lower()
            confidence = result["score"]
            
            # Convert to -1 to 1 score
            if label == "positive":
                score = confidence
            elif label == "negative":
                score = -confidence
            else:  # neutral
                score = 0.0
            
            return {
                "sentiment": label,
                "score": round(score, 3),
                "confidence": round(confidence, 3),
                "model": "roberta",
                "raw_label": result["label"],
                "raw_score": result["score"]
            }
            
        except Exception as e:
            logger.error(f"RoBERTa analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "model": "roberta",
                "error": str(e)
            }
    
    def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment of multiple texts with RoBERTa.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            Aggregated sentiment analysis
        """
        if not texts:
            return {
                "overall_sentiment": "neutral",
                "overall_score": 0.0,
                "distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "distribution_pct": {"positive": 0, "negative": 0, "neutral": 0},
                "total_analyzed": 0,
                "model": "roberta"
            }
        
        self._ensure_loaded()
        
        results = []
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        total_score = 0.0
        
        for text in texts:
            result = self.analyze(text)
            results.append(result)
            sentiment_counts[result["sentiment"]] += 1
            total_score += result["score"]
        
        total = len(texts)
        distribution_pct = {
            k: round((v / total) * 100, 1) for k, v in sentiment_counts.items()
        }
        
        avg_score = total_score / total
        if avg_score > 0.1:
            overall_sentiment = "positive"
        elif avg_score < -0.1:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"
        
        return {
            "overall_sentiment": overall_sentiment,
            "overall_score": round(avg_score, 3),
            "distribution": sentiment_counts,
            "distribution_pct": distribution_pct,
            "total_analyzed": total,
            "model": "roberta"
        }
    
    def classify_for_scraping(self, text: str) -> Tuple[str, float]:
        """
        Quick classification for scraped data.
        Returns just sentiment and score for efficiency.
        """
        result = self.analyze(text)
        return result["sentiment"], result["score"]


# =============================================================================
# Singleton instances and helper functions
# =============================================================================

_keyword_analyzer = None
_roberta_analyzer = None


def get_sentiment_analyzer(prefer_ml: bool = True) -> "SentimentAnalyzer | RoBERTaSentimentAnalyzer":
    """
    Get the appropriate sentiment analyzer.
    
    Args:
        prefer_ml: If True, prefer RoBERTa ML-based analyzer (default)
                   If False, use keyword-based analyzer
    
    Returns:
        Either RoBERTaSentimentAnalyzer or SentimentAnalyzer
    """
    global _keyword_analyzer, _roberta_analyzer
    
    if prefer_ml and ROBERTA_AVAILABLE:
        if _roberta_analyzer is None:
            _roberta_analyzer = RoBERTaSentimentAnalyzer()
        if _roberta_analyzer.is_available:
            return _roberta_analyzer
    
    # Fallback to keyword-based
    if _keyword_analyzer is None:
        _keyword_analyzer = SentimentAnalyzer()
    return _keyword_analyzer


def get_roberta_analyzer() -> Optional[RoBERTaSentimentAnalyzer]:
    """Get the RoBERTa analyzer if available, None otherwise."""
    global _roberta_analyzer
    
    if not ROBERTA_AVAILABLE:
        return None
    
    if _roberta_analyzer is None:
        _roberta_analyzer = RoBERTaSentimentAnalyzer()
    
    return _roberta_analyzer if _roberta_analyzer.is_available else None


def get_keyword_analyzer() -> SentimentAnalyzer:
    """Get the keyword-based analyzer (always available)."""
    global _keyword_analyzer
    if _keyword_analyzer is None:
        _keyword_analyzer = SentimentAnalyzer()
    return _keyword_analyzer


def analyze_sentiment(text: str, use_ml: bool = True) -> Dict[str, Any]:
    """
    Analyze sentiment of a single text.
    
    Args:
        text: Text to analyze
        use_ml: If True, prefer RoBERTa (default). If False, use keywords.
    
    Returns:
        Dict with sentiment analysis results
    """
    return get_sentiment_analyzer(prefer_ml=use_ml).analyze(text)


def classify_sentiment(text: str, use_ml: bool = True) -> Tuple[str, float]:
    """
    Quick classify sentiment for scraped data.
    
    Args:
        text: Text to classify
        use_ml: If True, prefer RoBERTa (default). If False, use keywords.
    
    Returns:
        Tuple of (sentiment label, score)
    """
    return get_sentiment_analyzer(prefer_ml=use_ml).classify_for_scraping(text)


def is_roberta_available() -> bool:
    """Check if RoBERTa sentiment analysis is available."""
    analyzer = get_roberta_analyzer()
    return analyzer is not None and analyzer.is_available








