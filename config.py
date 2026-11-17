"""Configurações gerais e criação do cliente LLM (OpenRouter via SDK da OpenAI)."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODELO = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")

CATALOGO_CSV = BASE_DIR / "dados" / "catalogo.csv"
CHROMA_DIR = BASE_DIR / ".chroma"
CUPONS_DIR = BASE_DIR / "cupons"
CAPTURAS_DIR = BASE_DIR / "capturas"

CAMERA_INDICE = int(os.getenv("CAMERA_INDICE", "0"))
MAX_PASSOS_REACT = int(os.getenv("MAX_PASSOS_REACT", "8"))
CONFIANCA_MINIMA = float(os.getenv("CONFIANCA_MINIMA", "0.7"))


def criar_cliente() -> OpenAI:
    """Cria o cliente OpenAI apontando para o OpenRouter (API compatível)."""
    chave = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not chave or chave.lower().startswith("coloque"):
        sys.exit(
            "ERRO: defina OPENROUTER_API_KEY no arquivo .env "
            "(copie .env.example para .env e cole sua chave)."
        )
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=chave,
        default_headers={"X-Title": "Hortifruti Vision (MVP ELT 577)"},
    )
