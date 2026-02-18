import re
import hashlib
from typing import Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    sanitized_value: Optional[str] = None


def validate_ethereum_address(address: str) -> ValidationResult:
    """
    Validate an Ethereum address.
    
    Returns ValidationResult with:
    - is_valid: True if valid address format
    - sanitized_value: Lowercase address (if valid)
    - error_message: Human-readable error
    """
    if not address:
        return ValidationResult(
            is_valid=False,
            error_message="Address cannot be empty",
            error_code="EMPTY_ADDRESS"
        )
    
    address = address.strip()
    
    if not address.startswith("0x"):
        return ValidationResult(
            is_valid=False,
            error_message="Address must start with '0x'",
            error_code="INVALID_PREFIX"
        )
    
    if len(address) != 42:
        return ValidationResult(
            is_valid=False,
            error_message=f"Address must be 42 characters (got {len(address)})",
            error_code="INVALID_LENGTH"
        )
    
    hex_part = address[2:]
    if not re.match(r'^[0-9a-fA-F]+$', hex_part):
        return ValidationResult(
            is_valid=False,
            error_message="Address contains invalid characters (only 0-9, a-f, A-F allowed)",
            error_code="INVALID_HEX"
        )
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=address.lower()
    )


def validate_price(price: str) -> ValidationResult:
    """
    Validate a price value.
    
    Returns ValidationResult with:
    - is_valid: True if valid positive number
    - sanitized_value: Float value
    - error_message: Human-readable error
    """
    if not price:
        return ValidationResult(
            is_valid=False,
            error_message="Price cannot be empty",
            error_code="EMPTY_PRICE"
        )
    
    try:
        cleaned = price.replace(",", "").replace(" ", "")
        value = float(cleaned)
        
        if value <= 0:
            return ValidationResult(
                is_valid=False,
                error_message="Price must be greater than 0",
                error_code="NEGATIVE_PRICE"
            )
        
        if value > 1_000_000_000:
            return ValidationResult(
                is_valid=False,
                error_message="Price seems unreasonably high (max 1B)",
                error_code="EXCEEDS_MAX"
            )
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=str(value)
        )
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_message="Invalid price format (use numbers only, e.g., 1000 or 1,000)",
            error_code="INVALID_FORMAT"
        )


def validate_token_symbol(symbol: str) -> ValidationResult:
    """
    Validate a token symbol.
    
    Returns ValidationResult with:
    - is_valid: True if valid symbol
    - sanitized_value: Uppercase symbol
    """
    if not symbol:
        return ValidationResult(
            is_valid=False,
            error_message="Token symbol cannot be empty",
            error_code="EMPTY_SYMBOL"
        )
    
    symbol = symbol.strip().upper()
    
    if len(symbol) > 10:
        return ValidationResult(
            is_valid=False,
            error_message="Token symbol too long (max 10 characters)",
            error_code="SYMBOL_TOO_LONG"
        )
    
    if not re.match(r'^[A-Z0-9]+$', symbol):
        return ValidationResult(
            is_valid=False,
            error_message="Symbol must contain only letters and numbers (e.g., BTC, ETH, SOL)",
            error_code="INVALID_SYMBOL"
        )
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=symbol
    )


def validate_wallet_label(label: str) -> ValidationResult:
    """
    Validate a wallet label.
    
    Returns ValidationResult with:
    - is_valid: True if valid label
    - sanitized_value: Cleaned label
    """
    if not label:
        return ValidationResult(
            is_valid=True,
            sanitized_value="Unnamed Wallet"
        )
    
    label = label.strip()
    
    if len(label) > 50:
        return ValidationResult(
            is_valid=False,
            error_message="Label too long (max 50 characters)",
            error_code="LABEL_TOO_LONG"
        )
    
    if not re.match(r'^[\w\s\-_.]+$', label):
        return ValidationResult(
            is_valid=False,
            error_message="Label contains invalid characters (use letters, numbers, spaces, -_. only)",
            error_code="INVALID_LABEL"
        )
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=label
    )


def validate_quantity(quantity: str) -> ValidationResult:
    """
    Validate a token quantity.
    
    Returns ValidationResult with:
    - is_valid: True if valid positive number
    - sanitized_value: Float value
    """
    if not quantity:
        return ValidationResult(
            is_valid=False,
            error_message="Quantity cannot be empty",
            error_code="EMPTY_QUANTITY"
        )
    
    try:
        cleaned = quantity.replace(",", "").replace(" ", "")
        value = float(cleaned)
        
        if value <= 0:
            return ValidationResult(
                is_valid=False,
                error_message="Quantity must be greater than 0",
                error_code="NEGATIVE_QUANTITY"
            )
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=str(value)
        )
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_message="Invalid quantity format (use numbers only)",
            error_code="INVALID_FORMAT"
        )


def validate_date_range(start_date: str, end_date: str) -> ValidationResult:
    """
    Validate a date range for analytics.
    
    Returns ValidationResult with:
    - is_valid: True if valid range
    - error_message: Error if invalid
    """
    from datetime import datetime, timedelta
    
    valid_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    
    start_dt = None
    for fmt in valid_formats:
        try:
            start_dt = datetime.strptime(start_date, fmt)
            break
        except ValueError:
            continue
    
    end_dt = None
    for fmt in valid_formats:
        try:
            end_dt = datetime.strptime(end_date, fmt)
            break
        except ValueError:
            continue
    
    if start_dt is None:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid start date format. Use: {valid_formats[0]}",
            error_code="INVALID_START_DATE"
        )
    
    if end_dt is None:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid end date format. Use: {valid_formats[0]}",
            error_code="INVALID_END_DATE"
        )
    
    if start_dt > end_dt:
        return ValidationResult(
            is_valid=False,
            error_message="Start date must be before end date",
            error_code="INVALID_RANGE"
        )
    
    if (end_dt - start_dt).days > 365:
        return ValidationResult(
            is_valid=False,
            error_message="Date range cannot exceed 365 days",
            error_code="RANGE_TOO_LONG"
        )
    
    return ValidationResult(is_valid=True)


def sanitize_callback_data(data: str, max_length: int = 64) -> str:
    """Sanitize callback data to prevent injection."""
    if not data:
        return ""
    
    allowed = re.sub(r'[^a-zA-Z0-9_]', '', data)
    return allowed[:max_length]


def validate_alert_direction(direction: str) -> ValidationResult:
    """Validate alert direction (above/below)."""
    if not direction:
        return ValidationResult(
            is_valid=False,
            error_message="Direction cannot be empty",
            error_code="EMPTY_DIRECTION"
        )
    
    direction = direction.strip().lower()
    
    if direction not in ("above", "below"):
        return ValidationResult(
            is_valid=False,
            error_message="Direction must be 'above' or 'below'",
            error_code="INVALID_DIRECTION"
        )
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=direction
    )


def validate_user_id(user_id: str) -> ValidationResult:
    """Validate a Telegram user ID."""
    if not user_id:
        return ValidationResult(
            is_valid=False,
            error_message="User ID cannot be empty",
            error_code="EMPTY_USER_ID"
        )
    
    try:
        uid = int(user_id)
        if uid <= 0:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid user ID",
                error_code="INVALID_USER_ID"
            )
        return ValidationResult(
            is_valid=True,
            sanitized_value=str(uid)
        )
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_message="User ID must be a number",
            error_code="INVALID_USER_ID"
        )


def validate_activation_key(key: str) -> ValidationResult:
    """Validate activation key format (ZENITH-XXXX-XXXX)."""
    if not key:
        return ValidationResult(
            is_valid=False,
            error_message="Activation key cannot be empty",
            error_code="EMPTY_KEY"
        )
    
    key = key.strip().upper()
    
    pattern = r'^ZENITH-[A-Z0-9]{4}-[A-Z0-9]{4}$'
    if not re.match(pattern, key):
        return ValidationResult(
            is_valid=False,
            error_message="Invalid key format. Use: ZENITH-XXXX-XXXX",
            error_code="INVALID_KEY_FORMAT"
        )
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=key
    )


def validate_days(days: str) -> ValidationResult:
    """Validate duration in days."""
    if not days:
        return ValidationResult(
            is_valid=False,
            error_message="Days cannot be empty",
            error_code="EMPTY_DAYS"
        )
    
    try:
        value = int(days)
        if value <= 0:
            return ValidationResult(
                is_valid=False,
                error_message="Days must be positive",
                error_code="NEGATIVE_DAYS"
            )
        if value > 3650:
            return ValidationResult(
                is_valid=False,
                error_message="Days cannot exceed 3650 (10 years)",
                error_code="EXCEEDS_MAX_DAYS"
            )
        return ValidationResult(
            is_valid=True,
            sanitized_value=str(value)
        )
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_message="Days must be a number",
            error_code="INVALID_DAYS"
        )


def validate_custom_word(word: str, max_length: int = 100) -> ValidationResult:
    """Validate a custom banned word/phrase."""
    if not word:
        return ValidationResult(
            is_valid=False,
            error_message="Word cannot be empty",
            error_code="EMPTY_WORD"
        )
    
    word = word.strip()
    
    if len(word) > max_length:
        return ValidationResult(
            is_valid=False,
            error_message=f"Word too long (max {max_length} characters)",
            error_code="WORD_TOO_LONG"
        )
    
    if len(word) < 2:
        return ValidationResult(
            is_valid=False,
            error_message="Word too short (min 2 characters)",
            error_code="WORD_TOO_SHORT"
        )
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=word
    )


def validate_priority(priority: str) -> ValidationResult:
    """Validate ticket priority."""
    valid_priorities = ["low", "normal", "high", "urgent"]
    
    if not priority:
        return ValidationResult(
            is_valid=False,
            error_message="Priority cannot be empty",
            error_code="EMPTY_PRIORITY"
        )
    
    priority = priority.strip().lower()
    
    if priority not in valid_priorities:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid priority. Use: {', '.join(valid_priorities)}",
            error_code="INVALID_PRIORITY"
        )
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=priority
    )


def check_rate_limit(
    user_id: int,
    action: str,
    limit: int,
    window_seconds: int,
    redis_client=None
) -> Tuple[bool, Optional[int]]:
    """
    Check if user has exceeded rate limit.
    
    Returns (is_allowed, seconds_until_reset)
    """
    from datetime import datetime, timedelta
    import time
    
    key = f"rate_limit:{user_id}:{action}"
    now = time.time()
    
    if redis_client:
        try:
            current = redis_client.get(key)
            if current and int(current) >= limit:
                ttl = redis_client.ttl(key)
                return False, ttl if ttl > 0 else window_seconds
            
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            pipe.execute()
            return True, 0
        except Exception:
            pass
    
    return True, 0


class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
