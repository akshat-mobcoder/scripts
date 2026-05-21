import os
import cv2
import pytesseract
import re
from PIL import Image
from core.utils import setup_logger

logger = setup_logger("core.ocr")

class OCRExtractor:
    @staticmethod
    def extract_from_image(image_path):
        """Phase 9: OCR Screenshot Extraction"""
        if not os.path.exists(image_path):
            logger.warning(f"OCR image path not found: {image_path}")
            return {"emails": [], "phones": [], "addresses": []}
            
        try:
            logger.info(f"Running OCR extraction on: {image_path}")
            # Preprocess image
            img = cv2.imread(image_path)
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Thresholding to improve OCR accuracy
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            
            # Run Tesseract
            text = pytesseract.image_to_string(thresh)
            
            # Extract
            emails = set()
            phones = set()
            addresses = set()
            
            # Emails
            email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
            for match in re.findall(email_pattern, text):
                emails.add(match.lower())
                
            # Phones
            phone_pattern = r'(\+?\d[\d\-\(\)\.\s]{7,}\d)'
            for match in re.findall(phone_pattern, text):
                clean = match.strip()
                digits = re.sub(r'\D', '', clean)
                if 9 <= len(digits) <= 15:
                    if not (len(digits) == 10 and digits.startswith(('202', '201'))):
                        phones.add(clean)
                        
            # Addresses (best effort on OCR text)
            street_pattern = r'\d+\s+[A-Za-z0-9#\.\s]{3,40}(?:Street|St|Avenue|Ave|Road|Rd|Highway|Hwy|Boulevard|Blvd|Drive|Dr|Way|Court|Ct|Circle|Cir|Lane|Ln|Suite|Ste|Floor|Fl)\.?,?\s+[A-Za-z\s]{3,20},?\s+[A-Z]{2}\s+\d{5}'
            for match in re.finditer(street_pattern, text, re.I):
                addresses.add(re.sub(r'\s+', ' ', match.group(0)))
                        
            logger.info(f"OCR extracted {len(emails)} emails, {len(phones)} phones, {len(addresses)} addresses")
            return {
                "emails": list(emails),
                "phones": list(phones),
                "addresses": list(addresses)
            }
        except Exception as e:
            logger.error(f"OCR extraction failed (is Tesseract installed?): {e}")
            return {"emails": [], "phones": [], "addresses": []}
