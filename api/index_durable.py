#!/usr/bin/env python3
"""
EVEZ Operator API — durable/auth-capable entrypoint.

This is a drop-in replacement candidate for api/index.py.
It preserves the current route surface while upgrading spine storage from
in-memory process state to SQLite-backed durable state.

Suggested local run:
    uvicorn api.index_durable:app --port 7777
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.auth_guard import require_operator_token
from api.durable_spine import DurableSpineStore

app = FastAPI(
    title="EVEZ Operator API",
    description="EVEZ behavioral OS — durable operator spine entrypoint",
    version="1.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

store = DurableSpineStore()


VALID_TYPES = {"observation", "transformation", "claim", "test", "decision", "linkage"}
VALID_LANES = {"empirical", "documentary", "metaphysical"}


def _storage_mode() -> str:
    return "durable"


def _auth_mode() -> str:
    return "bearer" if os.getenv("OPERATOR_API_TOKEN", "").strip() else "open"


def _durability_scope() -> str:
    db_path = os.getenv("SPINE_DB_PATH", "data/operator_spine.db")
    # honest but conservative: durable locally, platform persistence unknown until verified
    return "persistent-volume" if db_path.startswith("/data/") else "unknown"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _normalize(obj: Any, float_paths: set[str], path: str = "") -> Any:
    if isinstance(obj, str):
        return nfc(obj)
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f"Poison float at {path}")
        if path in float_paths:
            v = round(obj, 6)
            return 0.0 if v == 0.0 else v
        raise TypeError(f"Float at non-declared path {path}")
    if isinstance(obj, int):
        return obj
    if isinstance(obj, dict):
        return {nfc(k): _normalize(v, float_paths, f"{path}.{k}") for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_normalize(v, float_paths, f"{path}[{i}]") for i, v in enumerate(obj)]
    if obj is None:
        return None
    raise TypeError(f"Unsupported type at {path}: {type(obj)}")


def canonicalize(obj: dict, float_paths: list[str] | None = None) -> tuple[str, str]:
    fp = set(float_paths or [])
    normalized = _normalize(obj, fp)
    jcs = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(jcs.encode("utf-8")).hexdigest()
    return jcs, digest


def _make_event(event_type: str, lane: str, payload: dict, parent_hash: str | None) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base = {
        "event_type": event_type,
        "lane": lane,
        "payload": payload,
        "timestamp": ts,
        "height": 0,
        "parent_event_hash": parent_hash or "",
    }
    evidence_obj = {k: v for k, v in base.items() if k != "parent_event_hash" and k != "height"}
    _, evidence_hash = canonicalize(evidence_obj)
    base["evidence_hash"] = evidence_hash
    _, event_hash = canonicalize(base)
    base["event_hash"] = event_hash
    return base


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "evez-operator-api",
        "version": "1.1.0",
        "spine_height": store.total_events(),
        "docs": "/docs",
        "tools": "/tools",
        "storage_mode": _storage_mode(),
        "auth_mode": _auth_mode(),
        "durability_scope": _durability_scope(),
    }


@app.get("/tools")
def list_tools():
    return {
        "schema_version": "1.0",
        "name": "evez-operator",
        "description": "EVEZ behavioral operating system tools",
        "tools": [
            {
                "name": "spine_event",
                "description": "Add typed event to EVEZ spine",
                "inputSchema": {
                    "type": "object",
                    "required": ["event_type", "lane", "payload"],
                    "properties": {
                        "event_type": {"type": "string", "enum": sorted(VALID_TYPES)},
                        "lane": {"type": "string", "enum": sorted(VALID_LANES)},
                        "payload": {"type": "object"},
                        "parent_event_hash": {"type": "string"},
                    },
                },
            },
            {
                "name": "spine_verify",
                "description": "Verify SHA-256 chain integrity",
                "inputSchema": {"type": "object", "properties": {"from_height": {"type": "integer", "default": 0}}},
            },
            {
                "name": "contradiction_check",
                "description": "List active unsat cores",
                "inputSchema": {"type": "object", "properties": {"scope": {"type": "string", "default": "all"}}},
            },
            {
                "name": "fire_anchor_payload",
                "description": "Build Base Sepolia calldata for FIRE event",
                "inputSchema": {
                    "type": "object",
                    "required": ["fire_number", "evidence_hash"],
                    "properties": {
                        "fire_number": {"type": "integer"},
                        "evidence_hash": {"type": "string"},
                        "round": {"type": "integer"},
                        "v_score": {"type": "number"},
                    },
                },
            },
            {
                "name": "canonicalize",
                "description": "Normalize + JCS + SHA-256 any JSON object",
                "inputSchema": {
                    "type": "object",
                    "required": ["input"],
                    "properties": {
                        "input": {"type": "object"},
                        "float_paths": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            {"name": "deploy_status", "description": "All EVEZ service health", "inputSchema": {"type": "object", "properties": {}}},
        ],
    }


class SpineEventRequest(BaseModel):
    event_type: str
    lane: str
    payload: dict
    parent_event_hash: Optional[str] = None


@app.post("/spine/event", dependencies=[Depends(require_operator_token)])
def add_spine_event(req: SpineEventRequest):
    if req.event_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid event_type: {req.event_type}")
    if req.lane not in VALID_LANES:
        raise HTTPException(400, f"Invalid lane: {req.lane}")

    parent = req.parent_event_hash
    if parent is None:
        parent = store.get_tip_hash() or ""

    event = _make_event(req.event_type, req.lane, req.payload, parent)
    try:
        event = store.append_event(event)
    except ValueError as e:
        raise HTTPException(409, str(e))

    return {
        "ok": True,
        "event_hash": event["event_hash"],
        "evidence_hash": event["evidence_hash"],
        "height": event["height"],
        "storage_mode": _storage_mode(),
    }


@app.get("/spine/verify")
def verify_spine(from_height: int = 0):
    result = store.verify(from_height=from_height)
    result["storage_mode"] = _storage_mode()
    return result


@app.get("/spine/events")
def get_spine(limit: int = 20, offset: int = 0):
    return {
        "events": store.list_events(limit=limit, offset=offset),
        "total": store.total_events(),
        "storage_mode": _storage_mode(),
    }


class CanonicalizeRequest(BaseModel):
    input: dict
    float_paths: list[str] = []


@app.post("/canonicalize", dependencies=[Depends(require_operator_token)])
def canonicalize_endpoint(req: CanonicalizeRequest):
    try:
        jcs, digest = canonicalize(req.input, req.float_paths)
        return {"jcs": jcs, "sha256": digest, "bytes": len(jcs)}
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))


@app.get("/contradictions")
def get_contradictions(scope: str = "all"):
    cores = [
        {
            "id": "unsat-001",
            "scope": "revenue",
            "priority": "HIGH",
            "description": "Railway evez-os undeployed — Stripe webhooks dead",
            "resolution": "railway up in evez-os repo",
            "test": "HTTP GET https://evez-os.railway.app/health → 200",
        },
        {
            "id": "unsat-002",
            "scope": "fire",
            "priority": "MEDIUM",
            "description": "FIRE#125 unanchored — no funded wallet configured",
            "resolution": "Set WALLET_PRIVATE_KEY + ALCHEMY_API_KEY",
            "test": "eth_getBalance on wallet > 0.001 ETH",
        },
        {
            "id": "unsat-003",
            "scope": "contacts",
            "priority": "LOW",
            "description": "daniel@goodfire.ai hard-bounced, no valid Goodfire contact",
            "resolution": "Find contact via goodfire.ai/team or LinkedIn",
            "test": "SMTP RCPT TO → 250 OK",
        },
    ]
    if scope != "all":
        cores = [c for c in cores if c["scope"] == scope]
    return {"unsat_cores": cores, "count": len(cores), "data_mode": "diagnostic_static"}


@app.post("/fire/anchor", dependencies=[Depends(require_operator_token)])
def fire_anchor(fire_number: int, evidence_hash: str, round: int = 0, v_score: float = 0.0):
    payload = {
        "evidence_hash": evidence_hash,
        "fire_number": fire_number,
        "round": round,
        "system": "EVEZ_OS",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "v_score": v_score,
    }
    jcs, digest = canonicalize(payload, float_paths=[".v_score"])
    calldata = "0x" + jcs.encode("utf-8").hex()
    return {
        "fire_number": fire_number,
        "anchor_hash": digest,
        "calldata": calldata,
        "calldata_length_bytes": len(jcs),
        "network": "base-sepolia",
    }


@app.get("/deploy/status")
def deploy_status():
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "services": {
            "operator_spine_storage": {
                "status": "SQLITE_READY",
                "db_path": os.getenv("SPINE_DB_PATH", "data/operator_spine.db"),
            },
            "operator_spine_auth": {
                "status": _auth_mode().upper(),
                "action": "set OPERATOR_API_TOKEN to require bearer auth" if _auth_mode() == "open" else "token required for protected writes",
            },
            "vercel_mcp_server": {
                "status": "ENTRYPOINT_CANDIDATE",
                "url": "https://evez-operator.vercel.app",
            },
            "durability_scope": {
                "status": _durability_scope().upper(),
            },
        },
        "data_mode": "diagnostic_mixed",
    }
