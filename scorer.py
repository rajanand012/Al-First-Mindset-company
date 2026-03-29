"""Deterministic AI-First Adoption scoring + Claude API recommendations."""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

# --- 10 Self-Assessment Questions (scored 1-5) ---

QUESTIONS = [
    {
        "id": "ai_strategy",
        "name": "AI Strategy",
        "question": "Does your company have a formal AI or digital transformation strategy?",
        "options": [
            {"value": 1, "label": "No plans or discussions about AI"},
            {"value": 2, "label": "Informal discussions but no formal strategy"},
            {"value": 3, "label": "AI strategy in development or partially defined"},
            {"value": 4, "label": "Formal AI strategy with clear goals and timeline"},
            {"value": 5, "label": "Published AI-first strategy with executive sponsorship and measurable KPIs"},
        ],
    },
    {
        "id": "ai_production",
        "name": "AI in Production",
        "question": "How is AI used in your manufacturing or production processes?",
        "options": [
            {"value": 1, "label": "Not used at all"},
            {"value": 2, "label": "Exploring or piloting AI in one area"},
            {"value": 3, "label": "AI deployed in a few production processes (e.g., quality inspection or monitoring)"},
            {"value": 4, "label": "AI integrated across multiple production areas (predictive maintenance, optimization, etc.)"},
            {"value": 5, "label": "AI-driven across production — predictive maintenance, quality, process optimization, digital twins"},
        ],
    },
    {
        "id": "data_infrastructure",
        "name": "Data Infrastructure",
        "question": "How mature is your data collection and analytics infrastructure?",
        "options": [
            {"value": 1, "label": "Mostly manual processes and paper-based records"},
            {"value": 2, "label": "Basic digital data collection with spreadsheets or simple databases"},
            {"value": 3, "label": "Centralized data systems with dashboards and regular reporting"},
            {"value": 4, "label": "Advanced analytics platform with automated data pipelines"},
            {"value": 5, "label": "Real-time data platform with ML pipelines, data lakes, and AI-ready infrastructure"},
        ],
    },
    {
        "id": "ai_products",
        "name": "AI-Powered Products & Services",
        "question": "Do your products or services incorporate AI capabilities?",
        "options": [
            {"value": 1, "label": "No AI in our products or services"},
            {"value": 2, "label": "Exploring how to add AI features to existing products"},
            {"value": 3, "label": "One or two products have AI-enhanced features"},
            {"value": 4, "label": "AI is a significant differentiator in several products"},
            {"value": 5, "label": "AI is a core differentiator across our product line"},
        ],
    },
    {
        "id": "supply_chain",
        "name": "AI in Supply Chain & Operations",
        "question": "How is AI used in your supply chain and operations?",
        "options": [
            {"value": 1, "label": "No AI in supply chain or operations"},
            {"value": 2, "label": "Basic digitization of supply chain processes"},
            {"value": 3, "label": "Using AI for one area (e.g., demand forecasting or inventory)"},
            {"value": 4, "label": "AI-driven optimization in multiple supply chain areas"},
            {"value": 5, "label": "End-to-end AI-optimized supply chain — forecasting, logistics, inventory, and procurement"},
        ],
    },
    {
        "id": "ai_talent",
        "name": "AI Talent & Culture",
        "question": "Does your organization invest in AI skills and talent?",
        "options": [
            {"value": 1, "label": "No AI-specific roles or training"},
            {"value": 2, "label": "A few employees self-learning AI on the side"},
            {"value": 3, "label": "Some AI training programs or external AI consultants engaged"},
            {"value": 4, "label": "Dedicated AI team or department with ongoing hiring"},
            {"value": 5, "label": "AI leadership roles (e.g., Chief AI Officer), company-wide AI training, and active AI hiring"},
        ],
    },
    {
        "id": "ai_budget",
        "name": "AI Budget & Investment",
        "question": "What level of investment is allocated to AI initiatives?",
        "options": [
            {"value": 1, "label": "No dedicated AI budget"},
            {"value": 2, "label": "Small experimental budget within IT"},
            {"value": 3, "label": "Defined AI budget for specific projects"},
            {"value": 4, "label": "Significant AI budget with multi-year commitment"},
            {"value": 5, "label": "Major AI investment with clear ROI tracking and board-level visibility"},
        ],
    },
    {
        "id": "customer_experience",
        "name": "AI in Customer Experience",
        "question": "How does AI enhance your customer interactions?",
        "options": [
            {"value": 1, "label": "No AI in customer-facing processes"},
            {"value": 2, "label": "Basic automation (e.g., auto-reply emails)"},
            {"value": 3, "label": "AI chatbot or one AI-powered customer touchpoint"},
            {"value": 4, "label": "Multiple AI touchpoints — personalization, smart support, recommendations"},
            {"value": 5, "label": "Deeply personalized, AI-driven customer experience across all channels"},
        ],
    },
    {
        "id": "ai_governance",
        "name": "Responsible AI & Governance",
        "question": "Do you have responsible AI practices and governance in place?",
        "options": [
            {"value": 1, "label": "AI ethics not yet considered"},
            {"value": 2, "label": "Aware of AI ethics but no formal practices"},
            {"value": 3, "label": "Some data privacy and AI usage guidelines in place"},
            {"value": 4, "label": "Formal responsible AI framework with documented guidelines"},
            {"value": 5, "label": "Comprehensive AI governance — ethics board, regular audits, bias monitoring, transparency reports"},
        ],
    },
    {
        "id": "innovation_rd",
        "name": "AI Innovation & R&D",
        "question": "How active is AI in your R&D and innovation pipeline?",
        "options": [
            {"value": 1, "label": "No AI involvement in R&D"},
            {"value": 2, "label": "Exploring AI tools for R&D tasks"},
            {"value": 3, "label": "AI used in some R&D projects or prototyping"},
            {"value": 4, "label": "Active AI R&D program with measurable outcomes"},
            {"value": 5, "label": "AI-driven innovation lab, patents, or published research — AI is central to our R&D"},
        ],
    },
]

GRADE_THRESHOLDS = [
    (90, "A+", "AI-First Leader"),
    (80, "A", "AI-Advanced"),
    (70, "B+", "AI-Proficient"),
    (60, "B", "AI-Developing"),
    (50, "C+", "AI-Aware"),
    (40, "C", "AI-Exploring"),
    (30, "D", "AI-Beginner"),
    (0, "F", "AI-Absent"),
]


def get_grade(percentage):
    for threshold, grade, label in GRADE_THRESHOLDS:
        if percentage >= threshold:
            return grade, label
    return "F", "AI-Absent"


def score_assessment(company_name, website_url, industry_segment,
                     company_size, answers):
    """Score deterministically from questionnaire answers. Returns result dict.

    answers: dict mapping question id -> selected value (1-5)
    """
    question_lookup = {q["id"]: q for q in QUESTIONS}
    category_scores = []
    total_score = 0

    for q in QUESTIONS:
        score = max(1, min(5, int(answers.get(q["id"], 1))))
        total_score += score
        # Find the label for the selected score
        selected_label = ""
        for opt in q["options"]:
            if opt["value"] == score:
                selected_label = opt["label"]
                break
        category_scores.append({
            "category_id": q["id"],
            "name": q["name"],
            "score": score,
            "max_score": 5,
            "selected_label": selected_label,
        })

    max_score = len(QUESTIONS) * 5
    percentage = round((total_score / max_score) * 100, 1)
    grade, grade_label = get_grade(percentage)

    return {
        "company_name": company_name,
        "website_url": website_url,
        "industry_segment": industry_segment,
        "company_size": company_size,
        "overall_score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "grade": grade,
        "grade_label": grade_label,
        "category_scores": category_scores,
    }


def generate_recommendations(result):
    """Use Claude API (temperature=0) to generate tailored recommendations."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=api_key)

    # Build context from scores
    scores_summary = "\n".join(
        f"- {cat['name']}: {cat['score']}/5 — \"{cat['selected_label']}\""
        for cat in result["category_scores"]
    )

    # Identify weakest areas
    sorted_cats = sorted(result["category_scores"], key=lambda c: c["score"])
    weakest = sorted_cats[:3]
    weakest_text = ", ".join(c["name"] for c in weakest)

    prompt = f"""You are an AI strategy advisor for manufacturing companies.

## Company Profile
- **Company:** {result['company_name']}
- **Website:** {result['website_url']}
- **Industry:** {result.get('industry_segment') or 'Manufacturing (general)'}
- **Size:** {result.get('company_size') or 'Not specified'}
- **Overall AI Adoption Score:** {result['percentage']}% (Grade: {result['grade']} — {result['grade_label']})

## Self-Assessment Scores
{scores_summary}

## Weakest Areas: {weakest_text}

## Your Task
Based on this manufacturer's self-assessment, provide:
1. A 2-3 sentence executive summary of their AI maturity
2. Exactly 5 specific, actionable recommendations prioritized by impact — focus on their weakest areas and their specific industry segment

Respond with ONLY a valid JSON object (no markdown, no explanation):

{{
  "executive_summary": "<2-3 sentence summary>",
  "recommendations": [
    "<recommendation 1 — most impactful>",
    "<recommendation 2>",
    "<recommendation 3>",
    "<recommendation 4>",
    "<recommendation 5>"
  ]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]

    return json.loads(raw)
