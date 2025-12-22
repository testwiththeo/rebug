from __future__ import annotations

import asyncio

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.impact_tracking import ImpactTrackingService


@celery_app.task(name="impact.scan_impact_links")
def scan_impact_links() -> dict[str, int]:
    return asyncio.run(scan_impact_links_async())


async def scan_impact_links_async() -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        incidents_scanned, links_created = await ImpactTrackingService(db).scan_open_incidents()
        return {
            "incidents_scanned": incidents_scanned,
            "links_created": links_created,
        }
