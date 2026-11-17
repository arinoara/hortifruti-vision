"""Ferramentas (ações) disponíveis ao agente ReAct.

Princípio de segurança: o LLM escolhe O QUE fazer, mas números críticos
(código, preço, peso, valor) vêm sempre de fontes externas — catálogo,
balança e PDV — e nunca do texto gerado pelo modelo.
"""

from catalogo import Catalogo
from operador import OperadorTerminal
from pdv import PDVSimulado, brl, fmt_qtd


class Ferramentas:
    def __init__(self, catalogo: Catalogo, pdv: PDVSimulado, operador: OperadorTerminal,
                 confianca_minima: float = 0.7, confirmar_variedade: str = "auto"):
        self.catalogo = catalogo
        self.pdv = pdv
        self.operador = operador
        self.confianca_minima = confianca_minima
        self.confirmar_variedade = confirmar_variedade  # auto | sempre | nunca
        self.reiniciar()

    def reiniciar(self, identificacao: dict | None = None) -> None:
        """Limpa o estado entre um produto e outro."""
        self.identificacao = identificacao or {}
        self.ultimo_peso: float | None = None
        self.ultima_quantidade: int | None = None
        self.registrado = False
        self.operador_consultado = False

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
        self.operador_consultado = True
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
        elif self.ultima_quantidade is None:
            return "ERRO: item vendido por unidade. Use informar_quantidade antes de registrar."

        sugerido = item
        if self._precisa_confirmar(item):
            item = self._confirmar_com_operador(item)
            if item is None:
                self.registrado = True  # encerra este produto sem registrar
                return ("O operador CANCELOU o item; nada foi registrado. "
                        "Encerre com a Resposta Final informando o cancelamento.")

        quantidade = self._quantidade_para(item)
        reg = self.pdv.registrar(item, quantidade)
        self.registrado = True
        aviso = ""
        if item["codigo"] != sugerido["codigo"]:
            aviso = (f" ATENÇÃO: o operador corrigiu a sugestão {sugerido['codigo']} "
                     f"({sugerido['nome']} {sugerido['variedade']}) para este item.")
        return (f"Item {reg['seq']} registrado no PDV: {reg['codigo']} {reg['descricao']} — "
                f"{fmt_qtd(quantidade, item['unidade'])} x {brl(item['preco'])} = {brl(reg['valor'])}. "
                f"Total parcial do cupom: {brl(self.pdv.total)}.{aviso}")

    # ------------------------------------------- confirmação de variedade
    def _variedades(self, item: dict) -> list[dict]:
        """Todas as variedades do mesmo produto no catálogo (ex.: todas as bananas)."""
        return [i for i in self.catalogo.itens.values() if i["nome"] == item["nome"]]

    def _precisa_confirmar(self, item: dict) -> bool:
        """Regra determinística (no código, não no LLM) para pedir confirmação."""
        if self.confirmar_variedade == "nunca" or self.operador_consultado:
            return False
        if len(self._variedades(item)) < 2:
            return False
        if self.confirmar_variedade == "sempre":
            return True
        try:
            confianca = float(self.identificacao.get("confianca", 0))
        except (TypeError, ValueError):
            confianca = 0.0
        alternativas = [a for a in (self.identificacao.get("alternativas") or []) if str(a).strip()]
        return confianca < self.confianca_minima or bool(alternativas)

    def _confirmar_com_operador(self, item: dict) -> dict | None:
        opcoes = self._variedades(item)
        pergunta = f"a IA sugeriu {item['nome']} {item['variedade']}. Qual é o produto?"
        rotulo = "sugestão da IA"
        while True:
            padrao = next((i for i, o in enumerate(opcoes) if o["codigo"] == item["codigo"]), 0)
            escolha = self.operador.escolher_item(pergunta, opcoes, padrao, rotulo)
            if not isinstance(escolha, str):
                return escolha  # item escolhido ou None (cancelado)
            # texto livre: nova busca no catálogo (RAG) com o que o operador digitou
            opcoes = self.catalogo.buscar(escolha, k=4)
            pergunta = f"resultados do catálogo para '{escolha}':"
            rotulo = "mais provável"

    def _quantidade_para(self, item: dict) -> float | int:
        """Peso ou quantidade já lidos; se o operador trocou para um item com outra
        unidade de venda, lê a medida que falta direto da balança/operador."""
        if item["unidade"] == "kg":
            if self.ultimo_peso is None:
                self.ultimo_peso = self.operador.ler_peso()
            return self.ultimo_peso
        if self.ultima_quantidade is None:
            sugestao = self.identificacao.get("quantidade_visivel") or 1
            self.ultima_quantidade = self.operador.ler_quantidade(int(sugestao))
        return self.ultima_quantidade
