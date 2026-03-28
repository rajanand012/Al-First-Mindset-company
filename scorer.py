"""Structured AI-First Mindset scoring engine using Claude API (temperature 0)."""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

# --- Scoring Rubric ---
# 10 categories, each scored 1-5. Max total = 50, scaled to 100%.

SCORING_CATEGORIES = [
    {
        "id": "ai_presence",
        "name": "AI Presence on Website",
        "question": "Does the company prominently mention AI, machine learning, or intelligent automation on their website (homepage, about page, etc.)?",
        "scoring": {
            1: "No mention of AI anywhere",
            2: "Brief or passing mention of AI",
            3: "AI mentioned in multiple places but not central",
            4: "AI featured prominently as a key part of the business",
            5: "AI is core to their identity and messaging throughout",
        },
    },
    {
        "id": "ai_products",
        "name": "AI-Powered Products & Services",
        "question": "Does the company offer products or services that are powered by or enhanced with AI/ML?",
        "scoring": {
            1: "No AI-powered offerings visible",
            2: "One product with minor AI features",
            3: "Several products with AI features",
            4: "AI-powered products are a significant part of their portfolio",
            5: "Their core product line is built around AI capabilities",
        },
    },
    {
        "id": "smart_manufacturing",
        "name": "Smart Manufacturing & Industry 4.0",
        "question": "Is there evidence of AI/ML in their manufacturing processes (predictive maintenance, quality inspection, process optimization, digital twins, IoT)?",
        "scoring": {
            1: "No evidence of smart manufacturing",
            2: "Basic automation mentioned but no AI/ML",
            3: "Some AI/ML in manufacturing processes",
            4: "Significant AI integration across manufacturing",
            5: "Fully AI-driven smart factory / Industry 4.0 leader",
        },
    },
    {
        "id": "data_strategy",
        "name": "Data Strategy & Analytics",
        "question": "Does the company show evidence of a data-driven approach (analytics platforms, data collection, dashboards, data-informed decisions)?",
        "scoring": {
            1: "No evidence of data strategy",
            2: "Basic reporting or analytics mentioned",
            3: "Clear data analytics capabilities described",
            4: "Advanced analytics and data platforms in use",
            5: "Comprehensive data strategy with real-time analytics and AI-driven insights",
        },
    },
    {
        "id": "ai_talent",
        "name": "AI Talent & Team",
        "question": "Does the company appear to invest in AI talent (AI/ML job listings, dedicated AI teams, AI partnerships, AI leadership roles)?",
        "scoring": {
            1: "No evidence of AI talent investment",
            2: "General tech roles, no AI-specific positions",
            3: "Some AI/ML roles or partnerships mentioned",
            4: "Dedicated AI team or department visible",
            5: "Strong AI leadership (Chief AI Officer, AI labs, major AI partnerships)",
        },
    },
    {
        "id": "innovation_rd",
        "name": "AI Innovation & R&D",
        "question": "Is there evidence of AI research, patents, innovation labs, or R&D investment in AI/ML?",
        "scoring": {
            1: "No evidence of AI R&D",
            2: "General R&D mentioned but not AI-specific",
            3: "Some AI research or innovation projects",
            4: "Active AI R&D program with published results",
            5: "Industry-leading AI research with patents, publications, or innovation labs",
        },
    },
    {
        "id": "customer_experience",
        "name": "AI in Customer Experience",
        "question": "Does the company use AI to enhance customer experience (chatbots, personalization, AI-powered support, recommendation engines)?",
        "scoring": {
            1: "No AI in customer-facing interactions",
            2: "Basic chatbot or simple automation",
            3: "AI-enhanced support or personalization visible",
            4: "Multiple AI touchpoints in the customer journey",
            5: "Deeply personalized, AI-driven customer experience throughout",
        },
    },
    {
        "id": "supply_chain",
        "name": "AI in Supply Chain & Operations",
        "question": "Is there evidence of AI/ML in supply chain management, demand forecasting, logistics optimization, or inventory management?",
        "scoring": {
            1: "No evidence of AI in supply chain",
            2: "Basic supply chain digitization only",
            3: "Some AI applications in supply chain",
            4: "AI-driven supply chain optimization in multiple areas",
            5: "End-to-end AI-optimized supply chain and operations",
        },
    },
    {
        "id": "ai_strategy",
        "name": "AI Strategy & Vision",
        "question": "Does the company communicate a clear AI strategy, digital transformation roadmap, or AI-first vision?",
        "scoring": {
            1: "No AI strategy communicated",
            2: "Vague mention of digital transformation",
            3: "Some strategic AI goals mentioned",
            4: "Clear AI strategy with specific goals and timeline",
            5: "Published AI-first strategy with measurable objectives and leadership commitment",
        },
    },
    {
        "id": "ai_ethics",
        "name": "Responsible AI & Governance",
        "question": "Does the company address AI ethics, responsible AI practices, AI governance, transparency, or bias mitigation?",
        "scoring": {
            1: "No mention of AI ethics or governance",
            2: "Generic corporate responsibility mentioned",
            3: "Some AI ethics or data privacy practices noted",
            4: "Clear responsible AI framework or guidelines",
            5: "Comprehensive AI governance with published principles, audits, and oversight",
        },
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


def build_scoring_prompt(company_name, website_url, web_content,
                         industry_segment="", company_size=""):
    """Build the structured prompt for Claude to score each category."""

    rubric_text = ""
    for i, cat in enumerate(SCORING_CATEGORIES, 1):
        rubric_text += f"\n### Category {i}: {cat['name']}\n"
        rubric_text += f"**Question:** {cat['question']}\n"
        rubric_text += "**Scoring Guide:**\n"
        for score, desc in cat["scoring"].items():
            rubric_text += f"  {score} = {desc}\n"

    prompt = f"""You are an expert analyst evaluating a manufacturing company's AI-First Mindset maturity.

## Company Information
- **Company Name:** {company_name}
- **Website:** {website_url}
- **Industry Segment:** {industry_segment or 'Manufacturing (general)'}
- **Company Size:** {company_size or 'Not specified'}

## Website Content (scraped from their site)
<website_content>
{web_content[:80000]}
</website_content>

## Your Task
Score this company across exactly 10 categories using ONLY the evidence found in the website content above. Be objective and evidence-based. If something is not mentioned on their website, score it low — do not assume capabilities that are not documented.

## Scoring Rubric
{rubric_text}

## Required Output Format
You MUST respond with ONLY a valid JSON object in this exact structure (no markdown, no explanation, just JSON):

{{
  "scores": [
    {{
      "category_id": "ai_presence",
      "score": <1-5>,
      "evidence": "<brief quote or description of evidence found, or 'No evidence found'>"
    }},
    {{
      "category_id": "ai_products",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }},
    {{
      "category_id": "smart_manufacturing",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }},
    {{
      "category_id": "data_strategy",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }},
    {{
      "category_id": "ai_talent",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }},
    {{
      "category_id": "innovation_rd",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }},
    {{
      "category_id": "customer_experience",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }},
    {{
      "category_id": "supply_chain",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }},
    {{
      "category_id": "ai_strategy",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }},
    {{
      "category_id": "ai_ethics",
      "score": <1-5>,
      "evidence": "<brief evidence>"
    }}
  ],
  "top_recommendations": [
    "<recommendation 1: most impactful action to improve AI maturity>",
    "<recommendation 2>",
    "<recommendation 3>",
    "<recommendation 4>",
    "<recommendation 5>"
  ],
  "executive_summary": "<2-3 sentence summary of the company's AI-First Mindset maturity>"
}}"""

    return prompt


def run_assessment(company_name, website_url, web_content,
                   industry_segment="", company_size=""):
    """Call Claude API with temperature=0 to score the company. Returns full result dict."""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = build_scoring_prompt(
        company_name, website_url, web_content,
        industry_segment, company_size
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_response = message.content[0].text.strip()

    # Parse JSON — handle possible markdown wrapping
    if raw_response.startswith("```"):
        raw_response = raw_response.split("\n", 1)[1]
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3]

    result = json.loads(raw_response)

    # Build category scores with names
    category_scores = []
    total_score = 0
    cat_lookup = {c["id"]: c for c in SCORING_CATEGORIES}

    for item in result["scores"]:
        cat = cat_lookup.get(item["category_id"], {})
        score = max(1, min(5, int(item["score"])))
        total_score += score
        category_scores.append({
            "category_id": item["category_id"],
            "name": cat.get("name", item["category_id"]),
            "score": score,
            "max_score": 5,
            "evidence": item.get("evidence", ""),
        })

    max_score = len(SCORING_CATEGORIES) * 5
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
        "recommendations": result.get("top_recommendations", []),
        "executive_summary": result.get("executive_summary", ""),
    }
