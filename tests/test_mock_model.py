from __future__ import annotations

from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from llm.client import MockModel


@pytest.fixture
def model():
    return MockModel()


class TestMockModelTimeIntent:
    @pytest.mark.asyncio
    async def test_returns_time_tool_for_chinese_time_query(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "现在几点"}]}]
        response = await model(prompt)
        assert response.content[0]["type"] == "tool_use"
        assert response.content[0]["name"] == "time.now"

    @pytest.mark.asyncio
    async def test_returns_time_tool_for_english_keywords(self, model: MockModel) -> None:
        keywords = ["what time", "current time", "date today", "now"]
        for kw in keywords:
            prompt = [{"role": "user", "content": [{"text": kw}]}]
            response = await model(prompt)
            assert response.content[0]["name"] == "time.now", f"failed for: {kw}"


class TestMockModelMathIntent:
    @pytest.mark.asyncio
    async def test_returns_math_tool_for_simple_expression(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "计算 3 + 5"}]}]
        response = await model(prompt)
        assert response.content[0]["type"] == "tool_use"
        assert response.content[0]["name"] == "math.calc"
        assert response.content[0]["input"]["expression"] == "3 + 5"

    @pytest.mark.asyncio
    async def test_extracts_expression_with_spaces(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "计算 (10 + 2) * 3"}]}]
        response = await model(prompt)
        assert response.content[0]["name"] == "math.calc"
        assert "(10 + 2) * 3" in response.content[0]["input"]["expression"]

    @pytest.mark.asyncio
    async def test_handles_division_and_subtraction(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "100 / 5 - 10"}]}]
        response = await model(prompt)
        assert response.content[0]["name"] == "math.calc"


class TestMockModelFallback:
    @pytest.mark.asyncio
    async def test_returns_text_for_unknown_intent(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "讲个笑话"}]}]
        response = await model(prompt)
        assert response.content[0]["type"] == "text"
        assert "模拟回答" in response.content[0]["text"]

    @pytest.mark.asyncio
    async def test_handles_empty_prompt(self, model: MockModel) -> None:
        prompt = []
        response = await model(prompt)
        assert response.content[0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_handles_empty_user_text(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": []}]
        response = await model(prompt)
        assert response.content[0]["type"] == "text"


class TestMockModelPromptExtraction:
    @pytest.mark.asyncio
    async def test_extracts_latest_user_text(self, model: MockModel) -> None:
        prompt = [
            {"role": "user", "content": [{"text": "first message"}]},
            {"role": "assistant", "content": [{"text": "response"}]},
            {"role": "user", "content": [{"text": "现在几点"}]},
        ]
        response = await model(prompt)
        # Should use the last user message for intent detection
        assert response.content[0]["name"] == "time.now"

    @pytest.mark.asyncio
    async def test_ignores_assistant_messages(self, model: MockModel) -> None:
        prompt = [
            {"role": "assistant", "content": [{"text": "what time is it"}]},
            {"role": "user", "content": [{"text": "hello"}]},
        ]
        response = await model(prompt)
        # "hello" has no time/math intent, so fallback
        assert response.content[0]["type"] == "text"


class TestMockModelPriority:
    @pytest.mark.asyncio
    async def test_time_takes_priority_over_math(self, model: MockModel) -> None:
        # When both intents match, time should win
        prompt = [{"role": "user", "content": [{"text": "时间 3 + 5"}]}]
        response = await model(prompt)
        assert response.content[0]["name"] == "time.now"
