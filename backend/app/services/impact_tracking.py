from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.models.bug_report import BugReport
from app.models.impact_link import ImpactLink
from app.models.production_incident import ProductionIncident
from app.models.session import Session
from app.schemas.impact import ImpactLinkResponse, ProductionIncidentCreate, ProductionIncidentResponse
from app.services.integrations import IntegrationError
from app.services.slack import SlackService

IGNORED_FINAL_STATUSES = {"unable_to_repro", "wontfix"}
IMPACT_MATCH_THRESHOLD = 0.68


@dataclass(frozen=True)
class MatchCandidate:
    bug_report: BugReport
    session: Session
    score: float
    reason: str
    evidence: dict[str, Any]


class ImpactTrackingService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def ingest_incident(self, payload: ProductionIncidentCreate) -> tuple[ProductionIncident, list[ImpactLink]]:
        incident = ProductionIncident(
            id=uuid4(),
            title=payload.title,
            incident_url=payload.incident_url,
            affected_url=payload.affected_url,
            error_message=payload.error_message,
            source=payload.source,
            payload=payload.payload,
            occurred_at=payload.occurred_at,
        )
        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)

        links = await self.match_incident(incident)
        await self.notify_pending_links(links)
        return incident, links

    async def scan_open_incidents(self) -> tuple[int, int]:
        result = await self.db.execute(
            select(ProductionIncident).order_by(ProductionIncident.created_at.desc()).limit(200)
        )
        incidents = list(result.scalars().all())
        created = 0
        for incident in incidents:
            links = await self.match_incident(incident)
            created += len(links)
            await self.notify_pending_links(links)
        return len(incidents), created

    async def match_incident(self, incident: ProductionIncident) -> list[ImpactLink]:
        candidates = await self.load_ignored_bug_reports()
        if not candidates:
            return []

        scored = await self.score_candidates(incident, candidates)
        links: list[ImpactLink] = []
        for candidate in scored:
            if candidate.score < IMPACT_MATCH_THRESHOLD:
                continue

            existing = await self.db.scalar(
                select(ImpactLink)
                .where(ImpactLink.bug_report_id == candidate.bug_report.id)
                .where(ImpactLink.incident_url == incident.incident_url)
            )
            if existing:
                continue

            link = ImpactLink(
                id=uuid4(),
                bug_report_id=candidate.bug_report.id,
                incident_id=incident.id,
                incident_title=incident.title,
                incident_url=incident.incident_url,
                detected_at=datetime.now(UTC),
                match_score=Decimal(str(round(candidate.score, 3))),
                match_reason=candidate.reason,
                evidence=candidate.evidence,
            )
            self.db.add(link)
            links.append(link)

        if links:
            await self.db.commit()
            for link in links:
                await self.db.refresh(link)
        return links

    async def handle_jira_webhook(self, payload: dict[str, Any]) -> tuple[BugReport | None, int]:
        issue = payload.get("issue") or {}
        fields = issue.get("fields") or {}
        status = fields.get("status") or {}
        issue_key = issue.get("key") or payload.get("issue_key")
        status_name = status.get("name") if isinstance(status, dict) else payload.get("status")
        final_status = normalize_jira_status(status_name)

        if not issue_key:
            return None, 0

        report = await self.db.scalar(
            select(BugReport)
            .options(selectinload(BugReport.session))
            .where(BugReport.jira_ticket_key == str(issue_key))
        )
        if not report:
            return None, 0

        report.jira_status = str(status_name) if status_name else None
        if final_status:
            report.final_status = final_status
            report.status = final_status
            report.resolved_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(report)

        matched = 0
        if final_status in IGNORED_FINAL_STATUSES:
            scanned, created = await self.scan_open_incidents()
            matched = created if scanned else 0
        return report, matched

    async def list_links(self, limit: int = 100) -> list[ImpactLinkResponse]:
        result = await self.db.execute(
            select(ImpactLink, BugReport, Session)
            .join(BugReport, BugReport.id == ImpactLink.bug_report_id)
            .join(Session, Session.id == BugReport.session_id)
            .order_by(ImpactLink.detected_at.desc())
            .limit(limit)
        )
        return [to_impact_link_response(link, report, session) for link, report, session in result.all()]

    async def load_ignored_bug_reports(self) -> list[tuple[BugReport, Session]]:
        result = await self.db.execute(
            select(BugReport, Session)
            .join(Session, Session.id == BugReport.session_id)
            .where(
                BugReport.final_status.in_(IGNORED_FINAL_STATUSES)
                | BugReport.status.in_(IGNORED_FINAL_STATUSES)
            )
            .order_by(BugReport.updated_at.desc())
            .limit(200)
        )
        return list(result.all())

    async def score_candidates(
        self,
        incident: ProductionIncident,
        candidates: list[tuple[BugReport, Session]],
    ) -> list[MatchCandidate]:
        lexical = [
            self.score_candidate_lexically(incident, bug_report, session)
            for bug_report, session in candidates
        ]

        if self.settings.openai_api_key and incident.error_message:
            try:
                return await self.add_embedding_scores(incident, lexical)
            except Exception:
                return lexical
        return lexical

    def score_candidate_lexically(
        self,
        incident: ProductionIncident,
        bug_report: BugReport,
        session: Session,
    ) -> MatchCandidate:
        incident_pattern = normalize_url_pattern(incident.affected_url or incident.incident_url)
        session_pattern = normalize_url_pattern(session.url)
        url_score = url_pattern_score(incident_pattern, session_pattern)

        incident_text = incident_match_text(incident)
        bug_text = bug_match_text(bug_report)
        text_score = jaccard_similarity(tokenize(incident_text), tokenize(bug_text))
        score = (url_score * 0.52) + (text_score * 0.48)
        reason = f"URL pattern score {url_score:.2f}; error similarity {text_score:.2f}"
        evidence = {
            "incident_url_pattern": incident_pattern,
            "bug_url_pattern": session_pattern,
            "incident_error": incident.error_message,
            "bug_root_cause": (bug_report.root_cause or {}).get("summary"),
        }
        return MatchCandidate(bug_report, session, score, reason, evidence)

    async def add_embedding_scores(
        self,
        incident: ProductionIncident,
        candidates: list[MatchCandidate],
    ) -> list[MatchCandidate]:
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(api_key=self.settings.openai_api_key)
        documents = [incident_match_text(incident), *[bug_match_text(candidate.bug_report) for candidate in candidates]]
        vectors = await embeddings.aembed_documents(documents)
        incident_vector = vectors[0]
        scored: list[MatchCandidate] = []
        for candidate, vector in zip(candidates, vectors[1:], strict=False):
            embedding_score = cosine_similarity(incident_vector, vector)
            combined = (candidate.score * 0.55) + (embedding_score * 0.45)
            scored.append(
                MatchCandidate(
                    candidate.bug_report,
                    candidate.session,
                    combined,
                    f"{candidate.reason}; embedding similarity {embedding_score:.2f}",
                    {**candidate.evidence, "embedding_similarity": round(embedding_score, 3)},
                )
            )
        return scored

    async def notify_pending_links(self, links: list[ImpactLink]) -> None:
        for link in links:
            report = await self.db.get(BugReport, link.bug_report_id)
            if not report:
                continue
            session = await self.db.get(Session, report.session_id)
            if not session:
                continue
            try:
                await SlackService(self.db, self.settings).notify_impact_link(report, session, link)
                link.notification_status = "sent"
                link.notification_error = None
            except IntegrationError as error:
                link.notification_status = "failed"
                link.notification_error = str(error)
            except Exception as error:
                link.notification_status = "failed"
                link.notification_error = str(error)
        if links:
            await self.db.commit()


def to_incident_response(incident: ProductionIncident) -> ProductionIncidentResponse:
    return ProductionIncidentResponse(
        id=incident.id,
        title=incident.title,
        incident_url=incident.incident_url,
        affected_url=incident.affected_url,
        error_message=incident.error_message,
        source=incident.source,
        occurred_at=incident.occurred_at,
        created_at=incident.created_at,
    )


def to_impact_link_response(
    link: ImpactLink,
    report: BugReport,
    session: Session,
) -> ImpactLinkResponse:
    return ImpactLinkResponse(
        id=link.id,
        bug_report_id=report.id,
        session_id=session.id,
        bug_title=report.title,
        bug_status=report.final_status or report.status,
        jira_ticket_key=report.jira_ticket_key,
        jira_url=report.jira_url,
        replay_url=report.replay_url,
        original_url=session.url,
        incident_title=link.incident_title,
        incident_url=link.incident_url,
        detected_at=link.detected_at,
        match_score=float(link.match_score) if link.match_score is not None else None,
        match_reason=link.match_reason,
        notification_status=link.notification_status,
        notification_error=link.notification_error,
        evidence=link.evidence or {},
    )


def normalize_jira_status(status: str | None) -> str | None:
    value = (status or "").strip().lower().replace("'", "")
    compact = value.replace(" ", "_").replace("-", "_")
    if "unable" in value and "repro" in value:
        return "unable_to_repro"
    if "cant" in value and "repro" in value:
        return "unable_to_repro"
    if "cannot" in value and "repro" in value:
        return "unable_to_repro"
    if compact in {"wont_fix", "wontfix", "will_not_fix"}:
        return "wontfix"
    if compact in {"done", "fixed", "resolved"}:
        return "fixed"
    return None


def normalize_url_pattern(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    segments = [
        ":id" if is_dynamic_segment(segment) else segment.lower()
        for segment in parsed.path.strip("/").split("/")
        if segment
    ]
    return f"{host}/{'/'.join(segments)}"


def url_pattern_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0

    left_host, _, left_path = left.partition("/")
    right_host, _, right_path = right.partition("/")
    if left_host != right_host:
        return 0.0

    left_segments = set(left_path.split("/")) if left_path else set()
    right_segments = set(right_path.split("/")) if right_path else set()
    if not left_segments and not right_segments:
        return 0.75
    return 0.45 + (0.55 * jaccard_similarity(left_segments, right_segments))


def is_dynamic_segment(segment: str) -> bool:
    clean = segment.strip().lower()
    if clean.isdigit():
        return True
    if len(clean) >= 16 and clean.count("-") >= 2:
        return True
    return False


def incident_match_text(incident: ProductionIncident) -> str:
    return " ".join(
        [
            incident.title,
            incident.error_message or "",
            incident.affected_url or "",
            incident.incident_url,
        ]
    )


def bug_match_text(report: BugReport) -> str:
    root_cause = report.root_cause or {}
    return " ".join(
        [
            report.title,
            str(root_cause.get("summary") or ""),
            str(root_cause.get("category") or ""),
            " ".join(str(step.get("actual") or step.get("value") or "") for step in report.steps or []),
        ]
    )


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in "".join(character.lower() if character.isalnum() else " " for character in text).split()
        if len(token) > 2
    }


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)
