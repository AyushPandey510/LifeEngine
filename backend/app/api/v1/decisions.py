"""
Decision Simulation Endpoints (Production-Ready AI Decision Engine)
"""

from datetime import datetime, timezone
import json
import uuid
import asyncio
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models.db import Decision, Profile, User
from app.models.schemas import DecisionRequest, DecisionResponse, OptionResult
from app.services.ai_service import generate_ai_response

router = APIRouter()


# ==============================
# 🧠 SAFE JSON PARSER
# ==============================
def safe_json_parse(text: str):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return None


# ==============================
# 🔥 AI EVALUATION FUNCTION
# ==============================
async def evaluate_option(option: str, decision: str, profile: Profile | None):
    context = {
        "goals": (profile.goals if profile else []) or [],
        "habits": (profile.habits if profile else []) or [],
        "consistency_score": profile.consistency_score if profile else 50,
        "risk_tolerance": profile.risk_tolerance if profile else 50,
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are a high-level decision intelligence system.\n"
                "You evaluate choices realistically based on user data.\n"
                "Be logical, not motivational."
            ),
        },
        {
            "role": "user",
            "content": f"""
Decision:
{decision}

Option:
{option}

User Profile:
{json.dumps(context)}

Instructions:
- Score from 0 to 100
- 0 = very bad decision
- 100 = best decision
- Consider long-term outcomes, consistency, goals, risk

Return STRICT JSON ONLY:
{{
  "score": number,
  "reasoning": "short explanation (max 2 lines)"
}}
"""
        }
    ]

    try:
        text, _ = await generate_ai_response(
            messages,
            temperature=0.3,
            max_tokens=200
        )

        parsed = safe_json_parse(text)

        if not parsed:
            raise ValueError("Invalid JSON")

        return {
            "option": option,
            "score": int(parsed.get("score", 50)),
            "reasoning": parsed.get("reasoning", "No reasoning provided"),
        }

    except Exception:
        # fallback scoring
        return {
            "option": option,
            "score": 50,
            "reasoning": "Fallback evaluation (AI parsing failed)",
        }


# ==============================
# 🚀 MAIN ENDPOINT
# ==============================
@router.post("/simulate", response_model=DecisionResponse)
async def simulate_decision(
    payload: DecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    AI-powered decision simulation with multiple options
    """

    if not payload.options or len(payload.options) < 2:
        raise HTTPException(status_code=400, detail="At least 2 options required")

    # 🔹 fetch profile
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    # 🔥 evaluate options concurrently (FAST)
    tasks = [
        evaluate_option(option, payload.decision_text, profile)
        for option in payload.options
    ]

    results = await asyncio.gather(*tasks)

    # 🔹 sort best → worst
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    recommended = results[0]["option"]

    # 🔹 persist decision
    decision = Decision(
        id=uuid.uuid4(),
        user_id=current_user.id,
        decision_text=payload.decision_text,
        option_a=payload.options[0],
        option_b=payload.options[1] if len(payload.options) > 1 else "",
        simulation_result=results,
        created_at=datetime.now(timezone.utc),
    )

    db.add(decision)
    await db.commit()   # ✅ important

    # 🔹 response
    return DecisionResponse(
        id=decision.id,
        decision_text=decision.decision_text,
        options=[OptionResult(**r) for r in results],
        recommended=recommended,
        created_at=decision.created_at,
    )