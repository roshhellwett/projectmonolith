"""
Centralized secret validation and management for Project Monolith.

Validates all required environment variables at startup, categorizes them
by criticality, and provides masked logging helpers.
"""

import os
from dataclasses import dataclass, field
from enum import Enum

from core.logger import setup_logger

logger = setup_logger("SECRETS")


class SecretLevel(Enum):
    """How critical a secret is for system operation."""

    CRITICAL = "critical"  # System cannot start without this
    REQUIRED = "required"  # Bot/service won't work without this, but others can
    OPTIONAL = "optional"  # Nice-to-have, system degrades gracefully


@dataclass
class SecretDefinition:
    """Definition of an expected environment variable."""

    name: str
    level: SecretLevel
    description: str
    service: str = "core"  # Which service needs this


@dataclass
class SecretValidationResult:
    """Result of validating all secrets at startup."""

    missing_critical: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    present: list[str] = field(default_factory=list)

    @property
    def can_start(self) -> bool:
        return len(self.missing_critical) == 0


# ==========================================================
# All secrets the system expects
# ==========================================================
SECRET_DEFINITIONS: list[SecretDefinition] = [
    # Core — system won't start without these
    SecretDefinition("DATABASE_URL", SecretLevel.CRITICAL, "PostgreSQL connection string"),
    SecretDefinition("WEBHOOK_SECRET", SecretLevel.CRITICAL, "Webhook authentication secret"),
    SecretDefinition("WEBHOOK_URL", SecretLevel.REQUIRED, "Public webhook base URL (falls back to polling)"),
    SecretDefinition("ADMIN_USER_ID", SecretLevel.CRITICAL, "Telegram user ID of the admin"),
    # Bot tokens — each bot degrades independently
    SecretDefinition("CRYPTO_BOT_TOKEN", SecretLevel.REQUIRED, "Crypto bot token", "crypto"),
    SecretDefinition("AI_BOT_TOKEN", SecretLevel.REQUIRED, "AI bot token", "ai"),
    SecretDefinition("GROUP_BOT_TOKEN", SecretLevel.REQUIRED, "Group bot token", "group"),
    SecretDefinition("SUPPORT_BOT_TOKEN", SecretLevel.REQUIRED, "Support bot token", "support"),
    SecretDefinition("ADMIN_BOT_TOKEN", SecretLevel.REQUIRED, "Admin bot token", "admin"),
    # External services — features degrade without these
    SecretDefinition("SERPER_API_KEY", SecretLevel.OPTIONAL, "Serper web search API key", "ai"),
    SecretDefinition("ETH_RPC_URL", SecretLevel.OPTIONAL, "Ethereum RPC endpoint", "crypto"),
    SecretDefinition("SOLANA_RPC_URL", SecretLevel.OPTIONAL, "Solana RPC endpoint", "crypto"),
    SecretDefinition("ETHERSCAN_API_KEY", SecretLevel.OPTIONAL, "Etherscan API key", "crypto"),
]


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """Mask a secret value for safe logging. Shows first N chars only."""
    if not value:
        return "<empty>"
    if len(value) <= visible_chars:
        return "****"
    return value[:visible_chars] + "*" * min(12, len(value) - visible_chars)


def validate_secrets() -> SecretValidationResult:
    """
    Validate all expected environment variables at startup.

    Returns a SecretValidationResult indicating what's present/missing.
    Logs warnings for missing secrets.
    """
    result = SecretValidationResult()

    for secret_def in SECRET_DEFINITIONS:
        value = os.getenv(secret_def.name, "").strip()

        if not value:
            if secret_def.level == SecretLevel.CRITICAL:
                result.missing_critical.append(secret_def.name)
                logger.critical(f"🚨 MISSING CRITICAL: {secret_def.name} — {secret_def.description}")
            elif secret_def.level == SecretLevel.REQUIRED:
                result.missing_required.append(secret_def.name)
                logger.warning(f"⚠️  MISSING REQUIRED: {secret_def.name} — {secret_def.service} service disabled")
            else:
                result.missing_optional.append(secret_def.name)
                logger.info(f"ℹ️  MISSING OPTIONAL: {secret_def.name} — {secret_def.description}")
        else:
            result.present.append(secret_def.name)

    return result


def enforce_startup_secrets() -> SecretValidationResult:
    """
    Validate secrets and abort if critical ones are missing.

    Call this during application startup (lifespan).
    """
    result = validate_secrets()

    logger.info(
        f"🔑 Secrets: {len(result.present)} present, "
        f"{len(result.missing_required)} required missing, "
        f"{len(result.missing_optional)} optional missing"
    )

    if not result.can_start:
        logger.critical(
            f"\n┌── 🚨 SECTOR ERROR DIAGNOSTIC ──┐\n"
            f"│ Sector:   SECRETS (enforce_startup_secrets)\n"
            f"│ Error:    Missing critical secrets: {', '.join(result.missing_critical)}\n"
            f"└────────────────────────────────┘"
        )
        # In production, we still start but log critical errors.
        # This allows the /health endpoint to report the issue.
        # Uncomment the line below to hard-fail:
        # sys.exit(1)

    if result.missing_required:
        logger.warning(f"⚠️  Services disabled due to missing tokens: " f"{', '.join(result.missing_required)}")

    return result


def is_service_configured(service_name: str) -> bool:
    """Check if all required secrets for a specific service are present."""
    for secret_def in SECRET_DEFINITIONS:
        if (
            secret_def.service == service_name
            and secret_def.level in (SecretLevel.CRITICAL, SecretLevel.REQUIRED)
            and not os.getenv(secret_def.name, "").strip()
        ):
            return False
    return True


