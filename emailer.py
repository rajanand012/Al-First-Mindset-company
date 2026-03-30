"""Send email notifications when an assessment is completed."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

load_dotenv()


def send_assessment_notification(result):
    """Send email notification about a completed assessment.

    Configure these in .env:
        SMTP_HOST=smtp.gmail.com
        SMTP_PORT=587
        SMTP_USER=your-email@gmail.com
        SMTP_PASSWORD=your-app-password
        NOTIFY_EMAIL=raj.anand@goodmanlantern.com
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    notify_email = os.getenv("NOTIFY_EMAIL", "raj.anand@goodmanlantern.com")

    if not all([smtp_host, smtp_user, smtp_password]):
        print("Email notification skipped: SMTP not configured in .env")
        return False

    subject = f"New AI-First Assessment: {result['company_name']} — {result['percentage']}% ({result['grade']})"

    # Build category rows
    cat_rows = ""
    for cat in result.get("category_scores", []):
        bar = "█" * cat["score"] + "░" * (5 - cat["score"])
        cat_rows += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{cat['name']}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: center; font-family: monospace;">{bar} {cat['score']}/5</td>
        </tr>"""

    # Build recommendations
    recs_html = ""
    for i, rec in enumerate(result.get("recommendations", []), 1):
        recs_html += f"<li style='margin-bottom: 6px;'>{rec}</li>"

    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #201600;">
        <div style="background: #207796; padding: 20px; text-align: center;">
            <h1 style="color: #f3af00; margin: 0; font-size: 22px;">New AI-First Mindset Assessment</h1>
        </div>

        <div style="padding: 24px; background: #ffffff;">
            <h2 style="color: #207796; margin-top: 0;">
                {result['company_name']}
                <span style="background: #f3af00; color: #201600; padding: 4px 12px; border-radius: 6px; font-size: 16px; margin-left: 8px;">
                    {result['grade']} — {result['percentage']}%
                </span>
            </h2>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
                <tr>
                    <td style="padding: 4px 0; color: #888; width: 120px;">Respondent:</td>
                    <td style="padding: 4px 0; font-weight: 600;">{result.get('respondent_name', '—')}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #888;">Email:</td>
                    <td style="padding: 4px 0;">{result.get('respondent_email', '—')}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #888;">Designation:</td>
                    <td style="padding: 4px 0;">{result.get('respondent_designation', '—')}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #888;">Website:</td>
                    <td style="padding: 4px 0;">{result.get('website_url', '—')}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #888;">Segment:</td>
                    <td style="padding: 4px 0;">{result.get('industry_segment', '—')}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #888;">Company Size:</td>
                    <td style="padding: 4px 0;">{result.get('company_size', '—')}</td>
                </tr>
            </table>

            <h3 style="color: #207796; border-bottom: 2px solid #dff3fa; padding-bottom: 8px;">Category Scores</h3>
            <table style="width: 100%; border-collapse: collapse;">
                {cat_rows}
            </table>

            {f'''
            <h3 style="color: #207796; border-bottom: 2px solid #dff3fa; padding-bottom: 8px; margin-top: 20px;">Recommendations</h3>
            <ol style="padding-left: 20px; color: #333;">{recs_html}</ol>
            ''' if recs_html else ''}

            {f'<p style="background: #dff3fa; padding: 12px; border-radius: 8px; color: #207796;"><strong>Executive Summary:</strong> {result.get("executive_summary", "")}</p>' if result.get('executive_summary') else ''}
        </div>

        <div style="background: #201600; padding: 16px; text-align: center;">
            <small style="color: #888;">AI-First Mindset Assessment Tool</small>
        </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = notify_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, notify_email, msg.as_string())
        print(f"Email notification sent to {notify_email}")
        return True
    except Exception as e:
        print(f"Email notification failed: {e}")
        return False
