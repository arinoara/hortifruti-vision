"""Etapa 1 — Identificação visual com LLM multimodal (Zero-Shot Prompting).

O LLM recebe a foto e devolve um JSON estruturado. Ele NÃO decide código
nem preço: essas informações virão do catálogo (RAG) na etapa do agente.
"""

import json
import re
from pathlib import Path

from openai import OpenAI

from camera import imagem_para_data_url

PROMPT_VISAO = """Você é o módulo de visão computacional de um caixa de hortifruti no Brasil.
Analise a imagem e identifique o produto hortifruti principal.

Descreva com atenção as características visuais que diferenciam variedades
(ex.: banana prata x caturra (nanica), limão taiti x siciliano, maçã gala x fuji):
cor, formato, textura da casca, tamanho relativo.

Responda SOMENTE com um JSON válido, sem texto extra, neste formato:
{
  "tem_produto": true,
  "produto": "nome genérico em português, ex.: banana",
  "variedade": "variedade provável ou null se não for possível dizer",
  "confianca": 0.0,
  "caracteristicas": "cor, formato, casca, tamanho",
  "alternativas": ["outras possibilidades plausíveis"],
  "quantidade_visivel": 1,
  "observacao": "algo relevante (ex.: mais de um tipo de produto, embalagem) ou vazio"
}

Regras:
- "confianca" de 0 a 1 refere-se à identificação produto + variedade.
- Se não houver hortifruti na imagem, use "tem_produto": false.
- Não invente códigos nem preços."""


def _extrair_json(texto: str) -> dict:
    texto = re.sub(r"```(?:json)?", "", texto)
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError(f"Resposta sem JSON: {texto[:200]}")
    return json.loads(texto[inicio:fim + 1])


def identificar(cliente: OpenAI, modelo: str, caminho_imagem: Path) -> dict:
    resposta = cliente.chat.completions.create(
        model=modelo,
        temperature=0,
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT_VISAO},
                {"type": "image_url", "image_url": {"url": imagem_para_data_url(caminho_imagem)}},
            ],
        }],
    )
    dados = _extrair_json(resposta.choices[0].message.content or "")
    dados.setdefault("tem_produto", True)
    dados["confianca"] = float(dados.get("confianca") or 0)
    return dados
