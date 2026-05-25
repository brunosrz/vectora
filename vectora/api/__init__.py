"""Vectora API — FastAPI + SSE streaming.

Ponto de entrada: `vectora/api/server.py:create_app()`

Uso:
    # Modo chat (com frontend estático):
    from vectora.api.server import create_app
    app = create_app(serve_static=True)

    # Modo headless (só API):
    app = create_app(serve_static=False)
"""
