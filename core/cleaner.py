import re

def clean_emails(emails):
    """Normalize and remove duplicate emails."""
    cleaned = set()
    for e in emails:
        e_clean = e.strip().lower()
        # Basic validation
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', e_clean):
            # Ignore standard template placeholders
            if not any(x in e_clean for x in ["email.com", "example.com", "yoursite.com", "domain.com", "wix.com"]):
                cleaned.add(e_clean)
    return sorted(list(cleaned))

def clean_phones(phones):
    """Normalize and deduplicate phone numbers."""
    cleaned = set()
    for p in phones:
        # Strip all non-essential formatting
        original = str(p).strip()
        p_clean = original
        # Strip trailing chars
        p_clean = re.sub(r'[^\d+x\-.\(\)\s]', '', p_clean)
        p_clean = re.sub(r'\s+', ' ', p_clean).strip()
        
        # Deduplicate by comparing numbers only
        digits = re.sub(r'\D', '', p_clean)
        if not 7 <= len(digits) <= 15:
            continue

        # Avoid browser versions, coordinates, IDs, and analytics numbers that
        # look numeric but are not contact phone numbers.
        if re.search(r'\d+\.\d+\.\d+', p_clean):
            continue
        if re.search(r'\d+\.\d{5,}', p_clean):
            continue
        if re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}$', original):
            continue
        if len(set(digits)) <= 2 and len(digits) > 8:
            continue
        if digits.startswith(('201', '202')) and len(digits) == 10:
            continue

        starts_international = p_clean.startswith("+")
        if not starts_international:
            domestic_pattern = re.compile(
                r'^(?:\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}|\d{3}[-.\s]\d{4})(?:\s*x\d+)?$',
                re.I
            )
            if not domestic_pattern.match(p_clean):
                continue

        has_phone_formatting = bool(re.search(r'^\+|[\s().-]|x\d+', p_clean, re.I))
        is_plain_digits = p_clean == digits
        if is_plain_digits and not has_phone_formatting:
            continue

        cleaned.add(p_clean)
                
    return sorted(list(cleaned))

def clean_addresses(addresses):
    """Filter and deduplicate physical addresses."""
    cleaned = set()
    for addr in addresses:
        addr_clean = addr.strip()
        # Clean double spaces
        addr_clean = re.sub(r'\s+', ' ', addr_clean)
        # Exclude header noise
        if len(addr_clean) > 15:
            # Exclude menu items or footer labels
            if not any(x in addr_clean.lower() for x in ["copyright", "all rights reserved", "terms of use", "privacy policy"]):
                cleaned.add(addr_clean)
    return sorted(list(cleaned))
