"""
Smart Tiered Pipeline - Cost-Effective Translation
AI Publisher Pro

Giảm chi phí 10-30x và thời gian 6-10x bằng cách:
1. OCR extraction thay vì Vision cho text thường
2. Tiered model selection (Haiku/DeepSeek cho bulk, Sonnet cho complex)
3. Parallel processing
4. Smart caching
"""

import asyncio
import hashlib
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

# OCR options
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    from paddleocr import PaddleOCR
    HAS_PADDLE = True
except ImportError:
    HAS_PADDLE = False

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False


class ContentComplexity(Enum):
    """Content complexity levels"""
    SIMPLE = "simple"      # Plain text, basic formatting
    MEDIUM = "medium"      # Tables, lists, some formatting
    COMPLEX = "complex"    # Math formulas, code, diagrams
    VISION_REQUIRED = "vision"  # Images that need visual analysis


class ModelTier(Enum):
    """Model tiers by cost/capability"""
    ECONOMY = "economy"    # DeepSeek, Gemini Flash - $0.10-0.30/1M
    STANDARD = "standard"  # Haiku, GPT-4o-mini - $0.25-1/1M  
    PREMIUM = "premium"    # Sonnet, GPT-4o - $3-15/1M
    VISION = "vision"      # Vision models - expensive


@dataclass
class PageAnalysis:
    """Analysis result for a single page"""
    page_num: int
    complexity: ContentComplexity
    has_images: bool
    has_formulas: bool
    has_tables: bool
    has_code: bool
    text_content: str
    confidence: float
    recommended_tier: ModelTier
    estimated_tokens: int


@dataclass
class TranslationCost:
    """Cost tracking"""
    input_tokens: int = 0
    output_tokens: int = 0
    vision_calls: int = 0
    model_calls: Dict[str, int] = field(default_factory=dict)
    
    @property
    def estimated_cost(self) -> float:
        """Estimate total cost in USD"""
        # Approximate costs per 1M tokens
        costs = {
            "deepseek-chat": (0.27, 1.10),
            "gemini-1.5-flash": (0.075, 0.30),
            "claude-3-5-haiku": (0.25, 1.25),
            "gpt-4o-mini": (0.15, 0.60),
            "claude-3-5-sonnet": (3.0, 15.0),
            "gpt-4o": (2.50, 10.0),
        }
        
        total = 0
        # Simplified estimation
        avg_input_cost = 0.5  # Average across models
        avg_output_cost = 2.0
        
        total += (self.input_tokens / 1_000_000) * avg_input_cost
        total += (self.output_tokens / 1_000_000) * avg_output_cost
        total += self.vision_calls * 0.05  # ~$0.05 per vision call
        
        return total


@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    # OCR settings
    ocr_engine: str = "paddle"  # paddle, tesseract, easyocr
    ocr_languages: List[str] = field(default_factory=lambda: ["ch_sim", "en"])
    
    # Model selection
    economy_model: str = "deepseek-chat"
    standard_model: str = "claude-3-5-haiku-20241022"
    premium_model: str = "claude-3-5-sonnet-20241022"
    
    # Thresholds
    formula_threshold: float = 0.3  # % of page with formulas to use premium
    complexity_threshold: float = 0.5  # Complexity score threshold
    
    # Parallel processing
    max_concurrent: int = 10  # Increase from 3
    batch_size: int = 20  # Process in batches
    
    # Cost limits
    max_cost_usd: float = 5.0  # Alert if exceeding
    prefer_economy: bool = True  # Prefer cheaper models


class SmartTieredPipeline:
    """
    Smart translation pipeline that minimizes cost and time.
    
    Strategy:
    1. Extract text via OCR (FREE) instead of Vision ($$$)
    2. Analyze complexity to choose appropriate model tier
    3. Use cheap models (DeepSeek/Haiku) for 80-90% of content
    4. Reserve expensive models for complex content
    5. Parallel processing for speed
    """
    
    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        provider_manager = None
    ):
        self.config = config or PipelineConfig()
        self.provider_manager = provider_manager
        self.cost_tracker = TranslationCost()
        self._ocr = None
        self._cache = {}
    
    def _init_ocr(self):
        """Initialize OCR engine"""
        if self._ocr is not None:
            return
        
        engine = self.config.ocr_engine.lower()
        
        if engine == "paddle" and HAS_PADDLE:
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                use_gpu=False,
                show_log=False
            )
            self._ocr_type = "paddle"
            
        elif engine == "easyocr" and HAS_EASYOCR:
            self._ocr = easyocr.Reader(['ch_sim', 'en'])
            self._ocr_type = "easyocr"
            
        elif HAS_TESSERACT:
            self._ocr_type = "tesseract"
            
        else:
            raise RuntimeError(
                "No OCR engine available. Install one of: "
                "paddleocr, easyocr, or pytesseract"
            )
    
    def extract_text_ocr(self, image_path: str) -> Tuple[str, float]:
        """
        Extract text from image using OCR.
        
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        self._init_ocr()
        
        if self._ocr_type == "paddle":
            result = self._ocr.ocr(image_path, cls=True)
            if not result or not result[0]:
                return "", 0.0
            
            lines = []
            confidences = []
            for line in result[0]:
                text = line[1][0]
                conf = line[1][1]
                lines.append(text)
                confidences.append(conf)
            
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            return "\n".join(lines), avg_conf
        
        elif self._ocr_type == "easyocr":
            result = self._ocr.readtext(image_path)
            lines = [r[1] for r in result]
            confidences = [r[2] for r in result]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            return "\n".join(lines), avg_conf
        
        elif self._ocr_type == "tesseract":
            import cv2
            img = cv2.imread(image_path)
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            # Tesseract doesn't give confidence easily
            return text, 0.8
        
        return "", 0.0
    
    def analyze_content_complexity(
        self,
        text: str,
        image_path: Optional[str] = None
    ) -> ContentComplexity:
        """
        Analyze content complexity to determine model tier.
        
        Indicators of complexity:
        - Math symbols: ∫, Σ, ∂, ∞, √, ≈, ≤, ≥
        - LaTeX patterns: \\frac, \\int, \\sum
        - Code patterns: def, function, class, import
        - Table patterns: |---|, multiple columns
        """
        
        # Math indicators
        math_symbols = set('∫∑∂∞√≈≤≥±×÷∈∉∀∃∅∩∪⊂⊃αβγδεζηθλμπσφω')
        latex_patterns = ['\\frac', '\\int', '\\sum', '\\prod', '\\lim', 
                         '\\sqrt', '\\partial', '\\infty', '$$', '$']
        
        # Code indicators
        code_patterns = ['def ', 'function ', 'class ', 'import ', 'from ',
                        'return ', 'if __', '#!/', '```']
        
        # Table indicators
        table_patterns = ['|---|', '| --- |', '+---+', '│', '┌', '└']
        
        text_lower = text.lower()
        
        # Count indicators
        math_count = sum(1 for c in text if c in math_symbols)
        latex_count = sum(1 for p in latex_patterns if p in text)
        code_count = sum(1 for p in code_patterns if p in text_lower)
        table_count = sum(1 for p in table_patterns if p in text)
        
        total_chars = len(text) or 1
        math_ratio = (math_count + latex_count * 10) / total_chars
        
        # Determine complexity
        if math_ratio > 0.05 or latex_count > 3:
            return ContentComplexity.COMPLEX
        elif code_count > 2:
            return ContentComplexity.COMPLEX
        elif table_count > 1:
            return ContentComplexity.MEDIUM
        elif len(text) < 100:
            # Very short - might be header/caption with image
            return ContentComplexity.VISION_REQUIRED
        else:
            return ContentComplexity.SIMPLE
    
    def select_model_tier(
        self,
        complexity: ContentComplexity,
        ocr_confidence: float
    ) -> ModelTier:
        """Select appropriate model tier based on analysis"""
        
        # Low OCR confidence = might need vision
        if ocr_confidence < 0.6:
            return ModelTier.VISION
        
        # Map complexity to tier
        tier_map = {
            ContentComplexity.SIMPLE: ModelTier.ECONOMY,
            ContentComplexity.MEDIUM: ModelTier.STANDARD,
            ContentComplexity.COMPLEX: ModelTier.PREMIUM,
            ContentComplexity.VISION_REQUIRED: ModelTier.VISION,
        }
        
        tier = tier_map.get(complexity, ModelTier.STANDARD)
        
        # Override to economy if configured
        if self.config.prefer_economy and tier == ModelTier.STANDARD:
            tier = ModelTier.ECONOMY
        
        return tier
    
    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Get model name for tier"""
        tier_models = {
            ModelTier.ECONOMY: self.config.economy_model,
            ModelTier.STANDARD: self.config.standard_model,
            ModelTier.PREMIUM: self.config.premium_model,
            ModelTier.VISION: self.config.premium_model,  # Vision uses premium
        }
        return tier_models.get(tier, self.config.economy_model)
    
    async def analyze_page(
        self,
        page_num: int,
        image_path: str
    ) -> PageAnalysis:
        """Analyze a single page"""
        
        # Extract text via OCR (FREE!)
        text, confidence = self.extract_text_ocr(image_path)
        
        # Analyze complexity
        complexity = self.analyze_content_complexity(text, image_path)
        
        # Select tier
        tier = self.select_model_tier(complexity, confidence)
        
        # Estimate tokens
        estimated_tokens = len(text.split()) * 1.5  # Rough estimate
        
        return PageAnalysis(
            page_num=page_num,
            complexity=complexity,
            has_images=complexity == ContentComplexity.VISION_REQUIRED,
            has_formulas=complexity == ContentComplexity.COMPLEX,
            has_tables='|' in text or '│' in text,
            has_code='def ' in text or 'function ' in text,
            text_content=text,
            confidence=confidence,
            recommended_tier=tier,
            estimated_tokens=int(estimated_tokens)
        )
    
    async def translate_page(
        self,
        analysis: PageAnalysis,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None
    ) -> str:
        """Translate a single page using appropriate tier"""
        
        # Check cache
        cache_key = hashlib.md5(
            f"{analysis.text_content}:{source_lang}:{target_lang}".encode()
        ).hexdigest()
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Get model for tier
        model = self.get_model_for_tier(analysis.recommended_tier)
        
        # Determine provider
        if "deepseek" in model:
            provider = "deepseek"
        elif "gemini" in model:
            provider = "gemini"
        elif "gpt" in model:
            provider = "openai"
        else:
            provider = "claude"
        
        # Translate
        if self.provider_manager:
            response = await self.provider_manager.translate(
                text=analysis.text_content,
                source_lang=source_lang,
                target_lang=target_lang,
                context=context,
                provider=provider,
                model=model
            )
            translated = response.content
            
            # Track cost
            if response.usage:
                self.cost_tracker.input_tokens += response.usage.get("input_tokens", 0)
                self.cost_tracker.output_tokens += response.usage.get("output_tokens", 0)
        else:
            # Placeholder for testing
            translated = f"[TRANSLATED:{analysis.page_num}] {analysis.text_content[:100]}..."
        
        # Cache result
        self._cache[cache_key] = translated
        
        # Track model usage
        self.cost_tracker.model_calls[model] = \
            self.cost_tracker.model_calls.get(model, 0) + 1
        
        return translated
    
    async def process_document(
        self,
        image_paths: List[str],
        source_lang: str = "Chinese",
        target_lang: str = "Vietnamese",
        on_progress: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process entire document with smart tiered pipeline.
        
        Returns:
            Dict with translations, stats, and cost info
        """
        start_time = time.time()
        total_pages = len(image_paths)
        
        # Phase 1: Analyze all pages (parallel)
        print(f"📊 Analyzing {total_pages} pages...")
        
        analysis_tasks = [
            self.analyze_page(i, path)
            for i, path in enumerate(image_paths)
        ]
        
        analyses = await asyncio.gather(*analysis_tasks)
        
        # Print analysis summary
        tier_counts = {}
        for a in analyses:
            tier = a.recommended_tier.value
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        print(f"📈 Tier distribution:")
        for tier, count in tier_counts.items():
            pct = count / total_pages * 100
            print(f"   {tier}: {count} pages ({pct:.1f}%)")
        
        # Estimate cost before proceeding
        estimated_cost = self._estimate_cost(analyses)
        print(f"💰 Estimated cost: ${estimated_cost:.2f}")
        
        if estimated_cost > self.config.max_cost_usd:
            print(f"⚠️ Warning: Estimated cost exceeds limit of ${self.config.max_cost_usd}")
        
        # Phase 2: Translate in batches (parallel within batch)
        print(f"🔄 Translating...")
        
        translations = []
        batch_size = self.config.max_concurrent
        
        for i in range(0, total_pages, batch_size):
            batch = analyses[i:i + batch_size]
            
            tasks = [
                self.translate_page(a, source_lang, target_lang)
                for a in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"❌ Error on page {i+j}: {result}")
                    translations.append(analyses[i+j].text_content)  # Keep original
                else:
                    translations.append(result)
            
            # Progress callback
            progress = min((i + len(batch)) / total_pages * 100, 100)
            if on_progress:
                on_progress(progress, i + len(batch), total_pages)
            
            print(f"   Progress: {progress:.1f}% ({i + len(batch)}/{total_pages})")
        
        elapsed = time.time() - start_time
        
        return {
            "translations": translations,
            "total_pages": total_pages,
            "elapsed_seconds": elapsed,
            "elapsed_minutes": elapsed / 60,
            "cost_estimate": self.cost_tracker.estimated_cost,
            "tier_distribution": tier_counts,
            "model_usage": self.cost_tracker.model_calls,
            "tokens": {
                "input": self.cost_tracker.input_tokens,
                "output": self.cost_tracker.output_tokens,
            }
        }
    
    def _estimate_cost(self, analyses: List[PageAnalysis]) -> float:
        """Estimate cost before processing"""
        # Cost per 1M tokens (input, output)
        tier_costs = {
            ModelTier.ECONOMY: (0.27, 1.10),     # DeepSeek
            ModelTier.STANDARD: (0.25, 1.25),   # Haiku
            ModelTier.PREMIUM: (3.0, 15.0),     # Sonnet
            ModelTier.VISION: (3.0, 15.0),      # Vision = Premium
        }
        
        total = 0
        for a in analyses:
            input_cost, output_cost = tier_costs.get(
                a.recommended_tier, 
                tier_costs[ModelTier.STANDARD]
            )
            
            # Estimate: input tokens + similar output
            tokens = a.estimated_tokens * 2
            cost = (tokens / 1_000_000) * (input_cost + output_cost)
            total += cost
        
        return total


# =========================================
# Cost Comparison Calculator
# =========================================

def compare_costs(pages: int, avg_tokens_per_page: int = 800):
    """Compare costs across different approaches"""
    
    total_tokens = pages * avg_tokens_per_page
    
    approaches = {
        "Current (Vision + Sonnet)": {
            "input_cost": 3.0,  # Vision is expensive
            "output_cost": 15.0,
            "vision_per_page": 0.05,
        },
        "Smart Pipeline (OCR + Mixed)": {
            "input_cost": 0.5,  # Weighted average
            "output_cost": 2.0,
            "vision_per_page": 0.005,  # Only 10% need vision
        },
        "Economy (OCR + DeepSeek)": {
            "input_cost": 0.27,
            "output_cost": 1.10,
            "vision_per_page": 0,
        },
        "Budget (OCR + Gemini Flash)": {
            "input_cost": 0.075,
            "output_cost": 0.30,
            "vision_per_page": 0,
        }
    }
    
    print(f"\n📊 Cost Comparison for {pages} pages ({total_tokens:,} tokens)")
    print("=" * 60)
    
    for name, costs in approaches.items():
        input_cost = (total_tokens / 1_000_000) * costs["input_cost"]
        output_cost = (total_tokens / 1_000_000) * costs["output_cost"]
        vision_cost = pages * costs["vision_per_page"]
        total = input_cost + output_cost + vision_cost
        
        print(f"\n{name}:")
        print(f"  Input:  ${input_cost:.2f}")
        print(f"  Output: ${output_cost:.2f}")
        print(f"  Vision: ${vision_cost:.2f}")
        print(f"  TOTAL:  ${total:.2f}")


if __name__ == "__main__":
    # Compare costs for 223 pages
    compare_costs(223, avg_tokens_per_page=1000)
