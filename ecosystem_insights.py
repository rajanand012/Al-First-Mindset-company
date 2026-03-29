"""Fetch AI ecosystem insights for a company's industry using Claude + web search."""

import json
import os
import re
import time
import traceback

import anthropic
from dotenv import load_dotenv

load_dotenv()

# Simple in-memory TTL cache (1 hour)
_cache = {}
_CACHE_TTL = 3600


def _cache_key(company_name, industry_segment):
    return f"{company_name.lower().strip()}|{industry_segment.lower().strip()}"


def fetch_ecosystem_insights(company_name, industry_segment):
    """Fetch AI-related insights about peers in this company's industry ecosystem.

    Returns a list of 10 dicts: [{"question_id": "...", "insight": "...", "source": "..."}]
    Uses Claude API with web_search tool for real-time data.
    Results are cached for 1 hour.
    """
    key = _cache_key(company_name, industry_segment)

    # Check cache
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < _CACHE_TTL:
            return entry["data"]

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Ecosystem insights: No API key set")
        return _fallback_insights()

    try:
        insights = _fetch_with_web_search(company_name, industry_segment, api_key)
        _cache[key] = {"data": insights, "timestamp": time.time()}
        return insights
    except Exception as e:
        print(f"Ecosystem insights (web search) error: {e}")
        traceback.print_exc()

    # Fallback: try without web search (uses Claude's training data)
    try:
        insights = _fetch_without_web_search(company_name, industry_segment, api_key)
        _cache[key] = {"data": insights, "timestamp": time.time()}
        return insights
    except Exception as e:
        print(f"Ecosystem insights (fallback) error: {e}")
        traceback.print_exc()

    return _fallback_insights()


def _build_prompt(company_name, industry_segment):
    return f"""You are researching AI adoption trends in the {industry_segment or 'manufacturing'} industry to provide context for a company called "{company_name}".

Find recent, real examples of how OTHER companies in this industry ecosystem (peers, leaders, or adjacent players — NOT {company_name} itself) are using AI. Focus on well-known companies in the {industry_segment or 'manufacturing'} space.

Provide exactly 10 brief insights, one for each of these categories:

1. ai_strategy — A peer company's AI strategy or digital transformation announcement
2. ai_production — How a peer uses AI in manufacturing/production processes
3. data_infrastructure — A peer's investment in data platforms, analytics, or ML infrastructure
4. ai_products — A peer's AI-powered product or service launch
5. supply_chain — How a peer uses AI in supply chain, logistics, or forecasting
6. ai_talent — A peer's AI hiring, training, or talent investment
7. ai_budget — A peer's AI investment, funding, or R&D spending
8. customer_experience — How a peer uses AI for customer experience
9. ai_governance — A peer's responsible AI or governance initiative
10. innovation_rd — A peer's AI research, patents, or innovation lab

IMPORTANT RULES:
- Each insight MUST include specific numbers (dollar amounts, percentages, headcount, ROI figures, timelines). Example: "Did you know? Siemens invested $1.2B in AI-driven manufacturing in 2025, targeting 30% productivity gains."
- Each insight must be 1-2 sentences and mention the specific company name.
- The "source" field must cite a real publication or report name (e.g., "Reuters, 2025" or "Company Annual Report 2025").
- Start each with "Did you know?" or a similar engaging hook.

Respond with ONLY valid JSON (no markdown, no commentary, no code fences):

[
  {{"question_id": "ai_strategy", "insight": "...", "source": "..."}},
  {{"question_id": "ai_production", "insight": "...", "source": "..."}},
  {{"question_id": "data_infrastructure", "insight": "...", "source": "..."}},
  {{"question_id": "ai_products", "insight": "...", "source": "..."}},
  {{"question_id": "supply_chain", "insight": "...", "source": "..."}},
  {{"question_id": "ai_talent", "insight": "...", "source": "..."}},
  {{"question_id": "ai_budget", "insight": "...", "source": "..."}},
  {{"question_id": "customer_experience", "insight": "...", "source": "..."}},
  {{"question_id": "ai_governance", "insight": "...", "source": "..."}},
  {{"question_id": "innovation_rd", "insight": "...", "source": "..."}}
]"""


def _fetch_with_web_search(company_name, industry_segment, api_key):
    """Try fetching insights using Claude's web search tool."""
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(company_name, industry_segment)

    # Initial call with web search tool
    messages = [{"role": "user", "content": prompt}]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]

    # Handle multi-turn: Claude may need to call the tool and then respond
    max_turns = 5
    for _ in range(max_turns):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2500,
            temperature=0,
            tools=tools,
            messages=messages,
        )

        # If Claude is done (end_turn), extract text
        if response.stop_reason == "end_turn":
            return _extract_insights(response.content)

        # If Claude wants to use a tool, we need to pass results back
        # For server-side tools like web_search, the API handles it automatically
        # If we still get tool_use, something unexpected happened
        if response.stop_reason == "tool_use":
            # Append assistant message and empty tool results to continue
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Search completed.",
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            # Some other stop reason — extract whatever text we got
            return _extract_insights(response.content)

    return _extract_insights(response.content)


def _fetch_without_web_search(company_name, industry_segment, api_key):
    """Fallback: fetch insights using Claude's training knowledge (no web search)."""
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(company_name, industry_segment)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    return _extract_insights(response.content)


def _extract_insights(content_blocks):
    """Extract JSON insights from Claude's response content blocks."""
    raw_text = ""
    for block in content_blocks:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()

    # Remove markdown code fences if present
    if "```" in raw_text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
        if match:
            raw_text = match.group(1).strip()

    # Try to find JSON array in the text
    bracket_start = raw_text.find("[")
    bracket_end = raw_text.rfind("]")
    if bracket_start != -1 and bracket_end != -1:
        raw_text = raw_text[bracket_start:bracket_end + 1]

    insights = json.loads(raw_text)

    if not isinstance(insights, list) or len(insights) == 0:
        raise ValueError("Invalid insights format")

    return insights


def _fallback_insights():
    """Return placeholder insights when API is unavailable."""
    categories = [
        "ai_strategy", "ai_production", "data_infrastructure", "ai_products",
        "supply_chain", "ai_talent", "ai_budget", "customer_experience",
        "ai_governance", "innovation_rd",
    ]
    return [
        {
            "question_id": cat,
            "insight": "Industry leaders in your ecosystem are actively investing in this area. Complete the assessment to see how you compare.",
            "source": "Industry trend",
        }
        for cat in categories
    ]
