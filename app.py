"""Flask web application for AI-First Mindset Assessment Tool."""

import os
import traceback

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from database import init_db, save_assessment, get_assessment, get_all_assessments
from scorer import QUESTIONS, score_assessment, generate_recommendations
from ecosystem_insights import fetch_ecosystem_insights
from emailer import send_assessment_notification

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
        respondent_name = request.form.get("respondent_name", "").strip()
        respondent_email = request.form.get("respondent_email", "").strip()
        respondent_designation = request.form.get("respondent_designation", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website_url = request.form.get("website_url", "").strip()
        industry_segment = request.form.get("industry_segment", "").strip()
        company_size = request.form.get("company_size", "").strip()

        if not company_name or not website_url or not respondent_name or not respondent_email:
            flash("Name, email, company name and website URL are required.", "error")
            return redirect(url_for("index"))

        return render_template(
            "questionnaire.html",
            questions=QUESTIONS,
            respondent_name=respondent_name,
            respondent_email=respondent_email,
            respondent_designation=respondent_designation,
            company_name=company_name,
            website_url=website_url,
            industry_segment=industry_segment,
            company_size=company_size,
        )

    elif step == "questionnaire":
        respondent_name = request.form.get("respondent_name", "").strip()
        respondent_email = request.form.get("respondent_email", "").strip()
        respondent_designation = request.form.get("respondent_designation", "").strip()
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

            result["respondent_name"] = respondent_name
            result["respondent_email"] = respondent_email
            result["respondent_designation"] = respondent_designation

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

            # Step 4: Send email notification
            try:
                send_assessment_notification(result)
            except Exception:
                traceback.print_exc()

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

    return render_template(
        "results.html",
        assessment=assessment,
        previous=None,
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    admin_password = os.getenv("ADMIN_PASSWORD", "aifmos2026")

    if request.method == "POST":
        if request.form.get("password") == admin_password:
            from flask import session
            session["admin_auth"] = True
            return redirect(url_for("admin"))
        else:
            flash("Incorrect password.", "error")
            return render_template("admin_login.html")

    from flask import session
    if not session.get("admin_auth"):
        return render_template("admin_login.html")

    assessments = get_all_assessments()
    return render_template("admin.html", assessments=assessments)


@app.route("/api/ecosystem-insights", methods=["POST"])
def ecosystem_insights():
    """Async endpoint: fetch AI ecosystem insights for the company's industry."""
    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "").strip()
    industry_segment = data.get("industry_segment", "").strip()

    if not company_name:
        return jsonify([]), 400

    insights = fetch_ecosystem_insights(company_name, industry_segment)
    return jsonify(insights)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
