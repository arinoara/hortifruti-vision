"""Etapa 2 — Agente ReAct (Pensamento → Ação → Observação).

Implementação explícita do ciclo descrito no Capítulo 4 da apostila: o LLM
escreve um Pensamento e escolhe uma Ação; o programa executa a ferramenta e
devolve a Observação; o ciclo se repete até a Resposta Final.
"""

import json
import re

from openai import OpenAI

from ferramentas import Ferramentas

PROMPT_SISTEMA = """Você é o agente de caixa do Hortifruti Vision. Você recebe a identificação
visual de um produto (feita por outro módulo) e deve registrá-lo corretamente no PDV.

Ferramentas disponíveis:
{ferramentas}

Use EXATAMENTE este formato, com UMA ação por vez, e então pare:
Pensamento: seu raciocínio sobre o que já sabe e o que falta
Ação: nome_da_ferramenta
Entrada da Ação: {{"parametro": "valor"}}

O sistema responderá com:
Observação: resultado da ferramenta

Quando o trabalho estiver concluído (ou não puder ser feito), escreva:
Pensamento: conclusão
Resposta Final: mensagem curta para o operador

Regras obrigatórias:
1. SEMPRE use buscar_catalogo antes de registrar. O código deve vir do catálogo, nunca da sua memória.
2. Use perguntar_operador se a confiança visual for menor que {confianca_minima}, ou se o catálogo
   tiver mais de uma variedade compatível que a imagem não permita distinguir. Ofereça como opções
   as variedades do catálogo (nome + variedade).
3. Item vendido por kg: chame ler_balanca antes de registrar_pdv.
   Item vendido por unidade: chame informar_quantidade (use a quantidade visível como sugestão).
4. Se o produto não existir no catálogo, NÃO registre; explique na Resposta Final.
5. Registre apenas um item por identificação. Nunca escreva a Observação você mesmo."""

RE_ACAO = re.compile(r"Ação:\s*([a-zA-Z_]+)")
RE_ENTRADA = re.compile(r"Entrada da Ação:\s*(\{.*\})", re.DOTALL)
RE_FINAL = re.compile(r"Resposta Final:\s*(.*)", re.DOTALL)


class AgenteReAct:
    def __init__(self, cliente: OpenAI, modelo: str, ferramentas: Ferramentas,
                 max_passos: int = 8, confianca_minima: float = 0.7):
        self.cliente = cliente
        self.modelo = modelo
        self.ferramentas = ferramentas
        self.max_passos = max_passos
        descricoes = "\n".join(f"- {n}: {d}" for n, d in ferramentas.DESCRICOES.items())
        self.prompt_sistema = PROMPT_SISTEMA.format(ferramentas=descricoes, confianca_minima=confianca_minima)

    def _chamar_llm(self, mensagens: list[dict]) -> str:
        resp = self.cliente.chat.completions.create(
            model=self.modelo, messages=mensagens, temperature=0, max_tokens=500,
            stop=["Observação:", "\nObservação"],
        )
        texto = resp.choices[0].message.content or ""
        # alguns modelos ignoram "stop": cortamos qualquer Observação inventada
        return texto.split("Observação:")[0].strip()

    @staticmethod
    def _ler_entrada(texto: str) -> dict:
        m = RE_ENTRADA.search(texto)
        if not m:
            return {}
        bruto = m.group(1)
        # tenta do maior para o menor trecho entre chaves
        for fim in range(len(bruto), 0, -1):
            if bruto[fim - 1] == "}":
                try:
                    valor = json.loads(bruto[:fim])
                    return valor if isinstance(valor, dict) else {}
                except json.JSONDecodeError:
                    continue
        return {}

    def _mostrar_passo(self, texto: str) -> None:
        op = self.ferramentas.operador
        for linha in texto.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith("Pensamento"):
                op.mostrar("💭 " + linha, "pensamento")
            elif linha.startswith(("Ação", "Entrada da Ação")):
                op.mostrar("🔧 " + linha, "acao")
            elif linha.startswith("Resposta Final"):
                op.mostrar("✅ " + linha, "final")
            else:
                op.mostrar("   " + linha, "pensamento")

    def executar(self, identificacao: dict) -> str:
        self.ferramentas.reiniciar()
        op = self.ferramentas.operador
        mensagens = [
            {"role": "system", "content": self.prompt_sistema},
            {"role": "user", "content": "Identificação visual recebida:\n"
                                        + json.dumps(identificacao, ensure_ascii=False, indent=2)},
        ]
        for passo in range(1, self.max_passos + 1):
            op.mostrar(f"\n── Passo {passo} " + "─" * 40, "info")
            texto = self._chamar_llm(mensagens)
            self._mostrar_passo(texto)
            mensagens.append({"role": "assistant", "content": texto})

            acao = RE_ACAO.search(texto)
            final = RE_FINAL.search(texto)
            # Se houver ação antes da resposta final, a ação tem prioridade
            if final and (not acao or final.start() < acao.start()):
                return final.group(1).strip()
            if not acao:
                observacao = ("Formato inválido. Responda com 'Pensamento:', 'Ação:' e "
                              "'Entrada da Ação:' ou com 'Resposta Final:'.")
            else:
                observacao = self.ferramentas.executar(acao.group(1), self._ler_entrada(texto))

            op.mostrar("👁️  Observação: " + observacao, "observacao")
            mensagens.append({"role": "user", "content": f"Observação: {observacao}"})

        return "Limite de passos atingido sem conclusão. Registre o item manualmente."
