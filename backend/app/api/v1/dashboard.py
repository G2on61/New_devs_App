from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from app.services.cache import get_revenue_summary
from app.services.reservations import get_tenant_properties
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:

    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"

    try:
        return await get_tenant_properties(tenant_id)
    except Exception as e:
        print(f"Property lookup failed (tenant: {tenant_id}): {e}")
        raise HTTPException(status_code=503, detail="Property data is temporarily unavailable")

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:

    if (month is None) != (year is None):
        raise HTTPException(status_code=400, detail="month and year must be provided together")

    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"

    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id, month, year)
    except Exception as e:
        print(f"Revenue lookup failed for {property_id} (tenant: {tenant_id}): {e}")
        raise HTTPException(status_code=503, detail="Revenue data is temporarily unavailable")

    # Round once, on the exact Decimal total, to whole cents
    total_revenue = Decimal(revenue_data['total']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": float(total_revenue),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
