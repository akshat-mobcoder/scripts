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
        p_clean = p.strip()
        # Strip trailing chars
        p_clean = re.sub(r'[^\d+x\-.\(\)\s]', '', p_clean)
        
        # Deduplicate by comparing numbers only
        digits = re.sub(r'\D', '', p_clean)
        if len(digits) >= 7:
            # Prevent adding parts of addresses
            if not (digits.startswith(('202', '201')) and len(digits) == 10 and int(digits[:4]) in range(2010, 2030)):
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
