"""RAG: catálogo da loja indexado no ChromaDB.

Cada produto do CSV vira um documento de texto (nome, variedade, sinônimos
regionais e descrição visual). O ChromaDB gera os embeddings localmente
(modelo all-MiniLM-L6-v2 em ONNX, sem custo de API) e faz a busca por
similaridade vetorial. O agente usa essa busca para obter o código e o preço
REAIS da loja, em vez de confiar na memória do LLM.
"""

import csv
import hashlib
import unicodedata
from pathlib import Path

import chromadb

NOME_COLECAO = "catalogo_hortifruti"


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


class Catalogo:
    def __init__(self, caminho_csv: Path, pasta_chroma: Path):
        self.caminho_csv = Path(caminho_csv)
        self.itens = self._carregar_csv()
        cliente = chromadb.PersistentClient(path=str(pasta_chroma))
        self.colecao = self._indexar(cliente)

    # ------------------------------------------------------------------ dados
    def _carregar_csv(self) -> dict[str, dict]:
        itens = {}
        with open(self.caminho_csv, encoding="utf-8") as f:
            for linha in csv.DictReader(f):
                linha["preco"] = float(linha["preco"])
                itens[linha["codigo"]] = linha
        return itens

    @staticmethod
    def _documento(item: dict) -> str:
        sinonimos = item["sinonimos"].replace(";", ", ")
        return (
            f"{item['nome']} {item['variedade']}. "
            f"Também conhecido como: {sinonimos}. "
            f"Aparência: {item['descricao_visual']}. "
            f"Vendido por {'quilo' if item['unidade'] == 'kg' else 'unidade'}."
        )

    # -------------------------------------------------------------- indexação
    def _indexar(self, cliente):
        """(Re)cria o índice apenas quando o CSV muda (controle por hash)."""
        hash_csv = hashlib.md5(self.caminho_csv.read_bytes()).hexdigest()
        try:
            colecao = cliente.get_collection(NOME_COLECAO)
            if (colecao.metadata or {}).get("hash_csv") == hash_csv:
                return colecao
            cliente.delete_collection(NOME_COLECAO)
        except Exception:
            pass  # coleção ainda não existe

        print("[RAG] Indexando catálogo no ChromaDB (gerando embeddings)...")
        colecao = cliente.create_collection(NOME_COLECAO, metadata={"hash_csv": hash_csv})
        codigos = list(self.itens)
        colecao.add(
            ids=codigos,
            documents=[self._documento(self.itens[c]) for c in codigos],
            metadatas=[{"nome": self.itens[c]["nome"], "unidade": self.itens[c]["unidade"]} for c in codigos],
        )
        print(f"[RAG] {len(codigos)} produtos indexados.")
        return colecao

    # ------------------------------------------------------------------ busca
    def buscar(self, consulta: str, k: int = 4) -> list[dict]:
        """Busca semântica (ChromaDB) com um pequeno reforço lexical.

        O modelo de embeddings padrão é treinado principalmente em inglês;
        o reforço lexical (palavras em comum com nome/sinônimos) melhora a
        ordenação para termos em português como "taiti" ou "nanica".
        """
        n = min(len(self.itens), max(k * 3, 10))
        res = self.colecao.query(query_texts=[consulta], n_results=n)
        termos = {t for t in _normalizar(consulta).replace(",", " ").split() if len(t) > 2}

        candidatos = []
        for codigo, distancia in zip(res["ids"][0], res["distances"][0]):
            item = self.itens[codigo]
            alvo = _normalizar(f"{item['nome']} {item['variedade']} {item['sinonimos']}")
            acertos = sum(1 for t in termos if t in alvo)
            similaridade = max(0.0, 1 - distancia / 2)  # distância L2² de vetores normalizados
            pontuacao = similaridade + 0.25 * acertos
            candidatos.append({**item, "similaridade": round(similaridade, 3), "pontuacao": round(pontuacao, 3)})

        candidatos.sort(key=lambda c: c["pontuacao"], reverse=True)
        return candidatos[:k]

    def obter(self, codigo: str) -> dict | None:
        return self.itens.get(str(codigo).strip())
