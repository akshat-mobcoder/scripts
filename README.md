# Lead Intelligence and Outreach Toolkit

This project finds a company's official website, crawls permitted public company pages, extracts business-level signals, creates an audit report, and generates personalized outreach drafts. It can also send approved messages through SMTP email or Twilio WhatsApp.

## What It Does

- Resolves a company name to its likely official website.
- Crawls allowed pages while respecting `robots.txt`.
- Extracts company-level data such as emails, phone numbers, addresses, social links, business hours, CTAs, forms, tech stack, SEO signals, performance signals, reviews, hiring signals, and conversion opportunities.
- Generates JSON, Markdown, HTML reports, screenshots, and personalized email/WhatsApp/SMS drafts.
- Sends outreach only from an approved contacts CSV where `consent` and `approved` are both true.

## Requirements

- Python 3.10+
- PowerShell or another terminal
- Internet access for search/crawling
- Optional: SMTP credentials for email sending
- Optional: Twilio WhatsApp credentials for WhatsApp sending

## Setup

From this folder:

```powershell
cd C:\Users\raina\scripts
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

If PowerShell blocks venv activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run One Company Audit

```powershell
python main.py "Stripe"
```

You can also pass a website URL directly:

```powershell
python main.py "https://stripe.com"
```

## Run Batch Audits

Create `companies.txt`:

```text
Stripe
Blue Bottle Coffee Oakland
https://www.example.com
```

Then run:

```powershell
python main.py companies.txt
```

## Output Files

The main audit writes files under `outputs/`:

- `outputs/json/`: structured company data and outreach drafts.
- `outputs/audits/`: Markdown audit reports.
- `outputs/reports/`: HTML audit dashboards.
- `outputs/screenshots/`: homepage screenshots.
- `outputs/evidence/`: manager-readable evidence files showing the exact pages, extracted data, and signals used.

Each JSON profile includes:

- `business_name`
- `website_url`
- `emails`
- `phone_numbers`
- `addresses`
- `business_hours`
- `social_links`
- `tech_stack`
- `seo`
- `performance`
- `cro`
- `hiring`
- `reviews`
- `scores`
- `outreach.email`
- `outreach.whatsapp`
- `outreach.sms`
- `evidence_file`
- `evidence_json_file`

## Manager Evidence Files

Every audit also creates:

```text
outputs/evidence/company_name_evidence.md
outputs/evidence/company_name_evidence.json
```

Use the Markdown file for a manager review. It shows:

- Crawl settings used, including the same rate limit.
- Pages crawled.
- Emails, phone numbers, addresses, business hours, CTAs, forms, social links, and copy samples found per page.
- Final company data used by the audit.
- Score basis for SEO, performance, CRO, trust, social, and growth.
- Recommendations and outreach drafts with the data they are based on.

Use the JSON file if you need the same evidence in structured form for another tool.

If an old run has an evidence JSON file but the Markdown file is missing or empty, rebuild all manager-readable evidence files with:

```powershell
python rebuild_evidence_reports.py
```

## Preview Outreach Sending

Copy the example contacts file:

```powershell
Copy-Item contacts.example.csv contacts.csv
```

Edit `contacts.csv` with approved contacts:

```csv
business_name,email,phone,channel,consent,approved
Stripe,hello@example.com,+15551234567,email,true,true
Stripe,,+15551234567,whatsapp,true,true
```

Supported `channel` values:

- `email`
- `whatsapp`
- `both`
- `all`

Preview without sending:

```powershell
python send_outreach.py --profile outputs/json/stripe.json --contacts contacts.csv
```

Dry-run is the default, so this only prints what would be sent.

## Send Email

Set SMTP environment variables:

```powershell
$env:SMTP_HOST="smtp.example.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="user@example.com"
$env:SMTP_PASSWORD="your-password"
$env:SMTP_FROM="user@example.com"
```

Then send:

```powershell
python send_outreach.py --profile outputs/json/stripe.json --contacts contacts.csv --send
```

## Send WhatsApp

Set Twilio WhatsApp environment variables:

```powershell
$env:TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:TWILIO_AUTH_TOKEN="your-auth-token"
$env:TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"
```

Then send:

```powershell
python send_outreach.py --profile outputs/json/stripe.json --contacts contacts.csv --send
```

Phone numbers in `contacts.csv` must use E.164 format, for example:

```text
+15551234567
```

## Important Safety Rules

- Only message contacts you are allowed to contact.
- Keep `consent=true` and `approved=true` only for contacts that are valid to send.
- Every generated message includes opt-out language.
- The sender skips rows that are not both consented and approved.
- Do not use this to bypass website rules, `robots.txt`, or platform terms.

## Useful Commands

Check Python syntax:

```powershell
python -m py_compile main.py send_outreach.py core/parser.py core/crawler.py ai/outreach.py ai/report_generator.py intelligence/cro.py
```

Run the older simple scraper:

```powershell
python scraper.py "Company Name"
```

The recommended full pipeline is:

```powershell
python main.py "Company Name"
python send_outreach.py --profile outputs/json/company_name.json --contacts contacts.csv
python send_outreach.py --profile outputs/json/company_name.json --contacts contacts.csv --send
```
