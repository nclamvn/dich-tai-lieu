"""
Provider API Routes
AI Publisher Pro - Multi-Provider Support

Add these routes to your existing FastAPI app.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os

# Import provider manager
from ai_providers import (
    create_provider_manager,
    AIProviderManager,
    AIProviderType,
    PROVIDER_INFO
)

# =========================================
# Pydantic Models
# =========================================

class ProviderModel(BaseModel):
    """Single AI model info"""
    id: str
    name: str
    recommended: bool = False
    fast: bool = False


class ProviderInfo(BaseModel):
    """Provider information"""
    id: str
    name: str
    company: str
    description: str
    supports_vision: bool
    supports_streaming: bool
    models: List[ProviderModel]
    default_model: str
    is_available: bool = False
    is_current: bool = False


class SetProviderRequest(BaseModel):
    """Request to set provider"""
    provider: str = Field(..., description="Provider ID: claude, openai, gemini, deepseek")
    model: Optional[str] = Field(None, description="Specific model to use")


class SetProviderResponse(BaseModel):
    """Response after setting provider"""
    success: bool
    provider: str
    model: str
    message: str


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    providers: Dict[str, bool]


class ProvidersListResponse(BaseModel):
    """List of providers response"""
    providers: List[ProviderInfo]
    current: ProviderInfo


# =========================================
# Global Provider Manager
# =========================================

_provider_manager: Optional[AIProviderManager] = None


def get_provider_manager() -> AIProviderManager:
    """Get or create the global provider manager"""
    global _provider_manager
    
    if _provider_manager is None:
        # Initialize with environment variables
        api_keys = {}
        
        if os.getenv("ANTHROPIC_API_KEY"):
            api_keys["claude"] = os.getenv("ANTHROPIC_API_KEY")
        if os.getenv("OPENAI_API_KEY"):
            api_keys["openai"] = os.getenv("OPENAI_API_KEY")
        if os.getenv("GOOGLE_API_KEY"):
            api_keys["gemini"] = os.getenv("GOOGLE_API_KEY")
        if os.getenv("DEEPSEEK_API_KEY"):
            api_keys["deepseek"] = os.getenv("DEEPSEEK_API_KEY")
        
        default = os.getenv("DEFAULT_AI_PROVIDER", "claude")
        
        _provider_manager = create_provider_manager(
            default_provider=default,
            api_keys=api_keys if api_keys else None
        )
    
    return _provider_manager


def reset_provider_manager():
    """Reset the global provider manager (useful for testing)"""
    global _provider_manager
    _provider_manager = None


# =========================================
# Router
# =========================================

router = APIRouter(prefix="/api/v2/providers", tags=["AI Providers"])


@router.get("", response_model=ProvidersListResponse)
async def list_providers(
    manager: AIProviderManager = Depends(get_provider_manager)
):
    """
    List all available AI providers.
    
    Returns information about each provider including:
    - Supported models
    - Vision capabilities
    - Streaming support
    - Availability status
    """
    providers = []
    current_type = manager.current_provider
    available_providers = {p.type for p in manager.get_available_providers()}
    
    for ptype, info in PROVIDER_INFO.items():
        models = [
            ProviderModel(
                id=mid,
                name=mname,
                recommended=(mid == info.default_model),
                fast=("flash" in mid.lower() or "mini" in mid.lower() or "haiku" in mid.lower())
            )
            for mid, mname in info.models.items()
        ]
        
        providers.append(ProviderInfo(
            id=ptype.value,
            name=info.name,
            company=info.name.split()[0],  # e.g., "Anthropic" from "Anthropic Claude"
            description=info.description,
            supports_vision=info.supports_vision,
            supports_streaming=info.supports_streaming,
            models=models,
            default_model=info.default_model,
            is_available=(ptype in available_providers),
            is_current=(ptype == current_type)
        ))
    
    # Get current provider info
    current_info = PROVIDER_INFO[current_type]
    current = ProviderInfo(
        id=current_type.value,
        name=current_info.name,
        company=current_info.name.split()[0],
        description=current_info.description,
        supports_vision=current_info.supports_vision,
        supports_streaming=current_info.supports_streaming,
        models=[
            ProviderModel(id=mid, name=mname, recommended=(mid == current_info.default_model))
            for mid, mname in current_info.models.items()
        ],
        default_model=current_info.default_model,
        is_available=True,
        is_current=True
    )
    
    return ProvidersListResponse(providers=providers, current=current)


@router.get("/current")
async def get_current_provider(
    manager: AIProviderManager = Depends(get_provider_manager)
):
    """Get the currently selected AI provider"""
    current_type = manager.current_provider
    info = PROVIDER_INFO[current_type]
    
    return {
        "provider": current_type.value,
        "name": info.name,
        "description": info.description,
        "model": info.default_model,
        "supports_vision": info.supports_vision,
        "supports_streaming": info.supports_streaming,
        "available_models": list(info.models.keys())
    }


@router.post("/set", response_model=SetProviderResponse)
async def set_provider(
    request: SetProviderRequest,
    manager: AIProviderManager = Depends(get_provider_manager)
):
    """
    Set the active AI provider.
    
    Available providers:
    - **claude**: Anthropic Claude (best for nuanced translation)
    - **openai**: OpenAI GPT-4o (versatile, multimodal)
    - **gemini**: Google Gemini (fast, multilingual)
    - **deepseek**: DeepSeek (cost-effective)
    """
    provider_map = {
        "claude": AIProviderType.CLAUDE,
        "openai": AIProviderType.OPENAI,
        "chatgpt": AIProviderType.OPENAI,
        "gpt": AIProviderType.OPENAI,
        "gemini": AIProviderType.GEMINI,
        "google": AIProviderType.GEMINI,
        "deepseek": AIProviderType.DEEPSEEK,
    }
    
    provider_type = provider_map.get(request.provider.lower())
    if not provider_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {request.provider}. Available: claude, openai, gemini, deepseek"
        )
    
    # Check if provider is available
    available = {p.type for p in manager.get_available_providers()}
    if provider_type not in available:
        info = PROVIDER_INFO[provider_type]
        raise HTTPException(
            status_code=400,
            detail=f"Provider {request.provider} not available. Set {info.env_key} environment variable."
        )
    
    # Set provider
    manager.set_provider(provider_type)
    
    info = PROVIDER_INFO[provider_type]
    model = request.model or info.default_model
    
    return SetProviderResponse(
        success=True,
        provider=provider_type.value,
        model=model,
        message=f"Switched to {info.name} ({model})"
    )


@router.get("/health", response_model=HealthCheckResponse)
async def check_health(
    manager: AIProviderManager = Depends(get_provider_manager)
):
    """
    Check health status of all configured providers.
    
    Returns online/offline status for each provider.
    """
    health = await manager.health_check()
    
    all_healthy = all(health.values())
    any_healthy = any(health.values())
    
    if all_healthy:
        status = "healthy"
    elif any_healthy:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthCheckResponse(status=status, providers=health)


@router.post("/test")
async def test_provider(
    request: SetProviderRequest,
    manager: AIProviderManager = Depends(get_provider_manager)
):
    """
    Test a provider with a simple translation.
    
    Useful for verifying API keys and connectivity.
    """
    provider_map = {
        "claude": AIProviderType.CLAUDE,
        "openai": AIProviderType.OPENAI,
        "gemini": AIProviderType.GEMINI,
        "deepseek": AIProviderType.DEEPSEEK,
    }
    
    provider_type = provider_map.get(request.provider.lower())
    if not provider_type:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")
    
    try:
        response = await manager.translate(
            text="Hello, world!",
            source_lang="English",
            target_lang="Vietnamese",
            provider=provider_type,
            model=request.model
        )
        
        return {
            "success": True,
            "provider": provider_type.value,
            "model": response.model,
            "input": "Hello, world!",
            "output": response.content,
            "tokens_used": response.usage
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Provider test failed: {str(e)}"
        )


# =========================================
# Integration Helper
# =========================================

def integrate_with_app(app):
    """
    Integrate provider routes with existing FastAPI app.
    
    Usage:
        from fastapi import FastAPI
        from provider_routes import integrate_with_app
        
        app = FastAPI()
        integrate_with_app(app)
    """
    app.include_router(router)
    
    # Add startup event to validate providers
    @app.on_event("startup")
    async def check_providers_on_startup():
        manager = get_provider_manager()
        available = manager.get_available_providers()
        print(f"🤖 AI Providers available: {[p.name for p in available]}")
        print(f"🎯 Default provider: {manager.current_provider.value}")
