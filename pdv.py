"""PDV (ponto de venda) simulado.

No produto real, o código seria "digitado" no PDV da loja por emulação de
teclado. Aqui mostramos a sequência de teclas que seria enviada e mantemos
o cupom em memória, salvando-o em CSV ao finalizar a venda.
"""

import csv
from datetime import datetime
from pathlib import Path


def brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_qtd(qtd: float, unidade: str) -> str:
    return f"{qtd:.3f} kg".replace(".", ",") if unidade == "kg" else f"{int(qtd)} un"


class PDVSimulado:
    def __init__(self, pasta_cupons: Path):
        self.pasta = Path(pasta_cupons)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.itens: list[dict] = []

    def registrar(self, item: dict, quantidade: float) -> dict:
        valor = round(item["preco"] * quantidade, 2)
        registro = {
            "seq": len(self.itens) + 1,
            "codigo": item["codigo"],
            "descricao": f"{item['nome']} {item['variedade']}",
            "unidade": item["unidade"],
            "quantidade": quantidade,
            "preco_unit": item["preco"],
            "valor": valor,
        }
        self.itens.append(registro)
        qtd_tecla = f"{quantidade:.3f}".replace(".", ",") if item["unidade"] == "kg" else str(int(quantidade))
        print(f"\n⌨️  [emulação de teclado → PDV] {item['codigo']} <TAB> {qtd_tecla} <ENTER>")
        return registro

    def cancelar_ultimo(self) -> dict | None:
        return self.itens.pop() if self.itens else None

    @property
    def total(self) -> float:
        return round(sum(i["valor"] for i in self.itens), 2)

    def cupom_texto(self) -> str:
        linhas = ["=" * 58, "       HORTIFRUTI VISION — CUPOM (SIMULAÇÃO)", "=" * 58]
        if not self.itens:
            linhas.append("  (nenhum item registrado)")
        for i in self.itens:
            linhas.append(f"{i['seq']:>2} {i['codigo']}  {i['descricao'][:24]:<24} "
                          f"{fmt_qtd(i['quantidade'], i['unidade']):>9} {brl(i['valor']):>11}")
            unid = "kg" if i["unidade"] == "kg" else "un"
            linhas.append(f"{'':8}{brl(i['preco_unit'])}/{unid}")
        linhas += ["-" * 58, f"{'TOTAL':<44}{brl(self.total):>14}", "=" * 58]
        return "\n".join(linhas)

    def finalizar(self) -> Path | None:
        if not self.itens:
            return None
        caminho = self.pasta / f"cupom_{datetime.now():%Y%m%d_%H%M%S}.csv"
        with open(caminho, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(self.itens[0]))
            w.writeheader()
            w.writerows(self.itens)
        self.itens = []
        return caminho
