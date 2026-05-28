import os
import re
from jinja2 import Template
from core.utils import setup_logger
from config import OUTPUT_REPORTS_DIR, OUTPUT_AUDITS_DIR

logger = setup_logger("ai.report_generator")

class ReportGenerator:
    @staticmethod
    def _format_list(values, empty="None detected"):
        values = values or []
        if not values:
            return f"- {empty}"
        return "\n".join([f"- {value}" for value in values])

    @staticmethod
    def _format_hours(values):
        values = values or []
        day_re = r"\b(mon|monday|tue|tues|tuesday|wed|wednesday|thu|thur|thurs|thursday|fri|friday|sat|saturday|sun|sunday|daily|everyday)\b"
        time_re = r"(\d{1,2}:\d{2}\s*(am|pm|a\.m\.|p\.m\.)?|\d{1,2}\s*(am|pm|a\.m\.|p\.m\.)|closed|open 24)"
        filtered = [
            value for value in values
            if isinstance(value, str) and re.search(day_re, value, re.I) and re.search(time_re, value, re.I)
        ]
        return ReportGenerator._format_list(filtered)

    @staticmethod
    def generate_evidence_markdown(data, evidence):
        """Build a manager-readable evidence report showing what each output used."""
        logger.info("Generating manager evidence report...")

        name = data.get("business_name") or "Business"
        clean_name = name.split('|')[0].split('-')[0].strip()
        settings = evidence.get("crawler_settings", {})
        pages = evidence.get("pages", [])
        scores = data.get("scores", {}).get("scores", {})
        outreach = data.get("outreach", {})

        page_sections = []
        for idx, page in enumerate(pages, start=1):
            ctas = [f"{cta.get('text', '')} -> {cta.get('href', '')}".strip(" ->") for cta in page.get("ctas", [])]
            forms = [
                f"{form.get('input_count', 0)} fields ({', '.join(form.get('fields', [])[:6])})"
                for form in page.get("forms", [])
            ]
            summary = page.get("page_summary", {})
            paragraphs = summary.get("paragraphs", [])
            page_sections.append(f"""### {idx}. {page.get('url', 'Unknown URL')}

**Title:** {page.get('title') or 'None'}
**Meta Description:** {page.get('meta_description') or 'None'}
**H1s:** {", ".join(summary.get('h1', [])) or 'None'}

**Extracted Emails**
{ReportGenerator._format_list(page.get('emails', []))}

**Extracted Phones**
{ReportGenerator._format_list(page.get('phone_numbers', []))}

**Extracted Addresses**
{ReportGenerator._format_list(page.get('addresses', []))}

**Business Hours**
{ReportGenerator._format_hours(page.get('business_hours', []))}

**Social Links**
{ReportGenerator._format_list([f"{k}: {v}" for k, v in page.get('social_links', {}).items()])}

**Conversion Actions / CTAs**
{ReportGenerator._format_list(ctas)}

**Forms Detected**
{ReportGenerator._format_list(forms)}

**Visible Copy Samples Used For Context**
{ReportGenerator._format_list(paragraphs, "No paragraph samples captured")}
""")

        md_content = f"""# Manager Evidence Report

**Target Business:** {clean_name}
**Website URL:** {data.get('website_url', 'N/A')}
**Pages Crawled:** {len(pages)}

This file explains what the audit and outreach drafts are based on. Crawl limits and rate settings are unchanged.

---

## Crawl Settings Used

- **Max Depth:** {settings.get('max_depth')}
- **Max Pages Per Domain:** {settings.get('max_pages_per_domain')}
- **Concurrency Limit:** {settings.get('concurrency_limit')}
- **Rate Limit Seconds:** {settings.get('rate_limit_seconds')}
- **Respect Robots.txt:** {settings.get('respect_robots_txt')}

---

## Final Extracted Company Data

**Emails**
{ReportGenerator._format_list(data.get('emails', []))}

**Phone Numbers**
{ReportGenerator._format_list(data.get('phone_numbers', []))}

**Addresses**
{ReportGenerator._format_list(data.get('addresses', []))}

**Business Hours**
{ReportGenerator._format_hours(data.get('business_hours', []))}

**Social Links**
{ReportGenerator._format_list([f"{k}: {v}" for k, v in data.get('social_links', {}).items()])}

**Tech Stack**
{ReportGenerator._format_list(data.get('tech_stack', []))}

---

## Score Basis

- **Overall Opportunity Score:** {data.get('scores', {}).get('overall', 'N/A')}/100
- **SEO:** {scores.get('seo', 'N/A')}/100 based on title, meta description, headings, canonical tag, image alt coverage, keywords, and readability.
- **Performance:** {scores.get('performance', 'N/A')}/100 based on Lighthouse when available, otherwise browser load timing fallback.
- **Conversion:** {scores.get('conversion', 'N/A')}/100 based on CTAs, booking paths, forms, chat widgets, testimonials, and trust signals.
- **Trust:** {scores.get('trust', 'N/A')}/100 based on detected reviews/testimonials and reputation signals.
- **Social:** {scores.get('social', 'N/A')}/100 based on detected social links and brand consistency.
- **Growth:** {scores.get('growth', 'N/A')}/100 based on careers/hiring signals.

---

## Recommendations Used

{ReportGenerator._format_list(data.get('seo', {}).get('recommendations', []) + data.get('performance', {}).get('recommendations', []) + data.get('cro', {}).get('recommendations', []), "No recommendations generated")}

---

## Outreach Draft Basis

The email, WhatsApp, and SMS drafts use the public company data above plus the score findings and recommendations.

**Email Draft**
```text
{outreach.get('email') or data.get('outreach_email', '')}
```

**WhatsApp Draft**
```text
{outreach.get('whatsapp', '')}
```

**SMS Draft**
```text
{outreach.get('sms', '')}
```

---

## Page-by-Page Evidence

{chr(10).join(page_sections) if page_sections else "No page evidence captured."}
"""
        return md_content

    @staticmethod
    def generate_markdown(data):
        """Build an executive Markdown audit report."""
        logger.info("Generating Markdown audit report...")
        
        name = data.get("business_name") or "Business"
        clean_name = name.split('|')[0].split('-')[0].strip()
        url = data.get("website_url") or "N/A"
        desc = data.get("description") or "No description parsed."
        
        scores_data = data.get("scores", {})
        overall_score = scores_data.get("overall", 70)
        opp_tier = scores_data.get("opportunity_tier", "Medium")
        lead_qual = scores_data.get("lead_quality", "Warm Lead")
        scores = scores_data.get("scores", {})
        
        swot = data.get("swot", {})
        emails = ", ".join(data.get("emails", [])) or "None detected"
        phones = ", ".join(data.get("phone_numbers", [])) or "None detected"
        addresses = "; ".join(data.get("addresses", [])) or "None detected"
        socials = ", ".join([f"{k}: {v}" for k, v in data.get("social_links", {}).items()]) or "None detected"
        
        md_content = f"""# Business Health & Lead Intelligence Report

**Target Business:** {clean_name}
**Website URL:** {url}
**Opportunity Tier:** {opp_tier} ({lead_qual})
**Overall Opportunity Score:** {overall_score}/100

---

## Executive Summary
{data.get('summary', '')}

---

## Operations & Setup Details
- **Description:** {desc}
- **Contact Emails:** {emails}
- **Phone Numbers:** {phones}
- **Physical Addresses:** {addresses}
- **Social Media Links:** {socials}
- **Tech Stack Detected:** {", ".join(data.get('tech_stack', [])) or "None"}

---

## Intelligence Health Scores
| Category | Score / 100 | Recommendation / Finding |
| :--- | :---: | :--- |
| **SEO Score** | {scores.get('seo', 70)}/100 | {len(data.get('seo', {}).get('recommendations', []))} suggestions |
| **Performance Score** | {scores.get('performance', 70)}/100 | {len(data.get('performance', {}).get('recommendations', []))} speed opportunities |
| **Conversion (CRO) Score** | {scores.get('conversion', 70)}/100 | {len(data.get('cro', {}).get('recommendations', []))} friction elements |
| **Reputation (Trust) Score** | {scores.get('trust', 75)}/100 | Based on customer testimonials |
| **Social Presence Score** | {scores.get('social', 50)}/100 | Active on {len(data.get('social_links', {}))} networks |
| **Growth/Hiring Score** | {scores.get('growth', 40)}/100 | Hiring status: {data.get('hiring', {}).get('growth_focus', 'Stable')} |

---

## SWOT Analysis

### Strengths
{chr(10).join([f"- {s}" for s in swot.get('strengths', [])])}

### Weaknesses
{chr(10).join([f"- {w}" for w in swot.get('weaknesses', [])])}

### Opportunities
{chr(10).join([f"- {o}" for o in swot.get('opportunities', [])])}

### Threats
{chr(10).join([f"- {t}" for t in swot.get('threats', [])])}

---

## Actionable Recommendations
{chr(10).join([f"- {r}" for r in data.get('seo', {}).get('recommendations', []) + data.get('performance', {}).get('recommendations', []) + data.get('cro', {}).get('recommendations', [])])}

---

## Personalized Outreach Template
```text
{data.get('outreach_email', '')}
```

## WhatsApp / SMS Drafts
```text
WhatsApp:
{data.get('outreach', {}).get('whatsapp', '')}

SMS:
{data.get('outreach', {}).get('sms', '')}
```
"""
        return md_content

    @staticmethod
    def generate_html(data, output_path, screenshot_path=None):
        """Generate a premium glassmorphic HTML audit dashboard."""
        logger.info(f"Generating HTML report at {output_path}...")
        
        name = data.get("business_name") or "Business"
        clean_name = name.split('|')[0].split('-')[0].strip()
        url = data.get("website_url") or "N/A"
        desc = data.get("description") or "No description parsed."
        
        scores_data = data.get("scores", {})
        overall_score = scores_data.get("overall", 70)
        opp_tier = scores_data.get("opportunity_tier", "Medium")
        lead_qual = scores_data.get("lead_quality", "Warm Lead")
        scores = scores_data.get("scores", {})
        
        swot = data.get("swot", {})
        
        # Format lists
        emails = data.get("emails", [])
        phones = data.get("phone_numbers", [])
        addresses = data.get("addresses", [])
        socials = data.get("social_links", {})
        tech_stack = data.get("tech_stack", [])
        
        recs = (
            data.get('seo', {}).get('recommendations', []) +
            data.get('performance', {}).get('recommendations', []) +
            data.get('cro', {}).get('recommendations', [])
        )
        
        # HTML Template string
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Intelligence Audit - {{ clean_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4f46e5;
            --primary-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            --background: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--background);
            color: var(--text-main);
            line-height: 1.6;
            padding: 2rem;
            min-height: 100vh;
        }
        
        h1, h2, h3, .brand {
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* Glassmorphism Header */
        header {
            background: var(--primary-gradient);
            border-radius: 16px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(79, 70, 229, 0.2);
            position: relative;
            overflow: hidden;
        }
        
        header::after {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 300px;
            height: 300px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            filter: blur(50px);
        }
        
        .header-content {
            position: relative;
            z-index: 2;
        }
        
        .header-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
            padding-top: 1rem;
        }
        
        .badge {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.2);
        }
        
        /* Main Scores Grid */
        .scores-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .score-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            backdrop-filter: blur(10px);
            transition: transform 0.2s;
        }
        
        .score-card:hover {
            transform: translateY(-5px);
        }
        
        .score-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary);
            margin: 0.5rem 0;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .score-label {
            font-size: 0.9rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Content Split Layout */
        .split-layout {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        @media (max-width: 900px) {
            .split-layout {
                grid-template-columns: 1fr;
            }
        }
        
        .panel {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 2rem;
            backdrop-filter: blur(10px);
            margin-bottom: 2rem;
        }
        
        .panel h2 {
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 0.5rem;
        }
        
        /* SWOT Cards Grid */
        .swot-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        
        @media (max-width: 600px) {
            .swot-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .swot-box {
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 4px solid var(--primary);
            background: rgba(255, 255, 255, 0.02);
        }
        
        .swot-box.strengths { border-left-color: var(--success); }
        .swot-box.weaknesses { border-left-color: var(--danger); }
        .swot-box.opportunities { border-left-color: var(--warning); }
        .swot-box.threats { border-left-color: #6366f1; }
        
        .swot-box h3 {
            margin-bottom: 0.8rem;
            font-size: 1.1rem;
        }
        
        .swot-box ul {
            list-style: none;
            padding-left: 0;
        }
        
        .swot-box li {
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            color: var(--text-muted);
            position: relative;
            padding-left: 1.2rem;
        }
        
        .swot-box li::before {
            content: '•';
            position: absolute;
            left: 0;
            color: var(--primary);
            font-weight: bold;
        }
        
        /* List Styling */
        .info-list {
            list-style: none;
        }
        
        .info-list li {
            padding: 0.8rem 0;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            justify-content: space-between;
            font-size: 0.95rem;
        }
        
        .info-list li span:first-child {
            color: var(--text-muted);
            font-weight: 500;
        }
        
        .tech-tag {
            display: inline-block;
            background: rgba(79, 70, 229, 0.15);
            border: 1px solid rgba(79, 70, 229, 0.3);
            color: #a5b4fc;
            padding: 0.3rem 0.6rem;
            border-radius: 6px;
            font-size: 0.8rem;
            margin: 0.2rem;
        }
        
        /* Outreach Section */
        .outreach-box {
            background: #1e293b;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            font-family: 'Courier New', Courier, monospace;
            white-space: pre-wrap;
            color: #e2e8f0;
            font-size: 0.9rem;
            max-height: 400px;
            overflow-y: auto;
            border-left: 4px solid var(--success);
        }
        
        /* Screenshot image section */
        .screenshot-container {
            margin-top: 1.5rem;
            text-align: center;
        }
        
        .screenshot-container img {
            max-width: 100%;
            border-radius: 12px;
            border: 1px solid var(--card-border);
            box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">{{ opp_tier }} Opportunity</span>
                <h1 style="font-size: 2.5rem; margin: 0.5rem 0;">{{ clean_name }}</h1>
                <p style="color: rgba(255, 255, 255, 0.8); font-size: 1.1rem;">{{ desc }}</p>
                <div class="header-meta">
                    <span>Website: <a href="{{ url }}" target="_blank" style="color: white; font-weight: bold;">{{ url }}</a></span>
                    <span class="badge">Overall Health Score: {{ overall_score }}/100</span>
                </div>
            </div>
        </header>
        
        <div class="scores-grid">
            <div class="score-card">
                <div class="score-label">SEO</div>
                <div class="score-value">{{ scores.get('seo', 70) }}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Performance</div>
                <div class="score-value">{{ scores.get('performance', 70) }}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Conversion</div>
                <div class="score-value">{{ scores.get('conversion', 70) }}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Trust</div>
                <div class="score-value">{{ scores.get('trust', 75) }}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Social</div>
                <div class="score-value">{{ scores.get('social', 50) }}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Growth</div>
                <div class="score-value">{{ scores.get('growth', 40) }}</div>
            </div>
        </div>
        
        <div class="split-layout">
            <div class="main-column">
                <div class="panel">
                    <h2>Executive Summary</h2>
                    <p style="font-size: 1.1rem; color: #cbd5e1;">{{ data.get('summary', '') }}</p>
                </div>
                
                <div class="panel">
                    <h2>SWOT Analysis</h2>
                    <div class="swot-grid">
                        <div class="swot-box strengths">
                            <h3>Strengths</h3>
                            <ul>
                                {% for s in swot.get('strengths', []) %}
                                <li>{{ s }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                        <div class="swot-box weaknesses">
                            <h3>Weaknesses</h3>
                            <ul>
                                {% for w in swot.get('weaknesses', []) %}
                                <li>{{ w }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                        <div class="swot-box opportunities">
                            <h3>Opportunities</h3>
                            <ul>
                                {% for o in swot.get('opportunities', []) %}
                                <li>{{ o }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                        <div class="swot-box threats">
                            <h3>Threats</h3>
                            <ul>
                                {% for t in swot.get('threats', []) %}
                                <li>{{ t }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                </div>
                
                <div class="panel">
                    <h2>Personalized Sales Outreach Email</h2>
                    <div class="outreach-box">{{ data.get('outreach_email', '') }}</div>
                </div>
            </div>
            
            <div class="sidebar-column">
                <div class="panel">
                    <h2>Operational Contact</h2>
                    <ul class="info-list">
                        <li>
                            <span>Emails</span>
                            <span style="text-align: right;">
                                {% for email in emails %}
                                {{ email }}<br/>
                                {% else %}
                                None found
                                {% endfor %}
                            </span>
                        </li>
                        <li>
                            <span>Phones</span>
                            <span style="text-align: right;">
                                {% for phone in phones %}
                                {{ phone }}<br/>
                                {% else %}
                                None found
                                {% endfor %}
                            </span>
                        </li>
                        <li>
                            <span>Addresses</span>
                            <span style="text-align: right; font-size: 0.8rem; max-width: 150px;">
                                {% for addr in addresses %}
                                {{ addr }}<br/><br/>
                                {% else %}
                                None found
                                {% endfor %}
                            </span>
                        </li>
                    </ul>
                </div>
                
                <div class="panel">
                    <h2>Marketing Stack</h2>
                    <div style="margin-top: 1rem;">
                        {% for tech in tech_stack %}
                        <span class="tech-tag">{{ tech }}</span>
                        {% else %}
                        <span style="color: var(--text-muted);">No core widgets or trackers detected</span>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="panel">
                    <h2>Actionable Audits</h2>
                    <ul class="info-list" style="max-height: 300px; overflow-y: auto;">
                        {% for rec in recs %}
                        <li style="flex-direction: column;">
                            <span style="color: var(--warning); font-size: 0.85rem; font-weight: bold;">Recommendation</span>
                            <span style="font-size: 0.9rem; margin-top: 0.2rem;">{{ rec }}</span>
                        </li>
                        {% else %}
                        <li>No adjustments needed</li>
                        {% endfor %}
                    </ul>
                </div>
                
                {% if screenshot_path %}
                <div class="panel">
                    <h2>Visual Layout</h2>
                    <div class="screenshot-container">
                        <img src="{{ screenshot_path }}" alt="Homepage Screenshot">
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        # Compile via Jinja2
        template = Template(template_str)
        
        # Get relative path for screenshot to use inside HTML
        rel_screenshot_path = ""
        if screenshot_path:
            # We can use absolute file:// path or relative
            rel_screenshot_path = "file://" + screenshot_path
            
        html_content = template.render(
            clean_name=clean_name,
            desc=desc,
            url=url,
            overall_score=overall_score,
            opp_tier=opp_tier,
            scores=scores,
            swot=swot,
            emails=emails,
            phones=phones,
            addresses=addresses,
            tech_stack=tech_stack,
            recs=recs,
            screenshot_path=rel_screenshot_path,
            data=data
        )
        
        # Write HTML report
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Saved premium HTML report to {output_path}")
        
        return html_content
