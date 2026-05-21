"""Background Worker para Processamento de Embeddings Fire-and-Forget.

Loop assíncrono que:
1. Busca documentos pendentes da fila de embedding a cada 5 segundos
2. Processa até 10 documentos em paralelo (limitado por Semaphore(5))
3. Gera embeddings via Cohere (embed-multilingual-v3.0)
4. Escreve em LanceDB com idempotência (via queue_id como document ID)
5. Retry com exponential backoff (1s → 2s → 4s) até 3 tentativas
6. Move para DLQ após 3 falhas para auditoria manual
"""

import asyncio
import contextlib
import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import lancedb
except ImportError:
    lancedb = None  # type: ignore

try:
    import pyarrow as pa
except ImportError:
    pa = None  # type: ignore

try:
    from langchain_cohere import CohereEmbeddings
except ImportError:
    CohereEmbeddings = None  # type: ignore

from vectora.config.settings import settings
from vectora.services.queue import EmbeddingQueueRecord, get_embedding_queue

logger = logging.getLogger(__name__)


class CohereRateLimiter:
    """Token bucket rate limiter para chamadas à API Cohere.

    Garante que o BackgroundEmbeddingWorker nunca ultrapasse o limite de
    chamadas por minuto configurado — especialmente crítico para chaves trial
    (100 calls/min), onde bursts de 5 requests paralelos disparam HTTP 429.

    Algoritmo token bucket:
    - Capacidade = `calls_per_minute` tokens
    - Tokens se regeneram na taxa de 1 por `min_interval` segundos
    - `acquire()` bloqueia assincronamente até um token ficar disponível
    - Cada chamada registra o tempo de espera para métricas via /rag

    Por que token bucket (e não sleep fixo)?
    - Permite bursts curtos (se a fila estava vazia e tokens acumularam)
    - Mas limita a taxa média ao contrato da API ao longo do tempo
    - Não desperdiça capacidade em períodos de baixa demanda
    """

    def __init__(self, calls_per_minute: int) -> None:
        """Inicializa o rate limiter.

        Args:
            calls_per_minute: Limite de chamadas por minuto (ex: 90 para trial)
        """
        self.calls_per_minute = max(1, calls_per_minute)
        # Intervalo mínimo entre chamadas para respeitar o limite
        self.min_interval: float = 60.0 / self.calls_per_minute
        self._lock = asyncio.Lock()
        self._last_call_time: float = 0.0
        # Métricas expostas para o painel /rag
        self.throttle_count: int = 0
        self.total_throttle_seconds: float = 0.0

    async def acquire(self) -> float:
        """Aguarda até que seja seguro fazer mais uma chamada à API.

        Returns:
            Segundos de espera (0.0 se não houve throttle)
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call_time
            wait = self.min_interval - elapsed

            if wait > 0:
                self.throttle_count += 1
                self.total_throttle_seconds += wait
                logger.debug(
                    "cohere_rate_limiter_throttle: wait=%.2fs calls_per_min=%d",
                    wait,
                    self.calls_per_minute,
                )
                await asyncio.sleep(wait)

            self._last_call_time = time.monotonic()
            return max(0.0, wait)

    @property
    def avg_wait_s(self) -> float:
        """Tempo médio de espera por throttle (segundos)."""
        if self.throttle_count == 0:
            return 0.0
        return self.total_throttle_seconds / self.throttle_count

    @property
    def effective_rate(self) -> float:
        """Taxa efetiva configurada (calls/min)."""
        return self.calls_per_minute


# Tempos de backoff exponencial para retry de embeddings (segundos)
RETRY_BACKOFF = [1, 2, 4]  # 1s → 2s → 4s
MAX_RETRIES = 3
MAX_PARALLEL = 5  # Max 5 embeddings simultâneos (Semaphore)
BATCH_SIZE = 10  # Processa até 10 registros por batch

# Polling adaptativo: ao invés de POLLING_INTERVAL fixo, o worker
# aumenta o intervalo exponencialmente quando a fila está vazia
# e reseta ao encontrar items (evita queries desnecessárias em idle).
POLL_INTERVAL_MIN = 5  # Intervalo mínimo quando há items (segundos)
POLL_INTERVAL_MAX = 30  # Intervalo máximo em idle (segundos)
POLL_BACKOFF_FACTOR = 2  # Multiplicador a cada ciclo vazio


class _CohereRateLimitInterceptor(logging.Handler):
    """Intercepta warnings de rate limit do langchain_cohere.utils silenciosamente.

    Instalado diretamente no logger `langchain_cohere.utils` com propagate=False,
    impedindo que mensagens brutas de TooManyRequestsError / 429 cheguem ao root
    logger (e ao terminal do usuário).

    Em vez disso, atualiza o estado de rate limit no worker para exibição
    formatada via /rag — sem bloquear o fluxo async nem corromper o prompt.
    """

    def __init__(self, worker: BackgroundEmbeddingWorker) -> None:
        super().__init__(level=logging.WARNING)
        self.worker = worker

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if "429" in msg or "TooManyRequests" in msg or "rate" in msg.lower():
            self.worker.rate_limit_active = True
            self.worker.rate_limit_count += 1
            self.worker.last_rate_limit_at = datetime.now()
            # Ainda registra no arquivo JSON para auditabilidade
            file_logger = logging.getLogger("vectora.services.background")
            file_logger.debug(
                "cohere_rate_limit_intercepted: retry=%d",
                self.worker.rate_limit_count,
            )


class BackgroundEmbeddingWorker:
    """Worker assíncrono para processamento de embeddings em larga escala."""

    def __init__(self) -> None:
        """Inicializa o worker com configuração global."""
        self.config = settings
        self.running = False
        self.task: asyncio.Task[None] | None = None
        self.semaphore = asyncio.Semaphore(MAX_PARALLEL)
        # Semaphore(1) para proteger escritas em LanceDB contra race conditions
        # LanceDB não suporta múltiplas escritas simultâneas no mesmo diretório
        self.lancedb_semaphore = asyncio.Semaphore(1)
        # Contadores em memória para o painel /rag.
        # Não acumulam indefinidamente: resetados a cada startup do worker.
        self.processed_count: int = 0
        self.failed_count: int = 0
        # Cohere rate limit tracking — alimentado pelo _CohereRateLimitInterceptor.
        # rate_limit_active=True enquanto o último embedding retornou 429;
        # resetado para False após o primeiro embedding bem-sucedido.
        self.rate_limit_active: bool = False
        self.rate_limit_count: int = 0  # Total de 429s nesta sessão
        self.last_rate_limit_at: datetime | None = None
        self._rate_limit_handler: _CohereRateLimitInterceptor | None = None
        # Token bucket rate limiter — evita bursts que disparam HTTP 429.
        # Inicializado com o valor de settings (configurável; default 90/min).
        self._rate_limiter = CohereRateLimiter(self.config.cohere_calls_per_minute)
        # Polling adaptativo: _poll_interval cresce enquanto fila está vazia
        # e é resetado ao encontrar items (evita 12+ queries/min em idle).
        self._poll_interval: float = POLL_INTERVAL_MIN

    async def _get_queue(self) -> Any:
        """Obtém a queue (singleton lazy-loaded)."""
        return await get_embedding_queue(self.config.embedding_queue_dsn)

    async def start(self) -> None:
        """Inicia o worker como asyncio.Task."""
        if self.running:
            logger.warning("Worker já está rodando")
            return

        self.running = True

        # Instala interceptor no logger langchain_cohere.utils:
        # - propagate=False impede que warnings 429 cheguem ao root logger (terminal)
        # - o handler atualiza self.rate_limit_* para exibição formatada via /rag
        lc_logger = logging.getLogger("langchain_cohere.utils")
        self._rate_limit_handler = _CohereRateLimitInterceptor(self)
        lc_logger.addHandler(self._rate_limit_handler)
        lc_logger.propagate = False

        # Executar reconciliação na startup (recuperar records travados)
        await self._reconcile_startup()

        self.task = asyncio.create_task(self._run_loop())
        logger.info("BackgroundEmbeddingWorker iniciado")

    async def stop(self, timeout_seconds: int = 30) -> None:
        """Para o worker gracefully.

        Args:
            timeout_seconds: Segundos para aguardar a terminação
        """
        if not self.running:
            return

        logger.info("Parando BackgroundEmbeddingWorker...")
        self.running = False

        # Remove o interceptor e restaura propagação do logger
        lc_logger = logging.getLogger("langchain_cohere.utils")
        if self._rate_limit_handler:
            lc_logger.removeHandler(self._rate_limit_handler)
            self._rate_limit_handler = None
        lc_logger.propagate = True

        if self.task:
            try:
                async with asyncio.timeout(timeout_seconds):
                    await self.task
            except TimeoutError:
                logger.warning(
                    "Worker não terminou a tempo, cancelando",
                    extra={"timeout_seconds": timeout_seconds},
                )
                self.task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.task

        logger.info("BackgroundEmbeddingWorker parou")

    async def _reconcile_startup(self) -> None:
        """Recupera records travados em 'processing' na startup."""
        try:
            queue = await self._get_queue()
            await queue.reconcile()
            logger.info("Reconciliação de startup concluída")
        except Exception:
            logger.exception("Erro ao reconciliar startup")

    async def _run_loop(self) -> None:
        """Loop principal: fetch pending → process → retry/success/dlq."""
        while self.running:
            try:
                # Obter queue (lazy-loaded do singleton)
                queue = await self._get_queue()

                # Buscar até BATCH_SIZE documentos pendentes
                pending = await queue.get_pending(limit=BATCH_SIZE)

                if not pending:
                    # Fila vazia: backoff adaptativo até POLL_INTERVAL_MAX.
                    # Evita ~720 queries/hora em idle quando não há embeddings.
                    logger.debug(
                        "embedding_queue_empty, aguardando %.0fs",
                        self._poll_interval,
                    )
                    await asyncio.sleep(self._poll_interval)
                    self._poll_interval = min(
                        self._poll_interval * POLL_BACKOFF_FACTOR, POLL_INTERVAL_MAX
                    )
                    continue

                # Items encontrados: reset do intervalo de polling
                self._poll_interval = POLL_INTERVAL_MIN
                logger.debug("Batch encontrado", extra={"count": len(pending)})

                # Processar batch em paralelo (limitado por Semaphore)
                await asyncio.gather(
                    *[self._process_record(record, queue) for record in pending],
                    return_exceptions=True,
                )

                # Pequena pausa antes do próximo batch
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                logger.info("Worker foi cancelado")
                break
            except Exception:
                logger.exception("Erro no loop principal do worker")
                await asyncio.sleep(POLL_INTERVAL_MIN)

    async def _process_record(
        self, record: EmbeddingQueueRecord, queue: Any | None = None
    ) -> None:
        """Processa um registro individual com retry exponencial.

        Args:
            record: Registro da fila de embedding
            queue: Fila de embedding (obtém do singleton se None)
        """
        if queue is None:
            queue = await self._get_queue()

        queue_id = record.queue_id
        attempt = 0

        while attempt < MAX_RETRIES:
            try:
                async with self.semaphore:
                    # Marcar como processing
                    await queue.mark_processing(queue_id)

                    # Respeitar limite de chamadas Cohere (token bucket)
                    # Trial keys: 100 calls/min → configurado em 90 por segurança.
                    # acquire() retorna imediatamente se dentro do limite,
                    # ou aguarda async sem bloquear o event loop.
                    await self._rate_limiter.acquire()

                    # Gerar embedding via Cohere
                    embedding_vector = await self._generate_embedding(str(record.text))

                    # Escrever em LanceDB (idempotente via queue_id)
                    await self._write_to_lancedb(record, embedding_vector)

                    # Marcar como success
                    await queue.mark_success(queue_id)
                    self.processed_count += 1
                    # Embedding bem-sucedido: limpa flag de rate limit
                    self.rate_limit_active = False

                    logger.info(
                        "embedding_processed_success",
                        extra={
                            "queue_id": queue_id,
                            "collection": record.collection,
                        },
                    )
                    return  # Sucesso, sair do loop de retry

            except Exception as e:
                attempt += 1
                error_trace = traceback.format_exc()
                # Erro exposto diretamente na mensagem para aparecer no terminal
                logger.warning(
                    "embedding_processing_failed [%d/%d]: %s",
                    attempt,
                    MAX_RETRIES,
                    str(e),
                    extra={"queue_id": queue_id, "traceback": error_trace},
                )

                if attempt < MAX_RETRIES:
                    # Exponential backoff antes de retry
                    backoff_time = RETRY_BACKOFF[attempt - 1]
                    logger.info(
                        "embedding_retry_backoff",
                        extra={
                            "queue_id": queue_id,
                            "backoff_seconds": backoff_time,
                            "attempt": attempt,
                        },
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    # 3 falhas, mover para DLQ com stack trace completo
                    self.failed_count += 1
                    dlq_reason = f"{e!s}\n\nStack trace:\n{error_trace}"
                    try:
                        await queue.mark_dlq(queue_id, dlq_reason)
                    except Exception:
                        logger.exception(
                            "Erro ao mover para DLQ",
                            extra={"queue_id": queue_id},
                        )
                    else:
                        logger.info(
                            "embedding_moved_to_dlq",
                            extra={
                                "queue_id": queue_id,
                                "reason": str(e),
                            },
                        )

    async def _generate_embedding(self, text: str) -> list[float]:
        """Gera embedding via Cohere.

        Args:
            text: Texto para embeddar

        Returns:
            Lista de floats representando o embedding

        Raises:
            ValueError: Se COHERE_API_KEY não estiver configurado
            ImportError: Se langchain_cohere não estiver instalado
        """
        api_key = self.config.get_cohere_api_key()
        if not api_key:
            msg = "COHERE_API_KEY não configurado"
            raise ValueError(msg)

        # Diagnóstico de autenticação — apenas em DEBUG para não poluir o terminal
        logger.debug(
            "cohere_auth: len=%d prefix=%s suffix=%s",
            len(api_key),
            api_key[:6],
            api_key[-4:],
        )

        if CohereEmbeddings is None:
            msg = "langchain_cohere não está instalado"
            raise ImportError(msg)

        # NOTE: do NOT wrap in SecretStr here.
        # langchain-core's get_from_dict_or_env calls str(SecretStr) which returns
        # "**********" instead of the actual value, causing a 401 from Cohere.
        # Passing the plain string bypasses that branch entirely.
        embeddings_model = CohereEmbeddings(  # ty: ignore[missing-argument]
            cohere_api_key=api_key,  # ty: ignore[invalid-argument-type]
            model=self.config.embedding_model,
        )

        # embed_query é bloqueante (HTTP síncrono ~1-2s por chunk).
        # asyncio.to_thread() move para a thread pool do SO, liberando o event loop
        # para o spinner da UI e demais tarefas async enquanto a API responde.
        return await asyncio.to_thread(embeddings_model.embed_query, text)

    async def _write_to_lancedb(
        self, record: EmbeddingQueueRecord, vector: list[float]
    ) -> None:
        """Escreve documento em LanceDB (idempotente via queue_id).

        Args:
            record: Registro com metadata
            vector: Embedding vector

        Raises:
            ImportError: Se lancedb não estiver instalado
        """
        if lancedb is None:
            msg = "lancedb não está instalado"
            raise ImportError(msg)

        if self.config.lancedb_dir is None:
            msg = "lancedb_dir not configured"
            raise RuntimeError(msg)
        db = await lancedb.connect_async(str(Path(self.config.lancedb_dir)))

        # Schema para documento
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), len(vector))),
                pa.field("text", pa.string()),
                pa.field("metadata", pa.string()),
            ]
        )

        # Abrir ou criar tabela
        try:
            table = await db.open_table(str(record.collection))
        except Exception:
            table = await db.create_table(str(record.collection), schema=schema)
            logger.info(
                "lancedb_table_created",
                extra={"collection": record.collection},
            )

        # Adicionar documento (queue_id como document ID para idempotência)
        doc = {
            "id": record.queue_id,  # Chave primária = queue_id
            "vector": vector,
            "text": record.text,
            "metadata": record.doc_metadata or "{}",
        }

        # Protege escrita em LanceDB com semaphore(1) contra race conditions
        async with self.lancedb_semaphore:
            await table.add([doc])

        logger.debug(
            "lancedb_document_written",
            extra={
                "queue_id": record.queue_id,
                "collection": record.collection,
            },
        )


# Singleton global com lock
_worker: BackgroundEmbeddingWorker | None = None
_worker_lock: asyncio.Lock = asyncio.Lock()


async def get_background_worker() -> BackgroundEmbeddingWorker:
    """Obtém ou cria instância singleton do worker (thread-safe).

    Returns:
        Instância do BackgroundEmbeddingWorker

    Note:
        Usa asyncio.Lock para evitar race condition em múltiplas
        inicializações simultâneas.
    """
    global _worker

    if _worker is not None:
        return _worker

    async with _worker_lock:
        # Double-check após adquirir lock
        if _worker is None:
            _worker = BackgroundEmbeddingWorker()

    return _worker
