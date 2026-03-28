"""Flask web application for AI-First Mindset Assessment Tool."""

import os
import traceback

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash

from database import init_db, save_assessment, get_assessment, get_company_history, get_all_assessments
from scraper import fetch_website
from scorer import run_assessment, SCORING_CATEGORIES

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# Initialize database on startup
init_db()


@app.route("/")
def index():
    """Landing page with the assessment form."""
    return render_template("index.html")


@app.route("/assess", methods=["POST"])
def assess():
    """Run an AI-First Mindset assessment."""
    company_name = request.form.get("company_name", "").strip()
    website_url = request.form.get("website_url", "").strip()
    industry_segment = request.form.get("industry_segment", "").strip()
    company_size = request.form.get("company_size", "").strip()

    if not company_name or not website_url:
        flash("Company name and website URL are required.", "error")
        return redirect(url_for("index"))

    try:
        # Step 1: Fetch website content (cached for 7 days)
        web_data = fetch_website(website_url)

        # Step 2: Run structured scoring via Claude API (temperature=0)
        result = run_assessment(
            company_name=company_name,
            website_url=website_url,
            web_content=web_data["text"],
            industry_segment=industry_segment,
            company_size=company_size,
        )
        result["web_content_hash"] = web_data["content_hash"]
        result["from_cache"] = web_data.get("from_cache", False)

        # Step 3: Save to database
        assessment_id = save_assessment(result)

        return redirect(url_for("results", assessment_id=assessment_id))

    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("index"))
    except Exception as e:
        traceback.print_exc()
        flash(f"Assessment failed: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/results/<int:assessment_id>")
def results(assessment_id):
    """Display assessment results."""
    assessment = get_assessment(assessment_id)
    if not assessment:
        flash("Assessment not found.", "error")
        return redirect(url_for("index"))

    # Get previous assessments for comparison
    history = get_company_history(assessment["company_name"])
    previous = history[1] if len(history) > 1 else None

    return render_template(
        "results.html",
        assessment=assessment,
        previous=previous,
        categories=SCORING_CATEGORIES,
    )


@app.route("/history")
def history():
    """Show all past assessments."""
    assessments = get_all_assessments()
    return render_template("history.html", assessments=assessments)


@app.route("/history/<company_name>")
def company_history(company_name):
    """Show assessment history for a specific company."""
    assessments = get_company_history(company_name)
    if not assessments:
        flash("No assessments found for that company.", "error")
        return redirect(url_for("history"))
    return render_template(
        "company_history.html",
        company_name=company_name,
        assessments=assessments,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
