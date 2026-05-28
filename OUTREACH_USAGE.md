# Outreach Workflow

## 1. Generate Company Intelligence

Run the audit for one company:

```powershell
python main.py "Example Company"
```

Or run a batch file with one company name or website per line:

```powershell
python main.py companies.txt
```

The audit writes structured JSON to `outputs/json/` and includes personalized email, WhatsApp, and SMS drafts.

## 2. Prepare Approved Contacts

Copy `contacts.example.csv` and add only contacts you are allowed to message.

Required columns:

```csv
business_name,email,phone,channel,consent,approved
```

Messages are skipped unless both `consent` and `approved` are true.

## 3. Preview Sends

Dry-run is the default:

```powershell
python send_outreach.py --profile outputs/json/example_company.json --contacts contacts.csv
```

## 4. Send Email

Set SMTP environment variables:

```powershell
$env:SMTP_HOST="smtp.example.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="user@example.com"
$env:SMTP_PASSWORD="your-password"
$env:SMTP_FROM="user@example.com"
python send_outreach.py --profile outputs/json/example_company.json --contacts contacts.csv --send
```

## 5. Send WhatsApp

Set Twilio WhatsApp environment variables:

```powershell
$env:TWILIO_ACCOUNT_SID="AC..."
$env:TWILIO_AUTH_TOKEN="..."
$env:TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"
python send_outreach.py --profile outputs/json/example_company.json --contacts contacts.csv --send
```
