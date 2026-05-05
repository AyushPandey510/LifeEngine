from app.api.v1.chat import (
    _build_system_prompt,
    _extract_goal_plan,
    _extract_onboarding_updates,
    _next_onboarding_question,
)
from app.models.db import Profile
from app.services.ai_service import _mock_embedding


def test_chat_extracts_profile_signals_from_normal_talk():
    updates = _extract_onboarding_updates(
        "My name is Ayush. I want to deploy Life Engine this week. I struggle with procrastination."
    )

    assert updates["display_name"] == "Ayush"
    assert updates["goal"]["description"] == "deploy Life Engine this week"
    assert updates["risk_area"]["description"] == "procrastination"
    assert updates["conversation_signal"]["source"] == "chat"


def test_onboarding_asks_for_next_missing_essential_field():
    profile = Profile(
        display_name="Ayush",
        goals=[{"description": "ship the MVP"}],
        habits=[],
        personality={},
    )

    assert _next_onboarding_question(profile) == "What is one habit you are trying to build or fix right now?"


def test_system_prompt_blocks_invented_context():
    profile = Profile(display_name="Ayush", goals=[], habits=[], personality={})
    prompt = _build_system_prompt(profile, "What is your current goal?")

    assert "not allowed to invent memories" in prompt
    assert "What is your current goal?" in prompt


def test_goal_plan_detector_returns_required_json_shape():
    plan = _extract_goal_plan("My goal is to deploy Life Engine within 10 days.")

    assert plan["goal"] == "deploy Life Engine within 10 days"
    assert plan["tasks"]
    assert plan["progress"] == "0%"
    assert plan["next_step"]


def test_mock_embeddings_are_deterministic_and_distinguish_text():
    first = _mock_embedding("same text", 64)
    second = _mock_embedding("same text", 64)
    different = _mock_embedding("different text", 64)

    assert first == second
    assert first != different
