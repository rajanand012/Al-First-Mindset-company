"""Fetch AI ecosystem insights for a company's industry using Claude + web search."""

import json
import os
import time

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
        return _fallback_insights()

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are researching AI adoption trends in the {industry_segment or 'manufacturing'} industry to provide context for a company called "{company_name}".

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

Each insight should be 1-2 sentences, factual, recent, and mention the specific company name. Start each with "Did you know?" or a similar engaging hook.

Respond with ONLY valid JSON (no markdown):

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

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            temperature=0,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response (may have multiple content blocks with tool use)
        raw_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                raw_text += block.text

        # Clean up markdown wrapping if present
        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

        insights = json.loads(raw_text)

        # Cache the result
        _cache[key] = {"data": insights, "timestamp": time.time()}
        return insights

    except Exception as e:
        print(f"Ecosystem insights error: {e}")
        return _fallback_insights()


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
