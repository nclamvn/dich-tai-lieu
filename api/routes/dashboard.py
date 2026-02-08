"""
Cost Dashboard API Routes.

Exposes cost analytics and provider statistics via REST endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from api.services.provider_stats import ProviderStatsTracker
from api.services.cost_dashboard import CostDashboard

router = APIRouter(prefix="/api/dashboard", tags=["Cost Dashboard"])

# Module-level tracker (shared with the rest of the app)
_tracker: Optional[ProviderStatsTracker] = None
_dashboard: Optional[CostDashboard] = None


def get_dashboard() -> CostDashboard:
    """Get or create the cost dashboard singleton."""
    global _tracker, _dashboard
    if _dashboard is None:
        _tracker = ProviderStatsTracker()
        _dashboard = CostDashboard(_tracker)
    return _dashboard


def set_tracker(tracker: ProviderStatsTracker) -> None:
    """Set the tracker instance (for app startup wiring)."""
    global _tracker, _dashboard
    _tracker = tracker
    _dashboard = CostDashboard(tracker)


@router.get("/overview")
async def get_overview():
    """Get cost overview summary."""
    dashboard = get_dashboard()
    return dashboard.get_overview().to_dict()


@router.get("/providers")
async def get_provider_breakdown():
    """Get per-provider cost breakdown."""
    dashboard = get_dashboard()
    breakdown = dashboard.get_provider_breakdown()
    return [s.to_dict() for s in breakdown]


@router.get("/language-pairs")
async def get_language_pair_costs():
    """Get cost per language pair."""
    dashboard = get_dashboard()
    return dashboard.get_language_pair_costs()


@router.get("/estimate")
async def estimate_cost(
    pages: int = Query(default=1, ge=1, le=10000),
    language_pair: str = Query(default="*"),
    provider: Optional[str] = Query(default=None),
):
    """Estimate cost for a translation job."""
    dashboard = get_dashboard()
    estimate = dashboard.estimate_cost(
        pages=pages,
        language_pair=language_pair,
        provider=provider,
    )
    return estimate.to_dict()


@router.get("/cheapest")
async def get_cheapest_provider(
    language_pair: str = Query(default="*"),
):
    """Find the cheapest provider."""
    dashboard = get_dashboard()
    cheapest = dashboard.get_cheapest_provider(language_pair=language_pair)
    if not cheapest:
        return {"provider": None, "message": "No provider data available"}
    return cheapest.to_dict()


@router.get("/best-value")
async def get_best_value_provider(
    language_pair: str = Query(default="*"),
):
    """Find the best value (quality/cost ratio) provider."""
    dashboard = get_dashboard()
    best = dashboard.get_best_value_provider(language_pair=language_pair)
    if not best:
        return {"provider": None, "message": "No provider data available"}
    return best.to_dict()
