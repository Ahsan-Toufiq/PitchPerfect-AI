"""Validation utilities for PitchPerfect AI."""

import re
import urllib.parse
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
import tldextract

from .logger import get_logger


logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    cleaned_value: Optional[Any] = None
    
    def __bool__(self) -> bool:
        """Allow ValidationResult to be used in boolean context."""
        return self.is_valid


# Email validation patterns
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Business email patterns (to avoid personal emails)
PERSONAL_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'me.com', 'live.com', 'msn.com', 'ymail.com',
    'protonmail.com', 'mail.com', 'zoho.com', 'fastmail.com'
}

# Phone number pattern (international format)
PHONE_PATTERN = re.compile(
    r'^\+?[\d\s\-\(\)]{7,15}$'
)

# URL patterns
URL_PATTERN = re.compile(
    r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
)


def validate_email(email: str, allow_personal: bool = False) -> ValidationResult:
    """Validate email address.
    
    Args:
        email: Email address to validate
        allow_personal: Whether to allow personal email domains
        
    Returns:
        ValidationResult with validation status and cleaned email
    """
    if not email or not isinstance(email, str):
        return ValidationResult(False, "Email is required and must be a string")
    
    # Clean and normalize
    cleaned_email = email.strip().lower()
    
    # Basic format validation
    if not EMAIL_PATTERN.match(cleaned_email):
        return ValidationResult(False, f"Invalid email format: {email}")
    
    # Extract domain
    domain = cleaned_email.split('@')[1]
    
    # Check for personal email domains
    if not allow_personal and domain in PERSONAL_EMAIL_DOMAINS:
        return ValidationResult(
            False, 
            f"Personal email domain not allowed: {domain}",
            warnings=[f"Consider finding business email for this contact"]
        )
    
    # Check for suspicious patterns
    warnings = []
    if '+' in cleaned_email.split('@')[0]:
        warnings.append("Email contains '+' character (might be alias)")
    
    if len(cleaned_email.split('@')[0]) < 2:
        warnings.append("Very short email username")
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_email,
        warnings=warnings if warnings else None
    )


def validate_url(url: str, require_https: bool = False) -> ValidationResult:
    """Validate URL.
    
    Args:
        url: URL to validate
        require_https: Whether to require HTTPS
        
    Returns:
        ValidationResult with validation status and cleaned URL
    """
    if not url or not isinstance(url, str):
        return ValidationResult(False, "URL is required and must be a string")
    
    # Clean URL
    cleaned_url = url.strip()
    
    # Add protocol if missing
    if not cleaned_url.startswith(('http://', 'https://')):
        cleaned_url = 'https://' + cleaned_url
    
    # Basic format validation
    if not URL_PATTERN.match(cleaned_url):
        return ValidationResult(False, f"Invalid URL format: {url}")
    
    # Parse URL
    try:
        parsed = urllib.parse.urlparse(cleaned_url)
    except Exception as e:
        return ValidationResult(False, f"Failed to parse URL: {str(e)}")
    
    # Check for valid domain
    if not parsed.netloc:
        return ValidationResult(False, "URL missing domain")
    
    # Extract domain info
    try:
        domain_info = tldextract.extract(cleaned_url)
        if not domain_info.domain or not domain_info.suffix:
            return ValidationResult(False, "Invalid domain in URL")
    except Exception as e:
        logger.warning(f"Could not extract domain info from {cleaned_url}: {e}")
    
    # HTTPS requirement check
    warnings = []
    if require_https and parsed.scheme != 'https':
        return ValidationResult(False, "HTTPS required but URL uses HTTP")
    elif parsed.scheme == 'http':
        warnings.append("URL uses HTTP instead of HTTPS")
    
    # Check for suspicious patterns
    if parsed.netloc.count('.') > 5:
        warnings.append("URL has unusually many subdomains")
    
    if len(parsed.path) > 200:
        warnings.append("URL path is very long")
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_url,
        warnings=warnings if warnings else None
    )


def validate_phone(phone: str) -> ValidationResult:
    """Validate phone number.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        ValidationResult with validation status and cleaned phone
    """
    if not phone or not isinstance(phone, str):
        return ValidationResult(False, "Phone number is required and must be a string")
    
    # Clean phone number
    cleaned_phone = re.sub(r'[^\d\+\-\(\)\s]', '', phone.strip())
    
    if not cleaned_phone:
        return ValidationResult(False, "Phone number contains no valid characters")
    
    # Basic format validation
    if not PHONE_PATTERN.match(cleaned_phone):
        return ValidationResult(False, f"Invalid phone number format: {phone}")
    
    # Extract digits only for length check
    digits_only = re.sub(r'[^\d]', '', cleaned_phone)
    
    if len(digits_only) < 7 or len(digits_only) > 15:
        return ValidationResult(False, f"Phone number length invalid: {len(digits_only)} digits")
    
    warnings = []
    if not cleaned_phone.startswith('+'):
        warnings.append("Phone number missing country code")
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_phone,
        warnings=warnings if warnings else None
    )


def validate_business_name(name: str) -> ValidationResult:
    """Validate business name.
    
    Args:
        name: Business name to validate
        
    Returns:
        ValidationResult with validation status and cleaned name
    """
    if not name or not isinstance(name, str):
        return ValidationResult(False, "Business name is required and must be a string")
    
    # Clean name
    cleaned_name = ' '.join(name.strip().split())
    
    if len(cleaned_name) < 2:
        return ValidationResult(False, "Business name too short")
    
    if len(cleaned_name) > 200:
        return ValidationResult(False, "Business name too long")
    
    warnings = []
    
    # Check for suspicious patterns
    if cleaned_name.lower() in ['test', 'example', 'sample']:
        warnings.append("Business name appears to be placeholder")
    
    if re.search(r'^\d+$', cleaned_name):
        warnings.append("Business name is only numbers")
    
    if len(re.findall(r'[A-Z]', cleaned_name)) == len(cleaned_name.replace(' ', '')):
        warnings.append("Business name is all uppercase")
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_name,
        warnings=warnings if warnings else None
    )


def validate_business_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate complete business data record.
    
    Args:
        data: Dictionary containing business data
        
    Returns:
        ValidationResult with overall validation status
    """
    if not isinstance(data, dict):
        return ValidationResult(False, "Business data must be a dictionary")
    
    errors = []
    warnings = []
    cleaned_data = {}
    
    # Required fields
    required_fields = ['name']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return ValidationResult(False, "; ".join(errors))
    
    # Validate individual fields
    validations = {
        'name': (validate_business_name, data.get('name')),
        'email': (lambda x: validate_email(x, allow_personal=False), data.get('email')),
        'website': (validate_url, data.get('website')),
        'phone': (validate_phone, data.get('phone'))
    }
    
    for field, (validator, value) in validations.items():
        if value:  # Only validate if present
            result = validator(value)
            if not result.is_valid:
                errors.append(f"{field}: {result.error_message}")
            else:
                cleaned_data[field] = result.cleaned_value
                if result.warnings:
                    warnings.extend([f"{field}: {w}" for w in result.warnings])
        elif field in data:  # Field present but empty/None
            cleaned_data[field] = data[field]
    
    # Copy other fields as-is
    for field, value in data.items():
        if field not in validations:
            cleaned_data[field] = value
    
    # Additional business-specific validation
    if 'email' in cleaned_data and 'website' in cleaned_data:
        try:
            email_domain = cleaned_data['email'].split('@')[1]
            website_domain = tldextract.extract(cleaned_data['website']).registered_domain
            
            if email_domain != website_domain:
                warnings.append("Email domain doesn't match website domain")
        except Exception:
            pass  # Domain extraction failed, skip check
    
    # Rating validation
    if 'rating' in data:
        try:
            rating = float(data['rating'])
            if 0 <= rating <= 5:
                cleaned_data['rating'] = rating
            else:
                warnings.append(f"Rating {rating} outside expected range 0-5")
        except (ValueError, TypeError):
            warnings.append(f"Invalid rating format: {data['rating']}")
    
    # Review count validation
    if 'review_count' in data:
        try:
            review_count = int(data['review_count'])
            if review_count >= 0:
                cleaned_data['review_count'] = review_count
            else:
                warnings.append("Negative review count")
        except (ValueError, TypeError):
            warnings.append(f"Invalid review count format: {data['review_count']}")
    
    if errors:
        return ValidationResult(False, "; ".join(errors), warnings)
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_data,
        warnings=warnings if warnings else None
    )


def validate_search_term(search_term: str) -> ValidationResult:
    """Validate search term for scraping.
    
    Args:
        search_term: Search term to validate
        
    Returns:
        ValidationResult with validation status and cleaned term
    """
    if not search_term or not isinstance(search_term, str):
        return ValidationResult(False, "Search term is required and must be a string")
    
    # Clean search term
    cleaned_term = ' '.join(search_term.strip().split())
    
    if len(cleaned_term) < 3:
        return ValidationResult(False, "Search term too short (minimum 3 characters)")
    
    if len(cleaned_term) > 100:
        return ValidationResult(False, "Search term too long (maximum 100 characters)")
    
    warnings = []
    
    # Check for suspicious patterns
    if re.search(r'[^\w\s\-\,\.]', cleaned_term):
        warnings.append("Search term contains special characters")
    
    if cleaned_term.lower() in ['test', 'example', 'sample']:
        warnings.append("Search term appears to be placeholder")
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_term,
        warnings=warnings if warnings else None
    )


def validate_email_subject(subject: str) -> ValidationResult:
    """Validate email subject line.
    
    Args:
        subject: Email subject to validate
        
    Returns:
        ValidationResult with validation status and cleaned subject
    """
    if not subject or not isinstance(subject, str):
        return ValidationResult(False, "Email subject is required and must be a string")
    
    # Clean subject
    cleaned_subject = ' '.join(subject.strip().split())
    
    if len(cleaned_subject) < 5:
        return ValidationResult(False, "Email subject too short")
    
    if len(cleaned_subject) > 78:  # RFC recommended max
        return ValidationResult(False, "Email subject too long (max 78 characters)")
    
    warnings = []
    
    # Check for spam-like patterns
    spam_indicators = [
        'free', 'urgent', 'act now', 'limited time', 'guaranteed',
        '!!!', 'buy now', 'click here', 'make money', 'no cost'
    ]
    
    subject_lower = cleaned_subject.lower()
    for indicator in spam_indicators:
        if indicator in subject_lower:
            warnings.append(f"Subject contains potential spam indicator: '{indicator}'")
    
    # Check for excessive capitalization
    caps_ratio = sum(1 for c in cleaned_subject if c.isupper()) / len(cleaned_subject)
    if caps_ratio > 0.7:
        warnings.append("Subject has excessive capitalization")
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_subject,
        warnings=warnings if warnings else None
    )


def validate_email_content(content: str) -> ValidationResult:
    """Validate email content.
    
    Args:
        content: Email content to validate
        
    Returns:
        ValidationResult with validation status
    """
    if not content or not isinstance(content, str):
        return ValidationResult(False, "Email content is required and must be a string")
    
    # Clean content
    cleaned_content = content.strip()
    
    if len(cleaned_content) < 50:
        return ValidationResult(False, "Email content too short (minimum 50 characters)")
    
    if len(cleaned_content) > 5000:
        return ValidationResult(False, "Email content too long (maximum 5000 characters)")
    
    warnings = []
    
    # Check for required elements
    if 'unsubscribe' not in cleaned_content.lower():
        warnings.append("Email missing unsubscribe option")
    
    # Check for suspicious patterns
    if cleaned_content.count('!') > 5:
        warnings.append("Email has excessive exclamation marks")
    
    if re.search(r'(http://|https://)', cleaned_content):
        link_count = len(re.findall(r'(http://|https://)', cleaned_content))
        if link_count > 3:
            warnings.append(f"Email has many links ({link_count})")
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_content,
        warnings=warnings if warnings else None
    )


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem use.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed"
    
    # Remove/replace unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)  # Control characters
    sanitized = sanitized.strip('. ')  # Remove leading/trailing dots and spaces
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized


def is_valid_domain(domain: str) -> bool:
    """Check if domain is valid.
    
    Args:
        domain: Domain to check
        
    Returns:
        True if domain is valid
    """
    try:
        extracted = tldextract.extract(domain)
        return bool(extracted.domain and extracted.suffix)
    except Exception:
        return False


def clean_business_category(category: str) -> Optional[str]:
    """Clean and normalize business category.
    
    Args:
        category: Raw category string
        
    Returns:
        Cleaned category or None if invalid
    """
    if not category or not isinstance(category, str):
        return None
    
    # Clean and normalize
    cleaned = ' '.join(category.strip().split())
    cleaned = cleaned.title()  # Title case
    
    # Remove common prefixes/suffixes
    prefixes = ['the ', 'a ', 'an ']
    for prefix in prefixes:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
    
    if len(cleaned) < 2 or len(cleaned) > 50:
        return None
    
    return cleaned


def validate_analysis_scores(scores: Dict[str, float]) -> ValidationResult:
    """Validate website analysis scores.
    
    Args:
        scores: Dictionary of analysis scores
        
    Returns:
        ValidationResult with validation status
    """
    if not isinstance(scores, dict):
        return ValidationResult(False, "Scores must be a dictionary")
    
    valid_score_types = {
        'lighthouse_score', 'performance_score', 'seo_score', 
        'accessibility_score', 'best_practices_score'
    }
    
    errors = []
    warnings = []
    cleaned_scores = {}
    
    for score_type, value in scores.items():
        if score_type not in valid_score_types:
            warnings.append(f"Unknown score type: {score_type}")
            continue
        
        try:
            score_value = float(value)
            if 0 <= score_value <= 100:
                cleaned_scores[score_type] = score_value
            else:
                errors.append(f"{score_type} outside valid range 0-100: {score_value}")
        except (ValueError, TypeError):
            errors.append(f"Invalid score format for {score_type}: {value}")
    
    if errors:
        return ValidationResult(False, "; ".join(errors), warnings)
    
    return ValidationResult(
        True,
        cleaned_value=cleaned_scores,
        warnings=warnings if warnings else None
    ) 