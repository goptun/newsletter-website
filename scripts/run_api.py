#!/usr/bin/env python3
"""Sobe a API localmente com uvicorn — ver tasks.md 1.1.

Uso:
    python scripts/run_api.py
"""

import sys
from pathlib import Path

# Necessário pro processo de reload do uvicorn (que reimporta "app.api.main"
# num subprocesso próprio) encontrar o pacote quando este script é chamado
# como `python scripts/run_api.py` de fora da raiz do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        app_dir=str(Path(__file__).resolve().parent.parent),
    )
