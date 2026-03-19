"""
Audit logging — security-relevant events written to a rotating file.

Log location: /data/audit.log (Fly.io) or ./audit.log (local).
Format: ISO timestamp | event | detail
"""
import logging
import logging.handlers
from pathlib import Path


def _build_audit_logger() -> logging.Logger:
    logger = logging.getLogger("crm.audit")
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.INFO)
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")

    # Rotating file — prefer /data (Fly.io volume), fall back to local
    for log_dir in [Path("/data"), Path(".")]:
        try:
            log_path = log_dir / "audit.log"
            handler = logging.handlers.RotatingFileHandler(
                log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            handler.setFormatter(fmt)
            logger.addHandler(handler)
            break
        except OSError:
            continue

    # Always echo to stdout so Fly.io `fly logs` picks it up
    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    return logger


_audit = _build_audit_logger()


# ── Public helpers ────────────────────────────────────────────────────────────

def log_login_success(vendedor_id: int, telefono: str, ip: str) -> None:
    _audit.info("LOGIN_OK | vendedor_id=%s telefono=%s ip=%s", vendedor_id, telefono, ip)


def log_login_failure(telefono: str, reason: str, ip: str) -> None:
    _audit.warning("LOGIN_FAIL | telefono=%s reason=%s ip=%s", telefono, reason, ip)


def log_account_locked(vendedor_id: int, telefono: str, ip: str) -> None:
    _audit.warning(
        "ACCOUNT_LOCKED | vendedor_id=%s telefono=%s ip=%s", vendedor_id, telefono, ip
    )


def log_audio_upload(vendedor_id: int, visita_id: int, size_mb: float, ip: str) -> None:
    _audit.info(
        "AUDIO_UPLOAD | vendedor_id=%s visita_id=%s size_mb=%.2f ip=%s",
        vendedor_id, visita_id, size_mb, ip,
    )


def log_transcription(vendedor_id: int, visita_id: int, is_demo: bool, ip: str) -> None:
    _audit.info(
        "TRANSCRIPTION | vendedor_id=%s visita_id=%s demo=%s ip=%s",
        vendedor_id, visita_id, is_demo, ip,
    )


def log_dashboard_login(ip: str, success: bool) -> None:
    event = "DASHBOARD_LOGIN_OK" if success else "DASHBOARD_LOGIN_FAIL"
    _audit.info("%s | ip=%s", event, ip)
