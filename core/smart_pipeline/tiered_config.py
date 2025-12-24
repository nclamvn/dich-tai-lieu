"""
Tiered Translation Config - Fine-tuned
AI Publisher Pro

Default: GPT-4o-mini (best balance of quality/cost)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class TranslationMode(Enum):
    """Translation modes with different cost/quality tradeoffs"""
    ECONOMY = "economy"      # Cheapest: Gemini Flash / DeepSeek
    BALANCED = "balanced"    # Default: GPT-4o-mini
    QUALITY = "quality"      # Best: Claude Sonnet / GPT-4o


class ContentType(Enum):
    """Content types for routing"""
    PLAIN_TEXT = "plain_text"           # Simple paragraphs
    FORMATTED_TEXT = "formatted_text"   # Headers, lists, emphasis
    TABLE = "table"                     # Tables
    CODE = "code"                       # Code blocks
    MATH_SIMPLE = "math_simple"         # Basic formulas
    MATH_COMPLEX = "math_complex"       # LaTeX, advanced math
    MIXED = "mixed"                     # Combination


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    provider: str
    model_id: str
    input_cost: float   # per 1M tokens
    output_cost: float  # per 1M tokens
    max_tokens: int = 4096
    temperature: float = 0.3
    supports_vision: bool = False

    @property
    def avg_cost(self) -> float:
        return (self.input_cost + self.output_cost) / 2


# =========================================
# Model Definitions
# =========================================

MODELS = {
    # Economy tier
    "gemini-flash": ModelConfig(
        provider="gemini",
        model_id="gemini-1.5-flash",
        input_cost=0.075,
        output_cost=0.30,
        max_tokens=8192,
        supports_vision=True
    ),
    "deepseek": ModelConfig(
        provider="deepseek",
        model_id="deepseek-chat",
        input_cost=0.27,
        output_cost=1.10,
        max_tokens=8192,
        supports_vision=False
    ),

    # Balanced tier (DEFAULT)
    "gpt-4o-mini": ModelConfig(
        provider="openai",
        model_id="gpt-4o-mini",
        input_cost=0.15,
        output_cost=0.60,
        max_tokens=16384,
        supports_vision=True
    ),
    "haiku": ModelConfig(
        provider="claude",
        model_id="claude-3-5-haiku-20241022",
        input_cost=0.25,
        output_cost=1.25,
        max_tokens=8192,
        supports_vision=True
    ),

    # Quality tier
    "gpt-4o": ModelConfig(
        provider="openai",
        model_id="gpt-4o",
        input_cost=2.50,
        output_cost=10.00,
        max_tokens=16384,
        supports_vision=True
    ),
    "sonnet": ModelConfig(
        provider="claude",
        model_id="claude-sonnet-4-20250514",
        input_cost=3.00,
        output_cost=15.00,
        max_tokens=8192,
        supports_vision=True
    ),
}


@dataclass
class TieredConfig:
    """
    Fine-tuned configuration for tiered translation.

    Default: GPT-4o-mini for best balance
    """

    # =========================================
    # Model Selection
    # =========================================

    # Default model for all content
    default_model: str = "gpt-4o-mini"

    # Models by tier
    economy_models: List[str] = field(default_factory=lambda: [
        "gemini-flash",  # Cheapest
        "deepseek",      # Good for Chinese
    ])

    balanced_models: List[str] = field(default_factory=lambda: [
        "gpt-4o-mini",   # DEFAULT - Best balance
        "haiku",         # Alternative
    ])

    quality_models: List[str] = field(default_factory=lambda: [
        "gpt-4o",        # High quality
        "sonnet",        # Highest quality
    ])

    # =========================================
    # Content-based Routing
    # =========================================

    # Which model to use for each content type
    content_routing: Dict[ContentType, str] = field(default_factory=lambda: {
        ContentType.PLAIN_TEXT: "gpt-4o-mini",       # Default
        ContentType.FORMATTED_TEXT: "gpt-4o-mini",   # Default
        ContentType.TABLE: "gpt-4o-mini",            # Good at structure
        ContentType.CODE: "gpt-4o-mini",             # Good at code
        ContentType.MATH_SIMPLE: "gpt-4o-mini",      # Can handle basic
        ContentType.MATH_COMPLEX: "gpt-4o",          # Upgrade for complex
        ContentType.MIXED: "gpt-4o-mini",            # Default
    })

    # =========================================
    # Thresholds for Content Detection
    # =========================================

    # OCR confidence threshold
    ocr_confidence_threshold: float = 0.65  # Below this = needs vision

    # Math detection
    math_symbol_ratio: float = 0.02      # % of text that is math symbols
    latex_pattern_count: int = 2         # Number of LaTeX patterns

    # Code detection
    code_keyword_count: int = 3          # def, function, class, etc.

    # Table detection
    table_indicator_count: int = 2       # |, ─, │, etc.

    # Complexity thresholds
    simple_max_length: int = 500         # Characters
    complex_min_indicators: int = 5      # Combined indicators

    # =========================================
    # Processing Settings
    # =========================================

    # Parallel processing
    max_concurrent: int = 10
    batch_size: int = 20

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0

    # Cache
    enable_cache: bool = True
    cache_ttl_hours: int = 168  # 7 days

    # =========================================
    # Cost Control
    # =========================================

    # Cost limits
    max_cost_per_page: float = 0.05     # Alert if > $0.05/page
    max_total_cost: float = 10.0        # Alert if > $10 total

    # Budget mode - force economy models
    budget_mode: bool = False

    # =========================================
    # Quality Settings
    # =========================================

    # Temperature by content type
    temperatures: Dict[ContentType, float] = field(default_factory=lambda: {
        ContentType.PLAIN_TEXT: 0.3,
        ContentType.FORMATTED_TEXT: 0.3,
        ContentType.TABLE: 0.1,          # More deterministic
        ContentType.CODE: 0.1,           # More deterministic
        ContentType.MATH_SIMPLE: 0.2,
        ContentType.MATH_COMPLEX: 0.1,   # Most deterministic
        ContentType.MIXED: 0.3,
    })

    def get_model_for_content(self, content_type: ContentType) -> ModelConfig:
        """Get the appropriate model for content type"""
        model_name = self.content_routing.get(content_type, self.default_model)

        # Override with budget mode
        if self.budget_mode:
            model_name = self.economy_models[0]

        return MODELS[model_name]

    def get_temperature(self, content_type: ContentType) -> float:
        """Get temperature for content type"""
        return self.temperatures.get(content_type, 0.3)


# =========================================
# Mode Presets
# =========================================

def get_economy_config() -> TieredConfig:
    """Economy mode - Cheapest possible"""
    config = TieredConfig()
    config.default_model = "gemini-flash"
    config.budget_mode = True
    config.content_routing = {ct: "gemini-flash" for ct in ContentType}
    return config


def get_balanced_config() -> TieredConfig:
    """Balanced mode - GPT-4o-mini default (RECOMMENDED)"""
    return TieredConfig()  # Default is already balanced


def get_quality_config() -> TieredConfig:
    """Quality mode - Best quality, higher cost"""
    config = TieredConfig()
    config.default_model = "gpt-4o"
    config.content_routing = {
        ContentType.PLAIN_TEXT: "gpt-4o",
        ContentType.FORMATTED_TEXT: "gpt-4o",
        ContentType.TABLE: "gpt-4o",
        ContentType.CODE: "gpt-4o",
        ContentType.MATH_SIMPLE: "gpt-4o",
        ContentType.MATH_COMPLEX: "sonnet",  # Best for complex math
        ContentType.MIXED: "gpt-4o",
    }
    return config


# =========================================
# Cost Estimator
# =========================================

def estimate_cost(
    pages: int,
    avg_tokens_per_page: int = 800,
    mode: TranslationMode = TranslationMode.BALANCED
) -> Dict:
    """
    Estimate translation cost.

    Args:
        pages: Number of pages
        avg_tokens_per_page: Average tokens per page
        mode: Translation mode

    Returns:
        Dict with cost breakdown
    """
    total_tokens = pages * avg_tokens_per_page

    # Get config for mode
    configs = {
        TranslationMode.ECONOMY: get_economy_config(),
        TranslationMode.BALANCED: get_balanced_config(),
        TranslationMode.QUALITY: get_quality_config(),
    }
    config = configs[mode]
    model = MODELS[config.default_model]

    # Calculate cost
    input_cost = (total_tokens / 1_000_000) * model.input_cost
    output_cost = (total_tokens / 1_000_000) * model.output_cost
    total_cost = input_cost + output_cost

    # Estimate time (assuming 10 concurrent, ~2s per request)
    pages_per_minute = 10 * 30  # 10 concurrent × 30 requests/min
    estimated_minutes = pages / pages_per_minute

    return {
        "mode": mode.value,
        "model": config.default_model,
        "pages": pages,
        "total_tokens": total_tokens,
        "input_cost": round(input_cost, 2),
        "output_cost": round(output_cost, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_page": round(total_cost / pages, 4),
        "estimated_minutes": round(estimated_minutes, 1),
    }


# =========================================
# Quick Reference
# =========================================

def print_model_comparison():
    """Print model comparison table"""
    print("\n📊 Model Comparison")
    print("=" * 70)
    print(f"{'Model':<20} {'Input':>10} {'Output':>10} {'Avg':>10} {'Vision':>10}")
    print("-" * 70)

    for name, model in sorted(MODELS.items(), key=lambda x: x[1].avg_cost):
        vision = "✓" if model.supports_vision else "✗"
        print(f"{name:<20} ${model.input_cost:>8.3f} ${model.output_cost:>8.2f} ${model.avg_cost:>8.2f} {vision:>10}")

    print("\n💡 Default: gpt-4o-mini (best balance of quality/cost)")


def print_cost_estimate(pages: int = 223):
    """Print cost estimates for different modes"""
    print(f"\n💰 Cost Estimate for {pages} pages")
    print("=" * 60)

    for mode in TranslationMode:
        est = estimate_cost(pages, mode=mode)
        print(f"\n{mode.value.upper()} mode ({est['model']}):")
        print(f"  Cost: ${est['total_cost']:.2f} (${est['cost_per_page']:.4f}/page)")
        print(f"  Time: ~{est['estimated_minutes']:.0f} minutes")


if __name__ == "__main__":
    print_model_comparison()
    print_cost_estimate(223)
