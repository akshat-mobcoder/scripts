#!/usr/bin/env python3
"""
Consent-gated outreach sender.

This script sends generated audit messages only for contacts explicitly marked
as both consented and approved. It defaults to dry-run mode; pass --send to
actually send through SMTP and/or Twilio WhatsApp.

Contacts CSV columns:
    business_name,email,phone,channel,consent,approved

Examples:
    python send_outreach.py --profile outputs/json/acme.json --contacts contacts.csv
    python send_outreach.py --profile outputs/json/acme.json --contacts contacts.csv --send
"""

import argparse
import csv
import json
import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage
from typing import Any, Dict, Iterable, List

import requests


TRUE_VALUES = {"1", "true", "yes", "y", "approved", "consented", "opt-in", "opted-in"}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def truthy(value: str) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def load_profiles(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    profiles = payload if isinstance(payload, list) else [payload]
    by_name = {}
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        name = profile.get("business_name") or profile.get("company") or profile.get("name")
        if name:
            by_name[normalize_name(name)] = profile
    return by_name


def load_contacts(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def get_profile_for_contact(contact: Dict[str, str], profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if len(profiles) == 1:
        return next(iter(profiles.values()))

    business_name = contact.get("business_name") or contact.get("company") or contact.get("name")
    profile = profiles.get(normalize_name(business_name))
    if not profile:
        raise ValueError(f"No matching profile for contact business_name='{business_name}'")
    return profile


def get_messages(profile: Dict[str, Any]) -> Dict[str, str]:
    outreach = profile.get("outreach") or {}
    return {
        "email": outreach.get("email") or profile.get("outreach_email") or "",
        "whatsapp": outreach.get("whatsapp") or "",
        "sms": outreach.get("sms") or "",
    }


def iter_approved_contacts(contacts: Iterable[Dict[str, str]]) -> Iterable[Dict[str, str]]:
    for contact in contacts:
        if truthy(contact.get("consent")) and truthy(contact.get("approved")):
            yield contact
        else:
            label = contact.get("business_name") or contact.get("email") or contact.get("phone") or "unknown"
            print(f"[SKIP] {label}: consent and approved must both be true")


def parse_email_subject_and_body(message: str, fallback_subject: str) -> tuple[str, str]:
    lines = message.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip() or fallback_subject
        body = "\n".join(lines[1:]).lstrip()
        return subject, body
    return fallback_subject, message


def send_email(to_email: str, message: str, fallback_subject: str, dry_run: bool) -> None:
    if not to_email:
        raise ValueError("Missing email address")

    subject, body = parse_email_subject_and_body(message, fallback_subject)
    if dry_run:
        print(f"[DRY-RUN][EMAIL] To: {to_email} | Subject: {subject}")
        return

    required = ["SMTP_HOST", "SMTP_FROM"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required email environment variables: {', '.join(missing)}")

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ["SMTP_FROM"]

    email = EmailMessage()
    email["From"] = from_email
    email["To"] = to_email
    email["Subject"] = subject
    email.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls(context=context)
        if username and password:
            server.login(username, password)
        server.send_message(email)
    print(f"[SENT][EMAIL] {to_email}")


def format_whatsapp_number(phone: str) -> str:
    phone = phone.strip()
    if phone.startswith("whatsapp:"):
        return phone
    if not phone.startswith("+"):
        raise ValueError("WhatsApp phone must be in E.164 format, for example +15551234567")
    return f"whatsapp:{phone}"


def send_whatsapp(phone: str, message: str, dry_run: bool) -> None:
    if not phone:
        raise ValueError("Missing WhatsApp phone number")

    to_number = format_whatsapp_number(phone)
    if dry_run:
        print(f"[DRY-RUN][WHATSAPP] To: {to_number} | Preview: {message[:120]}")
        return

    required = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required Twilio environment variables: {', '.join(missing)}")

    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_WHATSAPP_FROM"]
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    response = requests.post(
        url,
        data={"From": from_number, "To": to_number, "Body": message},
        auth=(account_sid, auth_token),
        timeout=30,
    )
    response.raise_for_status()
    print(f"[SENT][WHATSAPP] {to_number}")


def send_for_contact(contact: Dict[str, str], profile: Dict[str, Any], dry_run: bool) -> None:
    messages = get_messages(profile)
    business_name = profile.get("business_name") or "Company"
    channel = (contact.get("channel") or "email").lower()

    if channel in {"email", "both", "all"}:
        send_email(
            contact.get("email", ""),
            messages["email"],
            f"Quick growth audit for {business_name}",
            dry_run,
        )

    if channel in {"whatsapp", "both", "all"}:
        send_whatsapp(contact.get("phone", ""), messages["whatsapp"] or messages["sms"], dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send approved personalized outreach from audit JSON.")
    parser.add_argument("--profile", required=True, help="Audit JSON file generated by main.py")
    parser.add_argument("--contacts", required=True, help="CSV with business_name,email,phone,channel,consent,approved")
    parser.add_argument("--send", action="store_true", help="Actually send messages. Defaults to dry-run.")
    args = parser.parse_args()

    dry_run = not args.send
    profiles = load_profiles(args.profile)
    contacts = load_contacts(args.contacts)

    if not profiles:
        print("[ERROR] No profiles found in JSON input", file=sys.stderr)
        return 1

    sent_or_previewed = 0
    for contact in iter_approved_contacts(contacts):
        try:
            profile = get_profile_for_contact(contact, profiles)
            send_for_contact(contact, profile, dry_run)
            sent_or_previewed += 1
        except Exception as exc:
            label = contact.get("business_name") or contact.get("email") or contact.get("phone") or "unknown"
            print(f"[ERROR] {label}: {exc}", file=sys.stderr)

    mode = "previewed" if dry_run else "sent"
    print(f"[DONE] {sent_or_previewed} approved contact(s) {mode}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
