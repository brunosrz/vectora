"""Pipeline de ingestão/indexação RAG de ponta a ponta.

Fila assíncrona (``queue.py``) → worker de embeddings (``background.py``) →
invalidação de cache (``cache_embeddings.py``/``cache_sync.py``) → curadoria
de conhecimento pós-ingestão (``curator.py``). ``rag_ingest.py`` é o ponto de
entrada usado pelo handler HTTP de ingestão de pasta.
"""
