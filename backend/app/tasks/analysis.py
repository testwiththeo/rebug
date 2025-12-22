from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.analysis_agent import AnalysisAgentService
from app.services.analysis_results import (
    mark_analysis_running,
    store_completed_analysis,
    store_failed_analysis,
)


@celery_app.task(
    name="analysis.run_session_analysis",
    bind=True,
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=300,
    autoretry_for=(Exception,),
)
def run_session_analysis(self, session_id: str) -> dict[str, str]:
    return asyncio.run(run_session_analysis_async(UUID(session_id), self.request.id))


async def run_session_analysis_async(
    session_id: UUID, task_id: str | None
) -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        await mark_analysis_running(db, session_id, task_id)
        service = AnalysisAgentService(db)

        try:
            payload = await service.analyze_session(session_id)
            await store_completed_analysis(db, session_id, payload, task_id)
            return {"session_id": str(session_id), "status": "completed"}
        except Exception as error:
            await store_failed_analysis(db, session_id, str(error), task_id)
            raise
