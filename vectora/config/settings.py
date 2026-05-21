"""Single Source of Truth for Vectora Configuration.

Pydantic-based settings module that consolidates:
1. Environment variables (3-level hierarchy: defaults.env → .env → ~/.vectora/.env)
2. Application constants (paths, databases, versions)
3. Runtime configuration (debug mode, model selection, logging)

This replaces the scattered config.py, constants.py, and initialization.py.

All configuration is validated at application startup — fails fast with clear
error messages instead of silent NoneType errors mid-execution.
"""

import logging
import os
from importlib import resources
from pathlib import Path
from typing import Any, Literal, cast

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Immutable application settings with validation.

    Three-level configuration hierarchy (in order of precedence):
    1. Embedded defaults.env (reproducible, in-package defaults)
    2. Project-local .env (project-specific overrides)
    3. User global ~/.vectora/.env (personal preferences)

    All settings are validated on initialization. Missing required settings
    raise ValidationError immediately instead of causing NoneType errors later.
    """

    # ============================================================================
    # LLM PROVIDER & MODEL CONFIGURATION
    # ============================================================================

    llm_provider: Literal["google-genai", "openai", "anthropic", "ollama", "cohere"] = (
        "google-genai"
    )
    """Active LLM provider (auto-detected from API keys if not set)."""

    # Google Generative AI
    google_api_key: str | None = None
    google_model: str = "gemini-2.5-flash"

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    # Anthropic
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # Ollama (local)
    ollama_base_url: str | None = None
    ollama_model: str = "llama2"

    # Cohere Chat (command-* series)
    # Nota: cohere_api_key (seção EMBEDDINGS abaixo) é reutilizado para ChatCohere.
    # Use LLM_PROVIDER=cohere para habilitar. Não é detectado automaticamente porque
    # COHERE_API_KEY é primariamente para embeddings e reranking.
    cohere_chat_model: str = "command-a-03-2025"

    # ============================================================================
    # APPLICATION IDENTITY & VERSIONING
    # ============================================================================

    version: str = "0.1.0rc1"
    """Vectora version (synced with pyproject.toml)."""

    app_name: str = "Vectora"
    creator_name: str = "Bruno Soares"

    # ============================================================================
    # RUNTIME BEHAVIOR
    # ============================================================================

    debug_mode: bool = False
    """Enable debug logging and verbose output."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    """Application log level."""

    quiet_mode: bool = False
    """Suppress external library logs (langchain, langgraph, etc.)."""

    # ============================================================================
    # DIRECTORIES (Roaming Profile Pattern)
    # ============================================================================

    vectora_home: Path = Path.home() / ".vectora"
    """Base directory for Vectora user data (~/.vectora/)."""

    data_dir: Path | None = None
    """Vector store, databases, embeddings (~/.vectora/data/)."""

    logs_dir: Path | None = None
    """Application logs (~/.vectora/logs/)."""

    keys_dir: Path | None = None
    """Sensitive credentials (~/.vectora/keys/)."""

    # ============================================================================
    # DATABASE CONNECTIONS
    # ============================================================================

    db_file: Path | None = None
    """SQLite database for sessions/checkpoints (~/.vectora/data/vectora.db)."""

    embedding_queue_file: Path | None = None
    """SQLite database for embedding queue (~/.vectora/data/embedding_queue.db)."""

    lancedb_dir: str | None = None
    """LanceDB vector store directory (~/.vectora/data/lancedb/)."""

    # Derived connection strings
    db_dsn: str | None = None
    """Database connection string for AsyncSqliteSaver."""

    embedding_queue_dsn: str | None = None
    """Embedding queue connection string."""

    # ============================================================================
    # FILE PATHS
    # ============================================================================

    env_file: Path | None = None
    """User configuration file (~/.vectora/.env)."""

    log_file: Path | None = None
    """Main application log file (JSON lines format)."""

    mcp_config_file: Path | None = None
    """MCP server configuration (~/.vectora/mcp.config.json)."""

    chat_config_file: Path | None = None
    """Persistent chat settings (~/.vectora/chat_config.json)."""

    # ============================================================================
    # FEATURE FLAGS & LIMITS
    # ============================================================================

    enable_mcp: bool = False
    """Enable MCP (Model Context Protocol) server integration."""

    max_context_tokens: int = 8000
    """Maximum tokens to keep in message history (sliding window)."""

    max_embedding_queue_size: int = 1000
    """Maximum documents pending embedding before throttling."""

    embedding_batch_size: int = 32
    """Number of documents to embed per batch."""

    # ============================================================================
    # WEB SEARCH (TAVILY)
    # ============================================================================

    tavily_api_key: str | None = None
    """API key for Tavily web search service."""

    # ============================================================================
    # EMBEDDINGS (COHERE) & RAG
    # ============================================================================

    cohere_api_key: str | None = None
    """API key for Cohere embeddings and reranking service."""

    embedding_model: str = "embed-multilingual-v3.0"
    """Cohere embedding model. v3.0 multilingual cobre 100+ idiomas (PT-BR)."""

    cohere_calls_per_minute: int = 90
    """Máximo de chamadas de embedding Cohere por minuto.
    Trial keys: 100/min — usamos 90 como buffer de segurança (10% abaixo do limite).
    Production keys: aumentar para 500+ conforme contrato."""

    embedding_dims: int = 1024
    """Cohere v3 retorna vetores de 1024 dimensões."""

    embedding_queue_enabled: bool = True
    """Enable asynchronous embedding queue processing."""

    # ── Tokenizer / Chunking ─────────────────────────────────────────────────
    tiktoken_encoding: str = "cl100k_base"
    """Tiktoken encoding used for token counting and document chunking.
    cl100k_base é compatível com GPT-4 e serve de boa aproximação para
    Cohere v3 (context de 512 tokens por embedding). Sem HuggingFace."""

    chunk_size: int = 512
    """Tamanho máximo de cada chunk em tokens (para ingestão de documentos)."""

    chunk_overlap: int = 50
    """Sobreposição em tokens entre chunks consecutivos (contexto entre chunks)."""

    default_search_top_k: int = 10
    """Default number of top-k results for vector search."""

    search_min_score: float = 0.5
    """Minimum similarity score threshold for search results."""

    reranker_type: str = "cohere"
    """Reranking model type (cohere, none)."""

    reranker_model: str = "rerank-multilingual-v3.0"
    """Cohere reranker. v3.0 multilingual ideal para conteúdo PT-BR."""

    reranker_top_k: int = 5
    """Number of results to rerank."""

    # ============================================================================
    # MCP (MODEL CONTEXT PROTOCOL)
    # ============================================================================

    mcp_server_url: str | None = None
    """URL for MCP server (if using HTTP transport)."""

    mcp_transport_type: str = "stdio"
    """MCP transport type (stdio, http)."""

    mcp_command: str | None = None
    """MCP server command to execute (stdio mode)."""

    mcp_command_args: list[str] | None = None
    """MCP server command arguments."""

    mcp_timeout: int = 30
    """MCP request timeout in seconds."""

    # ============================================================================
    # PYDANTIC CONFIGURATION
    # ============================================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================================================
    # INITIALIZATION & VALIDATION
    # ============================================================================

    def __init__(self, **data: Any) -> None:
        """Initialize settings with 3-level hierarchy and validation.

        Hierarchy (in precedence order):
        1. Embedded defaults.env
        2. Project-local .env
        3. ~/.vectora/.env
        4. Constructor arguments

        All directories are created if they don't exist.
        Missing required settings raise ValidationError immediately.
        """
        # Load 3-level environment hierarchy BEFORE Pydantic validation
        self._load_environment_hierarchy()

        # Call parent init (validates all fields)
        super().__init__(**data)

        # Initialize derived paths
        self._initialize_directories()
        self._initialize_derived_paths()

        # Auto-detect LLM provider if not explicitly set
        self._detect_llm_provider()

        logger.info(
            "Settings initialized",
            extra={
                "version": self.version,
                "llm_provider": self.llm_provider,
                "debug_mode": self.debug_mode,
            },
        )

    def _load_environment_hierarchy(self) -> None:
        """Load environment variables with 4-level hierarchy.

        Order of precedence (highest to lowest):
        1. .env (project local)              ← overrides everything (API keys, explicit config)
        2. ~/.vectora/.env (user secrets)    ← API keys do usuário (setup wizard)
        3. ~/.vectora/settings.json          ← preferências de runtime (provider ativo, model)
        4. defaults.env (embedded package)   ← valores padrão do Vectora
        5. OS environment (already loaded)   ← variáveis de sistema

        Separação: settings.json armazena preferências não-secretas (provider, model,
        debug_mode). ~/.vectora/.env guarda segredos (API keys). Projeto .env tem
        prioridade máxima para desenvolvimento local.
        """
        # Level 5 (lowest): Load embedded defaults.env via setdefault
        try:
            defaults_env = resources.files("vectora").joinpath("defaults.env")
            defaults_text = defaults_env.read_text(encoding="utf-8")

            for line in defaults_text.split("\n"):
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    if "=" in stripped:
                        key, value = stripped.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())
            logger.debug("Loaded defaults.env from package")
        except FileNotFoundError, TypeError, ModuleNotFoundError, AttributeError:
            logger.debug("defaults.env not found (normal for development)")

        # Level 3: Load ~/.vectora/settings.json (preferências de runtime não-secretas)
        # Contém: active_provider, active_model, debug_mode — NÃO contém API keys.
        # override=False (setdefault) para que o projeto .env ainda possa sobrescrever.
        _settings_json = Path.home() / ".vectora" / "settings.json"
        if _settings_json.exists():
            try:
                import json as _json

                _rt = _json.loads(_settings_json.read_text(encoding="utf-8"))
                _provider = _rt.get("active_provider")
                _model = _rt.get("active_model")
                if _provider:
                    os.environ.setdefault("LLM_PROVIDER", _provider)
                if _model and _provider:
                    _model_env_map = {
                        "google-genai": "GOOGLE_MODEL",
                        "openai": "OPENAI_MODEL",
                        "anthropic": "ANTHROPIC_MODEL",
                        "ollama": "OLLAMA_MODEL",
                        "cohere": "COHERE_CHAT_MODEL",
                    }
                    if _env_var := _model_env_map.get(_provider):
                        os.environ.setdefault(_env_var, _model)
                logger.debug(f"Loaded runtime settings from {_settings_json}")
            except Exception as _e:
                logger.debug(f"Could not load settings.json: {_e}")

        # Level 2: Load user global ~/.vectora/.env (segredos pessoais, fallback)
        # override=False: apenas preenche variáveis ainda não definidas no OS env.
        # O projeto .env (carregado abaixo com override=True) sempre ganha.
        user_env = Path.home() / ".vectora" / ".env"
        if user_env.exists():
            load_dotenv(user_env, override=False)
            logger.debug(f"Loaded user .env from {user_env} (fallback only)")

        # Level 1 (highest): Load project-local .env — overrides user global
        # Also check the package/project root directory to support running from other directories (e.g. via MCP/orchestrator)
        package_root_env = Path(__file__).resolve().parent.parent.parent / ".env"
        project_env = Path.cwd() / ".env"

        # Load package root .env first
        if (
            package_root_env.exists()
            and package_root_env.resolve() != project_env.resolve()
        ):
            load_dotenv(package_root_env, override=True)
            logger.debug(f"Loaded package root .env from {package_root_env}")

        # Load project-local .env (precedence over package root if in a different directory)
        if project_env.exists():
            load_dotenv(project_env, override=True)
            logger.debug(f"Loaded project .env from {project_env}")

    def _initialize_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.vectora_home.mkdir(parents=True, exist_ok=True)

        # Set directory paths
        self.data_dir = self.vectora_home / "data"
        self.logs_dir = self.vectora_home / "logs"
        self.keys_dir = self.vectora_home / "keys"

        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(
            "Directories initialized",
            extra={
                "vectora_home": str(self.vectora_home),
                "data_dir": str(self.data_dir),
            },
        )

    def _initialize_derived_paths(self) -> None:
        """Set all derived path and connection string fields."""
        # data_dir and logs_dir are always set by _initialize_directories before this;
        # cast to Path so the type checker understands the None branch is unreachable here
        data_dir = cast("Path", self.data_dir)
        logs_dir = cast("Path", self.logs_dir)

        # Database files
        self.db_file = data_dir / "vectora.db"
        self.embedding_queue_file = data_dir / "embedding_queue.db"

        # Connection strings
        # db_dsn: path simples (aceito por aiosqlite.connect() e Checkpointer)
        self.db_dsn = str(self.db_file)
        # embedding_queue_dsn: URL SQLAlchemy completa com driver async
        # SQLAlchemy create_async_engine() exige formato: dialect+driver:///path
        # Em Windows, paths absolutos começam com letra (C:\...) então usar as_posix()
        # para evitar escape de barras invertidas
        self.embedding_queue_dsn = (
            f"sqlite+aiosqlite:///{self.embedding_queue_file.as_posix()}"
        )

        # Vector store
        self.lancedb_dir = str(data_dir / "lancedb")

        # Configuration files
        self.env_file = self.vectora_home / ".env"
        self.log_file = logs_dir / "vectora.jsonl"
        self.mcp_config_file = self.vectora_home / "mcp.config.json"
        self.chat_config_file = self.vectora_home / "chat_config.json"

    def _detect_llm_provider(self) -> None:
        """Auto-detect LLM provider from available API keys.

        Precedence order (if multiple keys present):
        1. anthropic_api_key
        2. openai_api_key
        3. google_api_key
        4. ollama_base_url
        """
        if self.anthropic_api_key:
            self.llm_provider = "anthropic"
        elif self.openai_api_key:
            self.llm_provider = "openai"
        elif self.google_api_key:
            self.llm_provider = "google-genai"
        elif self.ollama_base_url:
            self.llm_provider = "ollama"

        logger.debug(f"LLM provider auto-detected: {self.llm_provider}")

    # ============================================================================
    # PUBLIC QUERY METHODS
    # ============================================================================

    def get_llm_provider(self) -> str:
        """Get the active LLM provider.

        Returns:
            Provider name: "google-genai", "openai", "anthropic", or "ollama"
        """
        return self.llm_provider

    def get_llm_model(self) -> str:
        """Get the model name for the active provider.

        Returns:
            Model name configured for current provider
        """
        model_map = {
            "google-genai": self.google_model,
            "openai": self.openai_model,
            "anthropic": self.anthropic_model,
            "ollama": self.ollama_model,
            "cohere": self.cohere_chat_model,
        }
        return model_map.get(self.llm_provider, self.google_model)

    def get_llm_api_key(self) -> str | None:
        """Get the API key for the active provider.

        Returns:
            API key or None if not configured
        """
        key_map = {
            "google-genai": self.google_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "ollama": None,  # Ollama doesn't require API key
            "cohere": self.cohere_api_key,
        }
        return key_map.get(self.llm_provider)

    def get_cohere_api_key(self) -> str | None:
        """Get the API key for Cohere embeddings and reranking.

        Precedência:
        1. Settings.cohere_api_key (carregado de .env / ~/.vectora/.env)
        2. Variável de ambiente COHERE_API_KEY (autodetectada pelo SDK também)

        Nota sobre formato das chaves Cohere:
        Chaves modernas do Cohere têm o prefixo "cohere_" (ex: cohere_AbCd1234...).
        O dashboard do Cohere tem um bug de UI onde ao VISUALIZAR uma chave já criada
        ele exibe apenas os dígitos sem o prefixo "cohere_". Sempre crie uma NOVA chave
        para copiar o valor completo — nunca use o campo "View" de chaves existentes.

        Returns:
            Cohere API key ou None se não configurado.
        """
        return self.cohere_api_key or os.getenv("COHERE_API_KEY")

    def get_available_providers(self) -> list[str]:
        """Get list of providers with API keys configured.

        Returns:
            List of available provider names
        """
        available = []
        if self.anthropic_api_key:
            available.append("anthropic")
        if self.openai_api_key:
            available.append("openai")
        if self.google_api_key:
            available.append("google-genai")
        if self.ollama_base_url:
            available.append("ollama")
        if self.cohere_api_key:
            available.append("cohere")
        return available

    def set_model(self, provider: str, model: str) -> None:
        """Update model for a specific provider.

        Args:
            provider: LLM provider ("google-genai", "openai", "anthropic", "ollama")
            model: Model name

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in ["google-genai", "openai", "anthropic", "ollama", "cohere"]:
            raise ValueError(f"Unknown LLM provider: {provider}")

        if provider == "google-genai":
            self.google_model = model
        elif provider == "openai":
            self.openai_model = model
        elif provider == "anthropic":
            self.anthropic_model = model
        elif provider == "ollama":
            self.ollama_model = model
        elif provider == "cohere":
            self.cohere_chat_model = model

        logger.info(f"Model updated: {provider}={model}")

    # ============================================================================
    # LEGACY COMPATIBILITY
    # ============================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """Legacy method for backward compatibility with old Config class.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        return getattr(self, key.lower(), default)

    def set(self, key: str, value: Any) -> None:
        """Legacy method for backward compatibility.

        Args:
            key: Configuration key
            value: New value
        """
        if hasattr(self, key.lower()):
            setattr(self, key.lower(), value)
            logger.debug(f"Configuration updated: {key}={value}")


# ============================================================================
# SINGLETON INSTANCE (For gradual migration from old Config)
# ============================================================================

_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global Settings instance.

    This function provides a singleton pattern for backward compatibility
    while encouraging use of dependency injection for new code.

    Returns:
        Global Settings instance
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# Module-level singleton for convenient access
settings = get_settings()
