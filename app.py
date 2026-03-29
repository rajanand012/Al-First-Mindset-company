"""Flask web application for AI-First Mindset Assessment Tool."""

import os
import traceback

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash

from database import init_db, save_assessment, get_assessment, get_company_history, get_all_assessments
from scorer import QUESTIONS, score_assessment, generate_recommendations

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/assess", methods=["GET", "POST"])
def assess():
    """Step 1: Company info form -> Step 2: Questionnaire."""
    if request.method == "GET":
        return redirect(url_for("index"))

    # Check if this is the company info submission or the questionnaire submission
    step = request.form.get("step", "company_info")

    if step == "company_info":
        company_name = request.form.get("company_name", "").strip()
        website_url = request.form.get("website_url", "").strip()
        industry_segment = request.form.get("industry_segment", "").strip()
        company_size = request.form.get("company_size", "").strip()

        if not company_name or not website_url:
            flash("Company name and website URL are required.", "error")
            return redirect(url_for("index"))

        return render_template(
            "questionnaire.html",
            questions=QUESTIONS,
            company_name=company_name,
            website_url=website_url,
            industry_segment=industry_segment,
            company_size=company_size,
        )

    elif step == "questionnaire":
        company_name = request.form.get("company_name", "").strip()
        website_url = request.form.get("website_url", "").strip()
        industry_segment = request.form.get("industry_segment", "").strip()
        company_size = request.form.get("company_size", "").strip()

        # Collect answers
        answers = {}
        for q in QUESTIONS:
            val = request.form.get(q["id"])
            if val is not None:
                answers[q["id"]] = int(val)

        if len(answers) < len(QUESTIONS):
            flash("Please answer all questions.", "error")
            return render_template(
                "questionnaire.html",
                questions=QUESTIONS,
                company_name=company_name,
                website_url=website_url,
                industry_segment=industry_segment,
                company_size=company_size,
            )

        try:
            # Step 1: Deterministic scoring
            result = score_assessment(
                company_name, website_url,
                industry_segment, company_size, answers
            )

            # Step 2: Generate AI recommendations via Claude API
            try:
                ai_output = generate_recommendations(result)
                result["recommendations"] = ai_output.get("recommendations", [])
                result["executive_summary"] = ai_output.get("executive_summary", "")
            except Exception as e:
                traceback.print_exc()
                result["recommendations"] = [
                    "Set up your ANTHROPIC_API_KEY in .env to receive AI-powered recommendations."
                ]
                result["executive_summary"] = ""

            # Step 3: Save to database
            assessment_id = save_assessment(result)
            return redirect(url_for("results", assessment_id=assessment_id))

        except Exception as e:
            traceback.print_exc()
            flash(f"Assessment failed: {str(e)}", "error")
            return redirect(url_for("index"))

    return redirect(url_for("index"))


@app.route("/results/<int:assessment_id>")
def results(assessment_id):
    assessment = get_assessment(assessment_id)
    if not assessment:
        flash("Assessment not found.", "error")
        return redirect(url_for("index"))

    history = get_company_history(assessment["company_name"])
    previous = history[1] if len(history) > 1 else None

    return render_template(
        "results.html",
        assessment=assessment,
        previous=previous,
    )


@app.route("/history")
def history():
    assessments = get_all_assessments()
    return render_template("history.html", assessments=assessments)


@app.route("/history/<company_name>")
def company_history(company_name):
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
