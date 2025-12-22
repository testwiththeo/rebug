from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.analysis_result import AnalysisResult, AnalysisStatus
from app.models.bug_report import BugReport
from app.models.session import Session, SessionStatus
from app.schemas.integration import FileBugResponse, JiraTicketResponse, SlackNotifyResponse
from app.services.analysis_agent import AnalysisAgentService
from app.services.analysis_results import get_analysis_result, store_completed_analysis
from app.services.jira import JiraService
from app.services.session_ingest import get_session_or_none
from app.services.slack import SlackService


class BugFilingService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def file_bug(self, session_id: UUID) -> FileBugResponse:
        session = await get_session_or_none(self.db, session_id)
        if not session:
            raise ValueError("Session not found.")

        analysis = await self.ensure_completed_analysis(session_id)
        replay_url = f"{str(self.settings.viewer_base_url).rstrip('/')}/replay/{session_id}"
        existing = await self.get_bug_report(session_id)

        jira_result = existing_jira_response(existing)
        if not jira_result:
            created = await JiraService(self.db, self.settings).create_ticket(session, analysis, replay_url)
            jira_result = JiraTicketResponse(**created)

        report = await self.upsert_bug_report(
            session=session,
            analysis=analysis,
            replay_url=replay_url,
            jira=jira_result,
            slack=existing_slack_response(existing),
            status="submitted",
            error_message=None,
        )

        slack_result = existing_slack_response(report)
        slack_error: str | None = None
        if not slack_result:
            try:
                notified = await SlackService(self.db, self.settings).notify(
                    session,
                    analysis,
                    replay_url,
                    jira_ticket_key=jira_result.ticket_key,
                    jira_ticket_url=jira_result.ticket_url,
                )
                slack_result = SlackNotifyResponse(**notified)
            except Exception as error:
                slack_error = str(error)

        final_status = "submitted" if slack_error is None else "partial"
        report = await self.upsert_bug_report(
            session=session,
            analysis=analysis,
            replay_url=replay_url,
            jira=jira_result,
            slack=slack_result,
            status=final_status,
            error_message=slack_error,
        )

        return FileBugResponse(
            session_id=session_id,
            bug_report_id=report.id,
            status=report.status,
            replay_url=replay_url,
            jira=jira_result,
            slack=slack_result,
            error_message=report.error_message,
            filed_at=report.filed_at,
        )

    async def ensure_completed_analysis(self, session_id: UUID) -> AnalysisResult:
        analysis = await get_analysis_result(self.db, session_id)
        if analysis and analysis.status == AnalysisStatus.completed.value:
            return analysis

        payload = await AnalysisAgentService(self.db, self.settings).analyze_session(session_id)
        return await store_completed_analysis(self.db, session_id, payload, task_id=None)

    async def get_bug_report(self, session_id: UUID) -> BugReport | None:
        return await self.db.scalar(select(BugReport).where(BugReport.session_id == session_id))

    async def upsert_bug_report(
        self,
        *,
        session: Session,
        analysis: AnalysisResult,
        replay_url: str,
        jira: JiraTicketResponse | None,
        slack: SlackNotifyResponse | None,
        status: str,
        error_message: str | None,
    ) -> BugReport:
        report = await self.get_bug_report(session.id)
        if not report:
            report = BugReport(
                id=uuid4(),
                session_id=session.id,
                analysis_result_id=analysis.id,
                title=analysis.summary or f"Bug recorded on {session.url}",
                steps=[],
                root_cause={},
                duplicate_check={},
            )
            self.db.add(report)

        report.analysis_result_id = analysis.id
        report.title = analysis.summary or f"Bug recorded on {session.url}"
        report.severity = analysis.severity_suggestion
        report.steps = analysis.steps or []
        report.root_cause = analysis.root_cause or {}
        report.duplicate_check = analysis.duplicate_check or {}
        report.replay_url = replay_url
        report.status = status
        report.error_message = error_message
        report.filed_at = report.filed_at or datetime.now(UTC)

        if jira:
            report.jira_ticket_id = jira.ticket_id
            report.jira_ticket_key = jira.ticket_key
            report.jira_url = jira.ticket_url
        if slack:
            report.slack_channel = slack.channel
            report.slack_ts = slack.ts
            report.slack_message_url = slack.message_url

        session.status = SessionStatus.submitted.value
        await self.db.commit()
        await self.db.refresh(report)
        return report


def existing_jira_response(report: BugReport | None) -> JiraTicketResponse | None:
    if not report or not report.jira_ticket_key or not report.jira_url:
        return None
    return JiraTicketResponse(
        ticket_id=report.jira_ticket_id or report.jira_ticket_key,
        ticket_key=report.jira_ticket_key,
        ticket_url=report.jira_url,
    )


def existing_slack_response(report: BugReport | None) -> SlackNotifyResponse | None:
    if not report or not (report.slack_ts or report.slack_message_url):
        return None
    return SlackNotifyResponse(
        channel=report.slack_channel,
        ts=report.slack_ts,
        message_url=report.slack_message_url,
    )
