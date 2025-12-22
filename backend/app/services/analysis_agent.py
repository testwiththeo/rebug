from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.analysis_result import AnalysisResult
from app.models.session import Session
from app.models.session_event import SessionEvent


@dataclass(frozen=True)
class SessionContext:
    session: Session
    events: list[SessionEvent]
    bug_marker_timestamp_ms: int | None


class AnalysisAgentService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def analyze_session(self, session_id: UUID) -> dict[str, Any]:
        context = await self.load_session_context(session_id)
        existing_reports = await self.load_existing_reports(session_id)

        if self.settings.openai_api_key:
            try:
                return await self.run_langchain_agent(context, existing_reports)
            except Exception as error:
                fallback = self.run_heuristic_pipeline(context, existing_reports)
                fallback["analysis"]["summary"] = (
                    f"{fallback['analysis']['summary']} (LLM unavailable: {error})"
                )
                return fallback

        return self.run_heuristic_pipeline(context, existing_reports)

    async def analyze_session_events(self, session_id: UUID) -> dict[str, Any]:
        context = await self.load_session_context(session_id)
        return self.format_prompt_payload(context, await self.load_existing_reports(session_id))

    async def check_duplicate(self, session_id: UUID) -> dict[str, Any]:
        context = await self.load_session_context(session_id)
        return await self.compute_duplicate_check(context, await self.load_existing_reports(session_id))

    async def generate_steps(self, session_id: UUID) -> list[dict[str, Any]]:
        context = await self.load_session_context(session_id)
        return generate_steps_from_events(context)

    async def diagnose_root_cause(self, session_id: UUID) -> dict[str, Any]:
        context = await self.load_session_context(session_id)
        return diagnose_root_cause_from_events(context)

    async def load_session_context(self, session_id: UUID) -> SessionContext:
        session = await self.db.get(Session, session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        result = await self.db.execute(
            select(SessionEvent)
            .where(SessionEvent.session_id == session_id)
            .order_by(SessionEvent.sequence)
            .limit(self.settings.analysis_max_events)
        )
        events = list(result.scalars().all())
        bug_marker = next((event for event in events if event.event_type == "bug_marker"), None)
        bug_marker_timestamp_ms = (
            bug_marker.timestamp_ms
            if bug_marker
            else events[-1].timestamp_ms
            if events
            else None
        )

        return SessionContext(
            session=session,
            events=sample_events_for_prompt(events, self.settings.analysis_max_events),
            bug_marker_timestamp_ms=bug_marker_timestamp_ms,
        )

    async def load_existing_reports(self, session_id: UUID) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(AnalysisResult, Session)
            .join(Session, Session.id == AnalysisResult.session_id)
            .where(AnalysisResult.session_id != session_id)
            .where(AnalysisResult.status == "completed")
            .order_by(AnalysisResult.updated_at.desc())
            .limit(50)
        )

        reports: list[dict[str, Any]] = []
        for analysis, session in result.all():
            reports.append(
                {
                    "id": str(analysis.id),
                    "session_id": str(analysis.session_id),
                    "title": analysis.summary or f"Bug in {session.url}",
                    "summary": analysis.summary or "",
                    "url": session.url,
                    "steps": analysis.steps,
                    "root_cause": analysis.root_cause,
                }
            )
        return reports

    def format_prompt_payload(
        self,
        context: SessionContext,
        existing_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "session_id": str(context.session.id),
            "url": context.session.url,
            "browser": {
                "name": context.session.browser_name,
                "version": context.session.browser_version,
                "os": context.session.os,
                "viewport": {
                    "width": context.session.viewport_width,
                    "height": context.session.viewport_height,
                },
            },
            "bug_marker_timestamp_ms": context.bug_marker_timestamp_ms,
            "events": [
                {
                    "type": event.event_type,
                    "timestamp_ms": event.timestamp_ms,
                    "category": event.category,
                    "data": event.data,
                    "masked": event.masked,
                    "sequence": event.sequence,
                }
                for event in context.events
            ],
            "existing_bug_reports": existing_reports,
        }

    async def run_langchain_agent(
        self,
        context: SessionContext,
        existing_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        from langchain.agents import AgentExecutor, create_react_agent
        from langchain.prompts import PromptTemplate
        from langchain_core.tools import Tool
        from langchain_openai import ChatOpenAI

        prompt_payload = self.format_prompt_payload(context, existing_reports)
        system_prompt = load_system_prompt(self.settings)

        tools = [
            Tool.from_function(
                name="analyze_session_events",
                description="Read session events from the database and format prompt context.",
                func=lambda _: json.dumps(prompt_payload, default=str),
            ),
            Tool.from_function(
                name="check_duplicate",
                description="Check whether this session matches previous analyzed bug reports.",
                func=lambda _: json.dumps(
                    self.run_duplicate_check_sync(context, existing_reports), default=str
                ),
            ),
            Tool.from_function(
                name="generate_steps",
                description="Generate reproduction steps from user interaction and timeline events.",
                func=lambda _: json.dumps(generate_steps_from_events(context), default=str),
            ),
            Tool.from_function(
                name="diagnose_root_cause",
                description="Find the first anomaly and root-cause evidence chain.",
                func=lambda _: json.dumps(diagnose_root_cause_from_events(context), default=str),
            ),
        ]

        react_prompt = PromptTemplate.from_template(
            "{system_prompt}\n\n"
            "You have access to these tools:\n{tools}\n\n"
            "Use this ReAct format:\n"
            "Question: the input question\n"
            "Thought: reason about what to do\n"
            "Action: one of [{tool_names}]\n"
            "Action Input: the input to the action\n"
            "Observation: the result of the action\n"
            "... repeat as needed\n"
            "Thought: I have enough evidence\n"
            "Final Answer: strict JSON only matching the required output schema\n\n"
            "Question: Analyze this Rebug session and return strict JSON.\n"
            "Session payload:\n{input}\n\n"
            "{agent_scratchpad}"
        )

        llm = ChatOpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            temperature=0,
        )
        agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True)
        response = await executor.ainvoke(
            {
                "system_prompt": system_prompt,
                "input": json.dumps(prompt_payload, default=str),
            }
        )

        output = response.get("output", "")
        parsed = parse_json_object(output)
        return normalize_analysis_result(parsed, context, await self.compute_duplicate_check(context, existing_reports))

    def run_heuristic_pipeline(
        self,
        context: SessionContext,
        existing_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        root_cause = diagnose_root_cause_from_events(context)
        steps = generate_steps_from_events(context)
        duplicate_check = self.run_duplicate_check_sync(context, existing_reports)
        confidence = float(root_cause.get("confidence") or 0.35)

        return {
            "analysis": {
                "session_id": str(context.session.id),
                "summary": build_summary(context, root_cause),
                "severity_suggestion": suggest_severity(root_cause),
            },
            "reproduction_steps": steps,
            "root_cause": root_cause,
            "duplicate_check": duplicate_check,
            "coverage_note": None,
            "data_sensitivity_warning": detect_sensitivity_warning(context.events),
            "_confidence": confidence,
        }

    async def compute_duplicate_check(
        self,
        context: SessionContext,
        existing_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if self.settings.openai_api_key and existing_reports:
            try:
                return await self.compute_embedding_duplicate_check(context, existing_reports)
            except Exception:
                pass
        return self.run_duplicate_check_sync(context, existing_reports)

    async def compute_embedding_duplicate_check(
        self,
        context: SessionContext,
        existing_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(api_key=self.settings.openai_api_key)
        query_text = duplicate_text_for_context(context)
        candidate_texts = [duplicate_text_for_report(report) for report in existing_reports]
        vectors = await embeddings.aembed_documents([query_text, *candidate_texts])
        query_vector = vectors[0]
        matches = []

        for report, vector in zip(existing_reports, vectors[1:], strict=False):
            similarity = cosine_similarity(query_vector, vector)
            if similarity >= self.settings.duplicate_threshold:
                matches.append(
                    {
                        "id": report["id"],
                        "session_id": report["session_id"],
                        "title": report["title"],
                        "similarity": round(similarity, 2),
                    }
                )

        return {
            "is_duplicate": bool(matches),
            "matches": sorted(matches, key=lambda item: item["similarity"], reverse=True)[:5],
            "note": "Vector similarity search against completed Rebug analyses",
        }

    def run_duplicate_check_sync(
        self,
        context: SessionContext,
        existing_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        query_terms = tokenize(duplicate_text_for_context(context))
        matches = []
        for report in existing_reports:
            similarity = jaccard_similarity(query_terms, tokenize(duplicate_text_for_report(report)))
            if similarity >= self.settings.duplicate_threshold:
                matches.append(
                    {
                        "id": report["id"],
                        "session_id": report["session_id"],
                        "title": report["title"],
                        "similarity": round(similarity, 2),
                    }
                )

        return {
            "is_duplicate": bool(matches),
            "matches": sorted(matches, key=lambda item: item["similarity"], reverse=True)[:5],
            "note": (
                "Lexical duplicate fallback used; configure OPENAI_API_KEY for embedding search"
                if existing_reports
                else "No prior analyzed reports available"
            ),
        }


def sample_events_for_prompt(events: list[SessionEvent], max_events: int) -> list[SessionEvent]:
    if len(events) <= max_events:
        return events

    sampled: list[SessionEvent] = []
    for index, event in enumerate(events):
        if event.event_type != "dom_mutation" or index % 3 == 0:
            sampled.append(event)
        if len(sampled) >= max_events:
            break
    return sampled


def generate_steps_from_events(context: SessionContext) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    order = 1

    for event in context.events:
        if event.event_type != "user_interaction":
            continue

        action = str(event.data.get("action") or event.category or "")
        if action == "navigation":
            steps.append(
                {
                    "order": order,
                    "action": "Navigate to",
                    "value": str(event.data.get("value") or context.session.url),
                    "expected": "Page loads successfully",
                    "actual": "Page navigation was recorded",
                }
            )
        elif action == "click":
            label = event.data.get("label") or event.data.get("target_selector") or "recorded target"
            steps.append(
                {
                    "order": order,
                    "action": "Click",
                    "value": str(label),
                    "expected": "Clicked control performs the intended action",
                    "actual": "Click was recorded in the session timeline",
                }
            )
        elif action == "input":
            value = event.data.get("value")
            steps.append(
                {
                    "order": order,
                    "action": "Type",
                    "value": f"{event.data.get('target_selector', 'input')} = {value}",
                    "expected": "Input value is accepted",
                    "actual": "Input event was recorded",
                }
            )
        elif action == "scroll":
            steps.append(
                {
                    "order": order,
                    "action": "Scroll to",
                    "value": json.dumps(event.data.get("scroll_position") or {}),
                    "expected": "Target content remains usable",
                    "actual": "Scroll event was recorded",
                }
            )
        else:
            continue

        order += 1
        if order > 12:
            break

    anomaly = find_first_anomaly(context.events)
    if anomaly:
        steps.append(
            {
                "order": order,
                "action": "Assert",
                "value": describe_event(anomaly),
                "expected": "The flow completes without errors",
                "actual": describe_event(anomaly),
            }
        )

    return steps or [
        {
            "order": 1,
            "action": "Navigate to",
            "value": context.session.url,
            "expected": "Session contains enough interaction events to reproduce the issue",
            "actual": "No user interaction events were captured",
        }
    ]


def diagnose_root_cause_from_events(context: SessionContext) -> dict[str, Any]:
    if not context.events:
        return {
            "confidence": 0.2,
            "category": "unknown",
            "summary": "Session contains no events to diagnose.",
            "evidence_chain": [],
            "primary_cause_event": None,
        }

    anomaly = find_first_anomaly(context.events)
    if not anomaly:
        return {
            "confidence": 0.35,
            "category": "unknown",
            "summary": "No network failure or console error was captured before the marker.",
            "evidence_chain": [event_to_evidence(event) for event in context.events[-3:]],
            "primary_cause_event": event_to_evidence(context.events[-1]),
        }

    category = categorize_anomaly(anomaly)
    nearby = [
        event
        for event in context.events
        if anomaly.timestamp_ms <= event.timestamp_ms <= anomaly.timestamp_ms + 1_500
        and event.event_type in {"network_request", "console_log", "dom_mutation", "bug_marker"}
    ][:5]

    return {
        "confidence": 0.82 if anomaly.event_type == "network_request" else 0.68,
        "category": category,
        "summary": summarize_anomaly(anomaly),
        "evidence_chain": [event_to_evidence(event) for event in nearby] or [event_to_evidence(anomaly)],
        "primary_cause_event": event_to_evidence(anomaly),
    }


def find_first_anomaly(events: list[SessionEvent]) -> SessionEvent | None:
    for event in events:
        if event.event_type == "network_request":
            status = as_int(event.data.get("status"))
            if status and status >= 400:
                return event
            if event.data.get("is_error") is True:
                return event
        if event.event_type == "console_log":
            level = str(event.data.get("level") or "").lower()
            if level == "error" or "error" in str(event.category or "").lower():
                return event
    return None


def categorize_anomaly(event: SessionEvent) -> str:
    if event.event_type == "network_request":
        status = as_int(event.data.get("status"))
        if status in {401, 403}:
            return "authentication" if status == 401 else "permission"
        if status and status >= 500:
            return "network_error"
        if status and status >= 400:
            return "data_validation"
        return "network_error"
    if event.event_type == "console_log":
        message = str(event.data.get("message") or "").lower()
        if "null" in message or "undefined" in message:
            return "dom_not_found"
        return "javascript_error"
    return "unknown"


def summarize_anomaly(event: SessionEvent) -> str:
    if event.event_type == "network_request":
        method = event.data.get("method", "GET")
        url = event.data.get("url", "unknown URL")
        status = event.data.get("status", "error")
        return f"{method} {url} returned {status}."
    if event.event_type == "console_log":
        return str(event.data.get("message") or "Console error captured.")
    return describe_event(event)


def event_to_evidence(event: SessionEvent) -> dict[str, Any]:
    return {
        "timestamp_ms": event.timestamp_ms,
        "event_type": event.event_type,
        "detail": describe_event(event),
    }


def describe_event(event: SessionEvent) -> str:
    if event.event_type == "network_request":
        method = event.data.get("method", "GET")
        url = event.data.get("url", "")
        status = event.data.get("status", "error")
        return f"{method} {url} {status}"
    if event.event_type == "console_log":
        return f"{event.data.get('level', 'log')}: {event.data.get('message', '')}"
    if event.event_type == "user_interaction":
        return f"{event.data.get('action', event.category)} {event.data.get('target_selector', '')}".strip()
    if event.event_type == "dom_mutation":
        return f"{event.data.get('type', 'mutation')} at {event.data.get('target_selector', 'unknown')}"
    return f"{event.event_type} {event.category or ''}".strip()


def normalize_analysis_result(
    parsed: dict[str, Any],
    context: SessionContext,
    duplicate_fallback: dict[str, Any],
) -> dict[str, Any]:
    if "error" in parsed:
        return {
            "analysis": {
                "session_id": str(context.session.id),
                "summary": str(parsed["error"]),
                "severity_suggestion": "minor",
            },
            "reproduction_steps": [],
            "root_cause": diagnose_root_cause_from_events(context),
            "duplicate_check": duplicate_fallback,
            "coverage_note": None,
            "data_sensitivity_warning": None,
            "_confidence": 0.2,
        }

    parsed.setdefault("analysis", {})
    parsed["analysis"].setdefault("session_id", str(context.session.id))
    parsed.setdefault("reproduction_steps", generate_steps_from_events(context))
    parsed.setdefault("root_cause", diagnose_root_cause_from_events(context))
    parsed.setdefault("duplicate_check", duplicate_fallback)
    parsed.setdefault("coverage_note", None)
    parsed.setdefault("data_sensitivity_warning", detect_sensitivity_warning(context.events))
    parsed["_confidence"] = float(parsed.get("root_cause", {}).get("confidence") or 0.5)
    return parsed


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def load_system_prompt(settings: Settings) -> str:
    configured_path = Path(settings.analysis_system_prompt_path)
    candidates = [
        configured_path,
        Path.cwd() / configured_path,
        Path(__file__).resolve().parents[1] / "prompts" / "system-prompt-gpt.md",
        Path(__file__).resolve().parents[3] / "prompts" / "system-prompt-gpt.md",
        Path("/app/prompts/system-prompt-gpt.md"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError("Unable to find analysis system prompt.")


def build_summary(context: SessionContext, root_cause: dict[str, Any]) -> str:
    summary = root_cause.get("summary")
    if summary:
        return str(summary)
    return f"Bug recorded on {context.session.url}"


def suggest_severity(root_cause: dict[str, Any]) -> str:
    category = root_cause.get("category")
    if category in {"authentication", "permission", "network_error"}:
        return "major"
    if category == "unknown":
        return "minor"
    return "major"


def detect_sensitivity_warning(events: list[SessionEvent]) -> str | None:
    if any(event.masked for event in events):
        return "Some captured values were masked before analysis."
    return None


def duplicate_text_for_context(context: SessionContext) -> str:
    pieces = [context.session.url]
    for event in context.events:
        if event.event_type in {"network_request", "console_log", "user_interaction"}:
            pieces.append(describe_event(event))
    return " ".join(pieces)


def duplicate_text_for_report(report: dict[str, Any]) -> str:
    return " ".join(
        [
            str(report.get("title", "")),
            str(report.get("summary", "")),
            str(report.get("url", "")),
            json.dumps(report.get("steps", []), default=str),
            json.dumps(report.get("root_cause", {}), default=str),
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


def as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
