"""Ferramentas (ações) disponíveis ao agente ReAct.

Princípio de segurança: o LLM escolhe O QUE fazer, mas números críticos
(código, preço, peso, valor) vêm sempre de fontes externas — catálogo,
balança e PDV — e nunca do texto gerado pelo modelo.
"""

from catalogo import Catalogo
from operador import OperadorTerminal
from pdv import PDVSimulado, brl, fmt_qtd


class Ferramentas:
    def __init__(self, catalogo: Catalogo, pdv: PDVSimulado, operador: OperadorTerminal):
        self.catalogo = catalogo
        self.pdv = pdv
        self.operador = operador
        self.reiniciar()

    def reiniciar(self) -> None:
        """Limpa o estado entre um produto e outro."""
        self.ultimo_peso: float | None = None
        self.ultima_quantidade: int | None = None
        self.registrado = False

    # Descrições mostradas ao LLM no prompt do agente
    DESCRICOES = {
        "buscar_catalogo": 'Busca produtos no catálogo da loja (RAG). Entrada: {"consulta": "texto"}. '
                           "Retorna código, nome, variedade, unidade de venda (kg/un), preço e aparência.",
        "perguntar_operador": 'Pergunta ao operador do caixa quando houver dúvida. '
                              'Entrada: {"pergunta": "texto", "opcoes": ["opção 1", "opção 2"]}.',
        "ler_balanca": "Lê o peso atual da balança (para itens vendidos por kg). Entrada: {}.",
        "informar_quantidade": 'Pede ao operador a quantidade (para itens vendidos por unidade). '
                               'Entrada: {"sugestao": 1}.',
        "registrar_pdv": 'Registra o item no PDV usando o último peso/quantidade lido. '
                         'Entrada: {"codigo": "1001"}.',
    }

    def executar(self, nome: str, args: dict) -> str:
        metodo = getattr(self, nome, None)
        if nome not in self.DESCRICOES or metodo is None:
            return f"ERRO: ferramenta '{nome}' não existe. Use uma de: {', '.join(self.DESCRICOES)}."
        try:
            return metodo(**args)
        except TypeError as e:
            return f"ERRO: parâmetros inválidos para {nome}: {e}"

    # ------------------------------------------------------------ ferramentas
    def buscar_catalogo(self, consulta: str = "") -> str:
        if not consulta.strip():
            return "ERRO: informe uma consulta."
        resultados = self.catalogo.buscar(consulta, k=4)
        linhas = [f"Resultados do catálogo para '{consulta}':"]
        for r in resultados:
            unidade = "kg" if r["unidade"] == "kg" else "unidade"
            linhas.append(
                f"- código {r['codigo']} | {r['nome']} {r['variedade']} | vendido por {unidade} | "
                f"{brl(r['preco'])}/{r['unidade']} | aparência: {r['descricao_visual']} "
                f"| relevância {r['pontuacao']}"
            )
        return "\n".join(linhas)

    def perguntar_operador(self, pergunta: str = "", opcoes: list | None = None) -> str:
        opcoes = [str(o) for o in (opcoes or [])] or ["Sim", "Não"]
        resposta = self.operador.perguntar_opcao(pergunta or "Confirme o produto:", opcoes)
        return f"O operador respondeu: {resposta}"

    def ler_balanca(self) -> str:
        self.ultimo_peso = self.operador.ler_peso()
        return f"Balança estável: {fmt_qtd(self.ultimo_peso, 'kg')}."

    def informar_quantidade(self, sugestao: int = 1) -> str:
        try:
            sugestao = int(sugestao)
        except (TypeError, ValueError):
            sugestao = 1
        self.ultima_quantidade = self.operador.ler_quantidade(sugestao)
        return f"Quantidade informada: {self.ultima_quantidade} unidade(s)."

    def registrar_pdv(self, codigo: str = "") -> str:
        if self.registrado:
            return "ERRO: este produto já foi registrado. Finalize com a Resposta Final."
        item = self.catalogo.obter(codigo)
        if item is None:
            return f"ERRO: código '{codigo}' não existe no catálogo. Use buscar_catalogo."
        if item["unidade"] == "kg":
            if self.ultimo_peso is None:
                return "ERRO: item vendido por kg. Use ler_balanca antes de registrar."
            quantidade = self.ultimo_peso
        else:
            if self.ultima_quantidade is None:
                return "ERRO: item vendido por unidade. Use informar_quantidade antes de registrar."
            quantidade = self.ultima_quantidade
        reg = self.pdv.registrar(item, quantidade)
        self.registrado = True
        return (f"Item {reg['seq']} registrado no PDV: {reg['codigo']} {reg['descricao']} — "
                f"{fmt_qtd(quantidade, item['unidade'])} x {brl(item['preco'])} = {brl(reg['valor'])}. "
                f"Total parcial do cupom: {brl(self.pdv.total)}.")
