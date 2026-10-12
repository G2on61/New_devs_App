from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

from sqlalchemy import text

from app.core.database_pool import db_pool


async def _fetch_revenue(query: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs a revenue aggregation query and returns the summary payload.
    """
    await db_pool.initialize()

    if not db_pool.session_factory:
        raise Exception("Database pool not available")

    async with db_pool.get_session() as session:
        result = await session.execute(text(query), params)
        row = result.fetchone()

    # Amounts stay as Decimal (serialised as strings) so no precision is lost
    total_revenue = Decimal(str(row.total_revenue)) if row else Decimal('0')

    return {
        "property_id": params["property_id"],
        "tenant_id": params["tenant_id"],
        "total": str(total_revenue),
        "currency": "USD",
        "count": row.reservation_count if row else 0
    }


async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Dict[str, Any]:
    """
    Calculates revenue for a specific month.

    A reservation belongs to the month of its check-in in the property's own
    time zone, so the month boundaries are converted with the property timezone.
    """

    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)

    query = """
        SELECT
            COALESCE(SUM(r.total_amount), 0) as total_revenue,
            COUNT(*) as reservation_count
        FROM reservations r
        JOIN properties p ON p.id = r.property_id AND p.tenant_id = r.tenant_id
        WHERE r.property_id = :property_id
        AND r.tenant_id = :tenant_id
        AND r.check_in_date >= (CAST(:start_date AS timestamp) AT TIME ZONE p.timezone)
        AND r.check_in_date < (CAST(:end_date AS timestamp) AT TIME ZONE p.timezone)
    """

    return await _fetch_revenue(query, {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "start_date": start_date,
        "end_date": end_date
    })


async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    query = """
        SELECT
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COUNT(*) as reservation_count
        FROM reservations
        WHERE property_id = :property_id AND tenant_id = :tenant_id
    """

    return await _fetch_revenue(query, {
        "property_id": property_id,
        "tenant_id": tenant_id
    })


async def get_tenant_properties(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Lists the properties that belong to a tenant.
    """
    await db_pool.initialize()

    if not db_pool.session_factory:
        raise Exception("Database pool not available")

    query = text("""
        SELECT id, name, timezone
        FROM properties
        WHERE tenant_id = :tenant_id
        ORDER BY id
    """)

    async with db_pool.get_session() as session:
        result = await session.execute(query, {"tenant_id": tenant_id})
        rows = result.fetchall()

    return [{"id": row.id, "name": row.name, "timezone": row.timezone} for row in rows]
