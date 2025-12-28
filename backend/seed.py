"""Seed script for Rebug test data.

Run inside the API container:
    docker exec rebug-api-1 python seed.py
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://rebug:rebug@postgres:5432/rebug"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def uid():
    return uuid4()


def utcnow():
    return datetime.now(timezone.utc)


async def seed():
    async with async_session() as db:
        # Clear existing data
        await db.execute(text("DELETE FROM impact_links"))
        await db.execute(text("DELETE FROM production_incidents"))
        await db.execute(text("DELETE FROM bug_reports"))
        await db.execute(text("DELETE FROM analysis_results"))
        await db.execute(text("DELETE FROM session_events"))
        await db.execute(text("DELETE FROM sessions"))

        sessions = []

        # ── Session 1: Login page console error (analyzed) ──
        s1_id = uid()
        s1_started = utcnow() - timedelta(hours=2)
        s1_ended = s1_started + timedelta(seconds=47)
        await db.execute(
            text("""
                INSERT INTO sessions (id, url, browser_name, browser_version, os,
                    viewport_width, viewport_height, started_at, ended_at, duration_sec,
                    event_count, size_bytes, status, checksum, created_at, updated_at)
                VALUES (:id, :url, :bv, :bver, :os, :vw, :vh, :sa, :ea, :dur, :ec, :sb, :st, :ck, now(), now())
            """),
            {
                "id": s1_id,
                "url": "https://app.example.com/login",
                "bv": "Chrome",
                "bver": "124.0.6367.91",
                "os": "macOS 14.4",
                "vw": 1440,
                "vh": 900,
                "sa": s1_started,
                "ea": s1_ended,
                "dur": 47,
                "ec": 34,
                "sb": 48200,
                "st": "analyzed",
                "ck": "a1b2c3d4e5f6",
            },
        )
        sessions.append(s1_id)

        # Events for session 1
        events_s1 = [
            (1, 0, "user_interaction", "navigation", {"action": "navigation", "url": "https://app.example.com/login"}),
            (2, 200, "dom_mutation", "rrweb", {"type": "childList", "target_selector": "body"}),
            (3, 350, "user_interaction", "input", {"action": "input", "target_selector": "#email", "value": "qa@example.com"}),
            (4, 800, "user_interaction", "input", {"action": "input", "target_selector": "#password", "value": "********"}),
            (5, 1200, "console_log", "console", {"level": "log", "message": "Login form submitted"}),
            (6, 1400, "network_request", "api", {"method": "POST", "url": "https://api.example.com/auth/login", "status": 401, "duration_ms": 340, "is_error": True}),
            (7, 1450, "console_log", "console", {"level": "error", "message": "Authentication failed: Invalid credentials"}),
            (8, 1600, "network_request", "api", {"method": "POST", "url": "https://api.example.com/auth/login", "status": 401, "duration_ms": 290, "is_error": True}),
            (9, 1650, "console_log", "console", {"level": "error", "message": "Authentication failed: Invalid credentials"}),
            (10, 2000, "user_interaction", "input", {"action": "input", "target_selector": "#email", "value": "admin@example.com"}),
            (11, 2400, "user_interaction", "input", {"action": "input", "target_selector": "#password", "value": "********"}),
            (12, 2800, "network_request", "api", {"method": "POST", "url": "https://api.example.com/auth/login", "status": 200, "duration_ms": 520, "is_error": False}),
            (13, 2900, "console_log", "console", {"level": "log", "message": "Login successful, redirecting to dashboard"}),
            (14, 3200, "user_interaction", "navigation", {"action": "navigation", "url": "https://app.example.com/dashboard"}),
            (15, 3500, "dom_mutation", "rrweb", {"type": "childList", "target_selector": "#root"}),
            (16, 4000, "network_request", "api", {"method": "GET", "url": "https://api.example.com/user/profile", "status": 200, "duration_ms": 180, "is_error": False}),
            (17, 4200, "network_request", "api", {"method": "GET", "url": "https://api.example.com/dashboard/stats", "status": 500, "duration_ms": 1200, "is_error": True}),
            (18, 4250, "console_log", "console", {"level": "error", "message": "GET /dashboard/stats 500 (Internal Server Error)"}),
            (19, 4300, "console_log", "console", {"level": "warn", "message": "Dashboard stats failed to load, using defaults"}),
            (20, 5000, "user_interaction", "click", {"action": "click", "target_selector": ".refresh-btn"}),
            (21, 5500, "network_request", "api", {"method": "GET", "url": "https://api.example.com/dashboard/stats", "status": 500, "duration_ms": 1100, "is_error": True}),
            (22, 5550, "console_log", "console", {"level": "error", "message": "GET /dashboard/stats 500 (Internal Server Error)"}),
            (23, 6000, "user_interaction", "click", {"action": "click", "target_selector": ".refresh-btn"}),
            (24, 6500, "network_request", "api", {"method": "GET", "url": "https://api.example.com/dashboard/stats", "status": 500, "duration_ms": 1050, "is_error": True}),
            (25, 7000, "user_interaction", "click", {"action": "click", "target_selector": "#bug-marker-btn"}),
            (26, 7100, "bug_marker", "bug", {"note": "Dashboard stats endpoint consistently returns 500 after login"}),
        ]
        for seq, ts_ms, etype, cat, data in events_s1:
            await db.execute(
                text("""
                    INSERT INTO session_events (session_id, sequence, timestamp_ms, event_type, category, data, masked)
                    VALUES (:sid, :seq, :ts, :et, :cat, :data, false)
                """),
                {"sid": s1_id, "seq": seq, "ts": ts_ms, "et": etype, "cat": cat, "data": json.dumps(data)},
            )

        # Analysis for session 1
        a1_id = uid()
        await db.execute(
            text("""
                INSERT INTO analysis_results (id, session_id, status, confidence, summary,
                    severity_suggestion, steps, root_cause, duplicate_check,
                    completed_at, created_at, updated_at)
                VALUES (:id, :sid, 'completed', 0.87, :summary, :sev,
                    :steps, :rc, :dc, :ca, now(), now())
            """),
            {
                "id": a1_id,
                "sid": s1_id,
                "summary": "Dashboard stats API returns 500 after successful login",
                "sev": "major",
                "steps": json.dumps([
                    {"order": 1, "action": "Navigate to", "value": "https://app.example.com/login", "actual": "Login page loaded"},
                    {"order": 2, "action": "Enter email", "value": "admin@example.com", "actual": "Input accepted"},
                    {"order": 3, "action": "Enter password", "value": "********", "actual": "Input accepted"},
                    {"order": 4, "action": "Click login", "value": "Submit button", "actual": "Redirected to dashboard"},
                    {"order": 5, "action": "Observe dashboard", "value": "Stats section", "actual": "Stats fail to load with 500 error"},
                ]),
                "rc": json.dumps({
                    "summary": "GET /dashboard/stats endpoint crashes with 500. Server logs show NullPointerException in StatsController when user has no organization membership.",
                    "category": "server-side",
                    "evidence_chain": [
                        {"event_type": "network_request", "timestamp_ms": 4200, "detail": "GET /dashboard/stats returned 500 after 1200ms"},
                        {"event_type": "console_log", "timestamp_ms": 4250, "detail": "Console logged 500 error"},
                        {"event_type": "network_request", "timestamp_ms": 5500, "detail": "Retry also returned 500"},
                        {"event_type": "network_request", "timestamp_ms": 6500, "detail": "Second retry also returned 500"},
                    ],
                }),
                "dc": json.dumps({"is_duplicate": False, "matches": [], "note": "No similar sessions found"}),
                "ca": utcnow(),
            },
        )

        # ── Session 2: Shopping cart race condition (analyzed, filed) ──
        s2_id = uid()
        s2_started = utcnow() - timedelta(hours=5)
        s2_ended = s2_started + timedelta(seconds=62)
        await db.execute(
            text("""
                INSERT INTO sessions (id, url, browser_name, browser_version, os,
                    viewport_width, viewport_height, started_at, ended_at, duration_sec,
                    event_count, size_bytes, status, checksum, created_at, updated_at)
                VALUES (:id, :url, :bv, :bver, :os, :vw, :vh, :sa, :ea, :dur, :ec, :sb, :st, :ck, now(), now())
            """),
            {
                "id": s2_id,
                "url": "https://shop.example.com/cart",
                "bv": "Chrome",
                "bver": "125.0.6422.60",
                "os": "Windows 11",
                "vw": 1920,
                "vh": 1080,
                "sa": s2_started,
                "ea": s2_ended,
                "dur": 62,
                "ec": 41,
                "sb": 52800,
                "st": "analyzed",
                "ck": "f6e5d4c3b2a1",
            },
        )
        sessions.append(s2_id)

        events_s2 = [
            (1, 0, "user_interaction", "navigation", {"action": "navigation", "url": "https://shop.example.com/products/widget-pro"}),
            (2, 500, "dom_mutation", "rrweb", {"type": "childList", "target_selector": ".product-page"}),
            (3, 1000, "user_interaction", "click", {"action": "click", "target_selector": ".add-to-cart-btn"}),
            (4, 1200, "network_request", "api", {"method": "POST", "url": "https://api.shop.example.com/cart/add", "status": 200, "duration_ms": 150, "is_error": False}),
            (5, 1300, "console_log", "console", {"level": "log", "message": "Item added to cart"}),
            (6, 1500, "user_interaction", "navigation", {"action": "navigation", "url": "https://shop.example.com/cart"}),
            (7, 2000, "network_request", "api", {"method": "GET", "url": "https://api.shop.example.com/cart", "status": 200, "duration_ms": 220, "is_error": False}),
            (8, 2200, "dom_mutation", "rrweb", {"type": "childList", "target_selector": ".cart-items"}),
            (9, 3000, "user_interaction", "click", {"action": "click", "target_selector": ".quantity-increase"}),
            (10, 3200, "network_request", "api", {"method": "PATCH", "url": "https://api.shop.example.com/cart/item", "status": 200, "duration_ms": 100, "is_error": False}),
            (11, 3500, "user_interaction", "click", {"action": "click", "target_selector": ".quantity-increase"}),
            (12, 3700, "network_request", "api", {"method": "PATCH", "url": "https://api.shop.example.com/cart/item", "status": 200, "duration_ms": 95, "is_error": False}),
            (13, 4000, "user_interaction", "click", {"action": "click", "target_selector": ".checkout-btn"}),
            (14, 4500, "network_request", "api", {"method": "POST", "url": "https://api.shop.example.com/checkout", "status": 200, "duration_ms": 2100, "is_error": False}),
            (15, 4600, "console_log", "console", {"level": "log", "message": "Checkout initiated"}),
            (16, 5000, "user_interaction", "click", {"action": "click", "target_selector": "#confirm-payment"}),
            (17, 5500, "network_request", "api", {"method": "POST", "url": "https://api.shop.example.com/payment/process", "status": 200, "duration_ms": 3200, "is_error": False}),
            (18, 5600, "console_log", "console", {"level": "log", "message": "Payment processed"}),
            (19, 6000, "network_request", "api", {"method": "POST", "url": "https://api.shop.example.com/orders", "status": 200, "duration_ms": 800, "is_error": False}),
            (20, 6200, "console_log", "console", {"level": "error", "message": "Order confirmation page failed to render: Cannot read properties of undefined (reading 'items')"}),
            (21, 6300, "dom_mutation", "rrweb", {"type": "childList", "target_selector": "#root"}),
            (22, 7000, "user_interaction", "click", {"action": "click", "target_selector": "#bug-marker-btn"}),
            (23, 7100, "bug_marker", "bug", {"note": "Order succeeds but confirmation page crashes - cart data lost before render"}),
        ]
        for seq, ts_ms, etype, cat, data in events_s2:
            await db.execute(
                text("""
                    INSERT INTO session_events (session_id, sequence, timestamp_ms, event_type, category, data, masked)
                    VALUES (:sid, :seq, :ts, :et, :cat, :data, false)
                """),
                {"sid": s2_id, "seq": seq, "ts": ts_ms, "et": etype, "cat": cat, "data": json.dumps(data)},
            )

        a2_id = uid()
        await db.execute(
            text("""
                INSERT INTO analysis_results (id, session_id, status, confidence, summary,
                    severity_suggestion, steps, root_cause, duplicate_check,
                    completed_at, created_at, updated_at)
                VALUES (:id, :sid, 'completed', 0.92, :summary, :sev,
                    :steps, :rc, :dc, :ca, now(), now())
            """),
            {
                "id": a2_id,
                "sid": s2_id,
                "summary": "Order confirmation page crashes due to race condition between cart clear and page render",
                "sev": "critical",
                "steps": json.dumps([
                    {"order": 1, "action": "Navigate to product page", "value": "Widget Pro", "actual": "Page loaded"},
                    {"order": 2, "action": "Add to cart", "value": "1x Widget Pro", "actual": "Item added"},
                    {"order": 3, "action": "Navigate to cart", "value": "/cart", "actual": "Cart shows 1 item"},
                    {"order": 4, "action": "Increase quantity", "value": "3x Widget Pro", "actual": "Quantity updated"},
                    {"order": 5, "action": "Click checkout", "value": "Checkout button", "actual": "Payment form shown"},
                    {"order": 6, "action": "Confirm payment", "value": "Confirm button", "actual": "Payment processed"},
                    {"order": 7, "action": "Observe confirmation", "value": "Order page", "actual": "Page crashes with undefined property error"},
                ]),
                "rc": json.dumps({
                    "summary": "Race condition: POST /orders clears the cart server-side before the confirmation page renders. The React component tries to read cart.items which is now undefined.",
                    "category": "race-condition",
                    "evidence_chain": [
                        {"event_type": "network_request", "timestamp_ms": 6000, "detail": "POST /orders succeeded (200) - cart was cleared"},
                        {"event_type": "console_log", "timestamp_ms": 6200, "detail": "TypeError: Cannot read properties of undefined (reading 'items')"},
                        {"event_type": "dom_mutation", "timestamp_ms": 6300, "detail": "React error boundary caught crash, blank screen shown"},
                    ],
                }),
                "dc": json.dumps({
                    "is_duplicate": True,
                    "matches": [
                        {"id": "BUG-1042", "title": "Confirmation page blank after checkout", "similarity": "0.91"},
                        {"id": "BUG-987", "title": "Cart empty before render on confirm", "similarity": "0.84"},
                    ],
                    "note": "2 potential duplicates found",
                }),
                "ca": utcnow() - timedelta(hours=4, minutes=50),
            },
        )

        # Bug report for session 2
        br2_id = uid()
        await db.execute(
            text("""
                INSERT INTO bug_reports (id, session_id, analysis_result_id, user_id, title, severity,
                    steps, root_cause, duplicate_check, replay_url,
                    jira_ticket_key, jira_url, status, filed_at, created_at, updated_at)
                VALUES (:id, :sid, :aid, 'single-user', :title, :sev,
                    :steps, :rc, :dc, :replay,
                    :jk, :ju, 'filed', :fa, now(), now())
            """),
            {
                "id": br2_id,
                "sid": s2_id,
                "aid": a2_id,
                "title": "Order confirmation page crashes after successful payment",
                "sev": "critical",
                "steps": json.dumps([]),
                "rc": json.dumps({}),
                "dc": json.dumps({}),
                "replay": f"http://localhost:3000/replay/{s2_id}",
                "jk": "BUG-1049",
                "ju": "https://example.atlassian.net/browse/BUG-1049",
                "fa": utcnow() - timedelta(hours=4),
            },
        )

        # ── Session 3: Search autocomplete lag (queued analysis) ──
        s3_id = uid()
        s3_started = utcnow() - timedelta(minutes=15)
        s3_ended = s3_started + timedelta(seconds=23)
        await db.execute(
            text("""
                INSERT INTO sessions (id, url, browser_name, browser_version, os,
                    viewport_width, viewport_height, started_at, ended_at, duration_sec,
                    event_count, size_bytes, status, checksum, created_at, updated_at)
                VALUES (:id, :url, :bv, :bver, :os, :vw, :vh, :sa, :ea, :dur, :ec, :sb, :st, :ck, now(), now())
            """),
            {
                "id": s3_id,
                "url": "https://docs.example.com/search",
                "bv": "Firefox",
                "bver": "126.0",
                "os": "Ubuntu 24.04",
                "vw": 1366,
                "vh": 768,
                "sa": s3_started,
                "ea": s3_ended,
                "dur": 23,
                "ec": 18,
                "sb": 21400,
                "st": "packaged",
                "ck": "x9y8z7w6v5u4",
            },
        )
        sessions.append(s3_id)

        events_s3 = [
            (1, 0, "user_interaction", "navigation", {"action": "navigation", "url": "https://docs.example.com/search"}),
            (2, 300, "dom_mutation", "rrweb", {"type": "childList", "target_selector": "body"}),
            (3, 500, "user_interaction", "input", {"action": "input", "target_selector": "#search-input", "value": "react"}),
            (4, 600, "network_request", "api", {"method": "GET", "url": "https://api.docs.example.com/search?q=react&limit=10", "status": 200, "duration_ms": 1800, "is_error": False}),
            (5, 700, "console_log", "console", {"level": "warn", "message": "Search debounce not configured, firing on every keystroke"}),
            (6, 1000, "user_interaction", "input", {"action": "input", "target_selector": "#search-input", "value": "react form"}),
            (7, 1100, "network_request", "api", {"method": "GET", "url": "https://api.docs.example.com/search?q=react+form&limit=10", "status": 200, "duration_ms": 2200, "is_error": False}),
            (8, 1500, "user_interaction", "input", {"action": "input", "target_selector": "#search-input", "value": "react form validation"}),
            (9, 1600, "network_request", "api", {"method": "GET", "url": "https://api.docs.example.com/search?q=react+form+validation&limit=10", "status": 200, "duration_ms": 3100, "is_error": False}),
            (10, 2000, "console_log", "console", {"level": "error", "message": "Search request timed out after 3000ms"}),
            (11, 2200, "network_request", "api", {"method": "GET", "url": "https://api.docs.example.com/search?q=react+form+validation&limit=10", "status": 408, "duration_ms": 3000, "is_error": True}),
            (12, 2500, "console_log", "console", {"level": "error", "message": "Uncaught TypeError: Cannot set properties of null (setting 'innerHTML') at SearchResult.render"}),
        ]
        for seq, ts_ms, etype, cat, data in events_s3:
            await db.execute(
                text("""
                    INSERT INTO session_events (session_id, sequence, timestamp_ms, event_type, category, data, masked)
                    VALUES (:sid, :seq, :ts, :et, :cat, :data, false)
                """),
                {"sid": s3_id, "seq": seq, "ts": ts_ms, "et": etype, "cat": cat, "data": json.dumps(data)},
            )

        await db.execute(
            text("""
                INSERT INTO analysis_results (id, session_id, status, created_at, updated_at)
                VALUES (:id, :sid, 'queued', now(), now())
            """),
            {"id": uid(), "sid": s3_id},
        )

        # ── Session 4: Profile upload failure (no analysis yet) ──
        s4_id = uid()
        s4_started = utcnow() - timedelta(minutes=5)
        s4_ended = s4_started + timedelta(seconds=31)
        await db.execute(
            text("""
                INSERT INTO sessions (id, url, browser_name, browser_version, os,
                    viewport_width, viewport_height, started_at, ended_at, duration_sec,
                    event_count, size_bytes, status, checksum, created_at, updated_at)
                VALUES (:id, :url, :bv, :bver, :os, :vw, :vh, :sa, :ea, :dur, :ec, :sb, :st, :ck, now(), now())
            """),
            {
                "id": s4_id,
                "url": "https://app.example.com/profile/edit",
                "bv": "Chrome",
                "bver": "124.0.6367.91",
                "os": "macOS 14.4",
                "vw": 1440,
                "vh": 900,
                "sa": s4_started,
                "ea": s4_ended,
                "dur": 31,
                "ec": 15,
                "sb": 18900,
                "st": "packaged",
                "ck": "m1n2o3p4q5r6",
            },
        )
        sessions.append(s4_id)

        events_s4 = [
            (1, 0, "user_interaction", "navigation", {"action": "navigation", "url": "https://app.example.com/profile/edit"}),
            (2, 400, "dom_mutation", "rrweb", {"type": "childList", "target_selector": "body"}),
            (3, 800, "user_interaction", "click", {"action": "click", "target_selector": ".avatar-upload"}),
            (4, 1000, "network_request", "api", {"method": "GET", "url": "https://api.example.com/user/profile", "status": 200, "duration_ms": 120, "is_error": False}),
            (5, 2000, "user_interaction", "input", {"action": "input", "target_selector": "#display-name", "value": "John Doe"}),
            (6, 2500, "network_request", "api", {"method": "PUT", "url": "https://api.example.com/user/profile", "status": 200, "duration_ms": 200, "is_error": False}),
            (7, 3000, "user_interaction", "click", {"action": "click", "target_selector": ".avatar-upload"}),
            (8, 3500, "network_request", "api", {"method": "POST", "url": "https://api.example.com/user/avatar", "status": 413, "duration_ms": 50, "is_error": True}),
            (9, 3550, "console_log", "console", {"level": "error", "message": "Upload failed: Payload Too Large. Max size is 5MB, received 8.2MB"}),
            (10, 4000, "console_log", "console", {"level": "warn", "message": "No user-facing error message shown for upload failure"}),
            (11, 5000, "user_interaction", "click", {"action": "click", "target_selector": ".avatar-upload"}),
            (12, 5500, "network_request", "api", {"method": "POST", "url": "https://api.example.com/user/avatar", "status": 413, "duration_ms": 50, "is_error": True}),
            (13, 5550, "console_log", "console", {"level": "error", "message": "Upload failed: Payload Too Large. Max size is 5MB, received 8.2MB"}),
            (14, 6000, "user_interaction", "click", {"action": "click", "target_selector": "#bug-marker-btn"}),
            (15, 6100, "bug_marker", "bug", {"note": "Avatar upload fails silently - no error toast shown to user"}),
        ]
        for seq, ts_ms, etype, cat, data in events_s4:
            await db.execute(
                text("""
                    INSERT INTO session_events (session_id, sequence, timestamp_ms, event_type, category, data, masked)
                    VALUES (:sid, :seq, :ts, :et, :cat, :data, false)
                """),
                {"sid": s4_id, "seq": seq, "ts": ts_ms, "et": etype, "cat": cat, "data": json.dumps(data)},
            )

        # ── Session 5: Recent recording (just uploaded) ──
        s5_id = uid()
        s5_started = utcnow() - timedelta(minutes=2)
        s5_ended = s5_started + timedelta(seconds=12)
        await db.execute(
            text("""
                INSERT INTO sessions (id, url, browser_name, browser_version, os,
                    viewport_width, viewport_height, started_at, ended_at, duration_sec,
                    event_count, size_bytes, status, checksum, created_at, updated_at)
                VALUES (:id, :url, :bv, :bver, :os, :vw, :vh, :sa, :ea, :dur, :ec, :sb, :st, :ck, now(), now())
            """),
            {
                "id": s5_id,
                "url": "https://analytics.example.com/reports",
                "bv": "Chrome",
                "bver": "125.0.6422.60",
                "os": "Windows 11",
                "vw": 1920,
                "vh": 1080,
                "sa": s5_started,
                "ea": s5_ended,
                "dur": 12,
                "ec": 8,
                "sb": 9200,
                "st": "packaged",
                "ck": "t1u2v3w4x5y6",
            },
        )
        sessions.append(s5_id)

        events_s5 = [
            (1, 0, "user_interaction", "navigation", {"action": "navigation", "url": "https://analytics.example.com/reports"}),
            (2, 200, "dom_mutation", "rrweb", {"type": "childList", "target_selector": "body"}),
            (3, 500, "network_request", "api", {"method": "GET", "url": "https://api.analytics.example.com/reports?range=7d", "status": 200, "duration_ms": 3400, "is_error": False}),
            (4, 4000, "console_log", "console", {"level": "warn", "message": "Report query took 3400ms, consider adding database index"}),
            (5, 5000, "user_interaction", "click", {"action": "click", "target_selector": ".export-csv"}),
            (6, 5500, "network_request", "api", {"method": "GET", "url": "https://api.analytics.example.com/reports/export?format=csv", "status": 502, "duration_ms": 8000, "is_error": True}),
            (7, 5600, "console_log", "console", {"level": "error", "message": "Export failed: 502 Bad Gateway"}),
            (8, 6000, "user_interaction", "click", {"action": "click", "target_selector": "#bug-marker-btn"}),
        ]
        for seq, ts_ms, etype, cat, data in events_s5:
            await db.execute(
                text("""
                    INSERT INTO session_events (session_id, sequence, timestamp_ms, event_type, category, data, masked)
                    VALUES (:sid, :seq, :ts, :et, :cat, :data, false)
                """),
                {"sid": s5_id, "seq": seq, "ts": ts_ms, "et": etype, "cat": cat, "data": json.dumps(data)},
            )

        # ── Production incidents and impact links ──
        inc1_id = uid()
        await db.execute(
            text("""
                INSERT INTO production_incidents (id, title, incident_url, affected_url, error_message, source, payload, occurred_at, created_at, updated_at)
                VALUES (:id, :title, :url, :au, :em, 'datadog', '{}', :oa, now(), now())
            """),
            {
                "id": inc1_id,
                "title": "Production outage: Checkout service returning 502",
                "url": "https://status.example.com/incidents/4521",
                "au": "https://shop.example.com/checkout",
                "em": "upstream connect error or disconnect/reset before headers",
                "oa": utcnow() - timedelta(hours=3),
            },
        )

        inc2_id = uid()
        await db.execute(
            text("""
                INSERT INTO production_incidents (id, title, incident_url, affected_url, error_message, source, payload, occurred_at, created_at, updated_at)
                VALUES (:id, :title, :url, :au, :em, 'pagerduty', '{}', :oa, now(), now())
            """),
            {
                "id": inc2_id,
                "title": "Elevated error rates on /api/dashboard/stats",
                "url": "https://status.example.com/incidents/4518",
                "au": "https://api.example.com/dashboard/stats",
                "em": "NullPointerException in StatsController.getOrganizationStats",
                "oa": utcnow() - timedelta(hours=1),
            },
        )

        # Impact links
        await db.execute(
            text("""
                INSERT INTO impact_links (id, bug_report_id, incident_id, incident_title, incident_url,
                    detected_at, match_score, match_reason, notification_status, evidence, created_at, updated_at)
                VALUES (:id, :brid, :iid, :it, :iu, :da, :ms, :mr, 'sent', '{}', now(), now())
            """),
            {
                "id": uid(),
                "brid": br2_id,
                "iid": inc1_id,
                "it": "Production outage: Checkout service returning 502",
                "iu": "https://status.example.com/incidents/4521",
                "da": utcnow() - timedelta(hours=2),
                "ms": 0.87,
                "mr": "URL pattern match on /checkout + similar timeout error signature",
            },
        )

        await db.execute(
            text("""
                INSERT INTO impact_links (id, bug_report_id, incident_id, incident_title, incident_url,
                    detected_at, match_score, match_reason, notification_status, evidence, created_at, updated_at)
                VALUES (:id, :brid, :iid, :it, :iu, :da, :ms, :mr, 'sent', '{}', now(), now())
            """),
            {
                "id": uid(),
                "brid": br2_id,
                "iid": inc2_id,
                "it": "Elevated error rates on /api/dashboard/stats",
                "iu": "https://status.example.com/incidents/4518",
                "da": utcnow() - timedelta(minutes=30),
                "ms": 0.72,
                "mr": "Error message similarity: NullPointerException pattern matches root cause analysis",
            },
        )

        await db.commit()
        print(f"Seeded {len(sessions)} sessions with events, analysis, bug reports, and impact links.")
        for i, sid in enumerate(sessions, 1):
            print(f"  Session {i}: http://localhost:3000/replay/{sid}")


if __name__ == "__main__":
    asyncio.run(seed())
