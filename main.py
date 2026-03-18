import hashlib
import time
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator


class RolloutStrategy(str, Enum):
    ALL = "all"
    PERCENTAGE = "percentage"
    USERS = "users"
    GROUPS = "groups"


class FlagRule(BaseModel):
    strategy: RolloutStrategy
    percentage: float | None = None
    user_ids: list[str] | None = None
    groups: list[str] | None = None

    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v):
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError("percentage must be between 0 and 100")
        return v


class FeatureFlag(BaseModel):
    key: str
    enabled: bool
    rule: FlagRule
    description: str = ""
    created_at: float
    updated_at: float


class CreateFlagRequest(BaseModel):
    key: str
    enabled: bool = False
    rule: FlagRule
    description: str = ""


class UpdateFlagRequest(BaseModel):
    enabled: bool | None = None
    rule: FlagRule | None = None
    description: str | None = None


class EvaluateRequest(BaseModel):
    user_id: str
    groups: list[str] = []
    attributes: dict[str, Any] = {}


class EvaluateResponse(BaseModel):
    flag_key: str
    enabled: bool
    reason: str


flags: dict[str, FeatureFlag] = {}

app = FastAPI(title="Feature Flag Service")


def evaluate_flag(flag: FeatureFlag, user_id: str, groups: list[str]) -> tuple[bool, str]:
    if not flag.enabled:
        return False, "flag_disabled"

    rule = flag.rule

    if rule.strategy == RolloutStrategy.ALL:
        return True, "strategy_all"

    if rule.strategy == RolloutStrategy.USERS:
        if rule.user_ids and user_id in rule.user_ids:
            return True, "user_allowlisted"
        return False, "user_not_in_allowlist"

    if rule.strategy == RolloutStrategy.GROUPS:
        if rule.groups and any(g in rule.groups for g in groups):
            return True, "group_match"
        return False, "no_group_match"

    if rule.strategy == RolloutStrategy.PERCENTAGE:
        bucket = int(hashlib.md5(f"{flag.key}:{user_id}".encode()).hexdigest(), 16) % 100
        threshold = rule.percentage or 0.0
        if bucket < threshold:
            return True, f"in_rollout_bucket_{bucket}"
        return False, f"outside_rollout_bucket_{bucket}"

    return False, "unknown_strategy"


@app.post("/flags", status_code=201)
async def create_flag(body: CreateFlagRequest):
    if body.key in flags:
        raise HTTPException(status_code=409, detail=f"Flag '{body.key}' already exists")
    now = time.time()
    flag = FeatureFlag(
        key=body.key,
        enabled=body.enabled,
        rule=body.rule,
        description=body.description,
        created_at=now,
        updated_at=now,
    )
    flags[body.key] = flag
    return flag


@app.get("/flags")
async def list_flags():
    return {"total": len(flags), "flags": list(flags.values())}


@app.get("/flags/{key}")
async def get_flag(key: str):
    flag = flags.get(key)
    if not flag:
        raise HTTPException(status_code=404, detail=f"Flag '{key}' not found")
    return flag


@app.patch("/flags/{key}")
async def update_flag(key: str, body: UpdateFlagRequest):
    flag = flags.get(key)
    if not flag:
        raise HTTPException(status_code=404, detail=f"Flag '{key}' not found")
    if body.enabled is not None:
        flag.enabled = body.enabled
    if body.rule is not None:
        flag.rule = body.rule
    if body.description is not None:
        flag.description = body.description
    flag.updated_at = time.time()
    return flag


@app.delete("/flags/{key}", status_code=204)
async def delete_flag(key: str):
    if key not in flags:
        raise HTTPException(status_code=404, detail=f"Flag '{key}' not found")
    del flags[key]


@app.post("/flags/{key}/evaluate")
async def evaluate(key: str, body: EvaluateRequest):
    flag = flags.get(key)
    if not flag:
        raise HTTPException(status_code=404, detail=f"Flag '{key}' not found")
    enabled, reason = evaluate_flag(flag, body.user_id, body.groups)
    return EvaluateResponse(flag_key=key, enabled=enabled, reason=reason)


@app.post("/evaluate/batch")
async def evaluate_batch(keys: list[str], body: EvaluateRequest):
    results = []
    for key in keys:
        flag = flags.get(key)
        if not flag:
            results.append(EvaluateResponse(flag_key=key, enabled=False, reason="flag_not_found"))
            continue
        enabled, reason = evaluate_flag(flag, body.user_id, body.groups)
        results.append(EvaluateResponse(flag_key=key, enabled=enabled, reason=reason))
    return {"results": results}


@app.get("/health")
async def health():
    return {"status": "ok", "total_flags": len(flags)}
