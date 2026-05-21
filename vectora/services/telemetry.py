"""TelemetryService: Logging, audit trails, and observability.

Responsibilities:
1. JSON structured logging with correlation IDs
2. Session audit trail export to Markdown
3. Debug dumps for troubleshooting
4. Performance metrics collection
5. Error tracking and reporting

Ports logic from: log_setup.py, chat.py, debug_dump.py
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import platform
import sys
import tarfile
import uuid
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path

    from vectora.config.settings import Settings

logger = logging.getLogger(__name__)


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Include extra fields if present
        for key in [
            "thread_id",
            "user_type",
            "model",
            "retrieval_source",
            "reranking_applied",
            "routing_decision",
        ]:
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)

        return json.dumps(log_obj, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Format logs as readable text for development."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as text."""
        prefix = f"[{record.levelname:8}] {record.name:20} | "

        if hasattr(record, "thread_id"):
            prefix += f"thread={record.thread_id:>3} | "

        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return prefix + msg


class TelemetryService:
    """Manages application logging, audit trails, and observability.

    Features:
    - JSON structured logging with correlation IDs
    - Session audit trail export (Markdown format)
    - Debug dumps (.tar.gz with logs, config, state)
    - Performance metrics tracking
    - Integration with debug mode
    """

    def __init__(self, settings: Settings):
        """Initialize TelemetryService.

        Args:
            settings: Application settings
        """
        self.settings = settings
        # log_file is always set by Settings._initialize_derived_paths; cast for ty
        self.log_file: Path = cast("Path", settings.log_file)
        self.correlation_id: str | None = None
        self.session_messages: dict[int, list[dict]] = {}  # session_id -> messages

        # Setup logging
        self._setup_logging()

        logger.debug("TelemetryService initialized")

    def _setup_logging(self) -> None:
        """Configure logging with dual outputs: text (console) + JSON (file)."""
        log_level = self.settings.log_level
        quiet_mode = self.settings.quiet_mode

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level))

        # Avoid duplicate handlers
        if root_logger.handlers:
            return

        # Console handler with text formatting
        formatter_text = TextFormatter(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        )

        handler_console = logging.StreamHandler()
        handler_console.setFormatter(formatter_text)
        handler_console.setLevel(getattr(logging, log_level))
        root_logger.addHandler(handler_console)

        # File handler with JSON formatting
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        formatter_json = JSONFormatter()

        handler_file = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        handler_file.setFormatter(formatter_json)
        handler_file.setLevel(getattr(logging, log_level))
        root_logger.addHandler(handler_file)

        # Suppress external library logs in quiet mode
        if quiet_mode:
            silent_loggers = [
                "langchain",
                "langchain_core",
                "langchain_google_genai",
                "langgraph",
                "google",
                "google.genai",
            ]
            for logger_name in silent_loggers:
                logging.getLogger(logger_name).setLevel(logging.ERROR)

    def log_chat_message(
        self,
        session_id: int,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Log chat message to structured JSON log and audit trail.

        Args:
            session_id: Session identifier
            role: Message role ("user", "assistant", "system")
            content: Message content
            metadata: Additional metadata dict
        """
        # Add to session messages
        if session_id not in self.session_messages:
            self.session_messages[session_id] = []

        self.session_messages[session_id].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(UTC).isoformat(),
                "metadata": metadata or {},
            }
        )

        # Log to structured logging
        logger.info(
            f"[{role.upper()}] {content[:100]}...",
            extra={
                "session_id": session_id,
                "role": role,
                "content_length": len(content),
                **(metadata or {}),
            },
        )

    async def export_session_audit(self, session_id: int) -> str:
        """Export session as Markdown audit trail.

        Returns:
            Path to exported Markdown file (~/vectora/exports/session_N.md)
        """
        export_dir = self.settings.vectora_home / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"session_{session_id}.md"

        # Get messages for session
        messages = self.session_messages.get(session_id, [])

        # Build markdown content
        md_lines = [
            f"# Session Audit: #{session_id}",
            "",
            f"**Exported:** {datetime.now(UTC).isoformat()}",
            f"**Messages:** {len(messages)}",
            "",
            "## Conversation",
            "",
        ]

        for msg in messages:
            role = msg["role"].upper()
            timestamp = msg.get("timestamp", "unknown")
            content = msg["content"]

            md_lines.append(f"**{role}** ({timestamp})")
            md_lines.append(f"> {content}")
            md_lines.append("")

        # Write to file
        export_path.write_text("\n".join(md_lines), encoding="utf-8")

        logger.info(f"Session {session_id} exported to {export_path}")
        return str(export_path)

    async def export_debug_dump(self) -> str:
        """Create comprehensive debug dump for troubleshooting.

        Contents (.tar.gz):
        - INFO.json (metadata, platform info, versions)
        - logs/ (JSON log files)
        - data/ (databases if present)

        Returns:
            Path to .tar.gz file (~/.vectora/exports/debug_dump_TIMESTAMP.tar.gz)
        """
        export_dir = self.settings.vectora_home / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).isoformat().replace(":", "-").split(".")[0]
        dump_path = export_dir / f"debug_dump_{timestamp}.tar.gz"

        # Collect metadata
        metadata = {
            "timestamp": datetime.now(UTC).isoformat(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "llm_provider": self.settings.get_llm_provider(),
            "vectora_version": self.settings.version,
        }

        # Create tar.gz archive
        try:
            with tarfile.open(str(dump_path), "w:gz") as tar:
                # Add metadata
                meta_json = json.dumps(metadata, indent=2).encode()
                meta_info = tarfile.TarInfo(name="INFO.json")
                meta_info.size = len(meta_json)
                tar.addfile(meta_info, BytesIO(meta_json))

                # Add log files
                if self.log_file.parent.exists():
                    for log_file in self.log_file.parent.glob("*.jsonl"):
                        tar.add(str(log_file), arcname=f"logs/{log_file.name}")
                        logger.debug(f"Debug dump: added {log_file.name}")

                # Add databases if present
                data_dir = self.settings.data_dir
                if data_dir is not None and data_dir.exists():
                    for db_file in data_dir.glob("*.db"):
                        tar.add(str(db_file), arcname=f"data/{db_file.name}")
                    for wal_file in data_dir.glob("*.db-*"):
                        tar.add(str(wal_file), arcname=f"data/{wal_file.name}")

            logger.info(f"Debug dump created: {dump_path}")
            return str(dump_path)

        except Exception as e:
            logger.exception(f"Failed to create debug dump: {e}")
            raise

    def log_error(
        self,
        error_type: str,
        message: str,
        traceback: str | None = None,
        context: dict | None = None,
    ) -> None:
        """Log error with full context.

        Args:
            error_type: Error class name
            message: Error message
            traceback: Stack trace (optional)
            context: Additional context (session_id, user_input, etc.)
        """
        logger.error(
            f"{error_type}: {message}",
            extra={
                "error_type": error_type,
                "traceback": traceback or "",
                **(context or {}),
            },
        )

    def start_correlation(self, session_id: int) -> str:
        """Start new correlation ID for request tracing.

        Args:
            session_id: Session identifier

        Returns:
            Correlation ID (UUID)
        """
        self.correlation_id = str(uuid.uuid4())
        logger.debug(f"Correlation started: {self.correlation_id}")
        return self.correlation_id

    def get_metrics(self) -> dict:
        """Get current application metrics.

        Returns:
            Metrics dict with session and message statistics
        """
        total_messages = sum(len(msgs) for msgs in self.session_messages.values())
        total_sessions = len(self.session_messages)

        return {
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "correlation_id": self.correlation_id,
        }

    def enable_debug_logging(self) -> None:
        """Enable detailed debug logging."""
        self.settings.debug_mode = True
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")

    def disable_debug_logging(self) -> None:
        """Disable debug logging."""
        self.settings.debug_mode = False
        logging.getLogger().setLevel(getattr(logging, self.settings.log_level))
        logger.info("Debug logging disabled")
