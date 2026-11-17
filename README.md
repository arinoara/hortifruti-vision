# Hortifruti Vision — MVP (ELT 577)

Protótipo funcional do **Hortifruti Vision**, solução apresentada no pitch da
disciplina: **a câmera reconhece, a IA identifica e o PDV recebe o código** do
hortifruti, sem digitação manual pelo operador do caixa.

Neste MVP:

| Componente do produto real | Como está no MVP |
|---|---|
| Câmera sobre a balança | **Webcam do computador** (OpenCV) ou arquivo de imagem |
| Modelo de IA treinado para hortifruti | **LLM multimodal** via OpenRouter (validação do conceito, sem treinar modelo próprio) |
| Cadastro de produtos da loja | `dados/catalogo.csv` (44 itens) indexado no **ChromaDB** |
| Balança Toledo | **Balança simulada** (o operador digita o peso, ou Enter gera um peso aleatório) |
| PDV da loja (emulação de teclado) | **PDV simulado**: mostra as teclas que seriam enviadas e gera o cupom em CSV |

---

## Funcionalidade implementada

1. O operador captura a foto do produto pela webcam.
2. **Identificação visual:** um LLM multimodal analisa a imagem e devolve um
   JSON com produto, variedade provável, confiança, características e alternativas.
3. **Agente ReAct:** um segundo passo, só de texto, raciocina e age em ciclos
   *Pensamento → Ação → Observação* usando estas ferramentas:
   - `buscar_catalogo`: **RAG**, busca semântica no catálogo da loja (código, preço, unidade de venda);
   - `perguntar_operador`: pede confirmação quando a confiança é baixa ou a variedade é ambígua (ex.: limão taiti × siciliano);
   - `ler_balanca`: lê o peso (itens vendidos por kg);
   - `informar_quantidade`: lê a quantidade (itens vendidos por unidade);
   - `registrar_pdv`: envia o item ao PDV simulado.
4. O item entra no cupom, e a venda pode ser finalizada e salva em `cupons/`.

**Segurança contra alucinação:** o LLM decide *o que fazer*, mas **código,
preço, peso e valor nunca vêm do texto gerado pelo modelo**. Eles vêm do
catálogo, da balança e do PDV. A ferramenta `registrar_pdv` recusa códigos
inexistentes e exige a leitura de peso ou quantidade antes do registro.

**Confirmação de variedade pelo operador:** antes de registrar, se o produto
tiver mais de uma variedade no catálogo (ex.: banana prata, caturra/nanica,
maçã, da terra) e a identificação visual tiver dúvida (confiança abaixo de
`CONFIANCA_MINIMA` **ou** alternativas listadas), o próprio código, e não o
LLM, mostra ao operador todas as variedades do catálogo para escolher.
Enter confirma a sugestão da IA, um número escolhe outra, `0` cancela o item
e um texto livre (ex.: `caturra`) faz uma nova busca no RAG. Essa regra é
controlada por `CONFIRMAR_VARIEDADE` no `.env`.

```
[Webcam / arquivo] ──► Etapa 1: LLM multimodal (Zero-Shot, saída JSON)
                                  │
                                  ▼
                       Etapa 2: Agente ReAct  ◄──── OpenRouter (SDK OpenAI)
              ┌──────────┬────────┴───────┬──────────────┬─────────────┐
              ▼          ▼                ▼              ▼             ▼
        buscar_catalogo perguntar_   ler_balanca   informar_     registrar_pdv
        (RAG/ChromaDB)  operador     (simulada)    quantidade    (PDV simulado)
                                                                       │
                                                                       ▼
                                                                Cupom (CSV)
```

## Técnicas de LLM utilizadas

| Técnica (capítulo) | Onde está |
|---|---|
| **Engenharia de Prompt — Zero-Shot** (Cap. 2) | `visao.py`: prompt com saída JSON estruturada, sem exemplos |
| **ReAct** (Cap. 4) | `agente.py`: ciclo Pensamento → Ação → Observação implementado explicitamente, com 5 ferramentas em `ferramentas.py` |
| **RAG** (Cap. 5) | `catalogo.py`: catálogo indexado no **ChromaDB** com embeddings locais (all-MiniLM-L6-v2), consultado pela ferramenta `buscar_catalogo` |

---

## Instalação

Requisitos: **Python 3.12+**, webcam (opcional) e conexão com a internet.

### Opção A: com `pip` (venv padrão do Python)

```bash
# 1. Entre na pasta do projeto
cd hortifruti_vision

# 2. Crie e ative um ambiente virtual
python3.12 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# 3. Instale as dependências
python -m pip install -r requirements.txt
```

### Opção B: com [`uv`](https://docs.astral.sh/uv/)

```bash
cd hortifruti_vision
uv venv --python 3.12 .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows
uv pip install -r requirements.txt
```

> **Erro `Comando 'pip' não encontrado`?** Provavelmente o `.venv` foi criado
> com o `uv`, que não coloca o `pip` dentro do ambiente. Não instale o `python3-pip` do sistema. Use
> `uv pip install -r requirements.txt` ou, se preferir o pip, rode
> `python -m ensurepip` antes de `python -m pip install -r requirements.txt`.

Dependências (`requirements.txt`): `openai` (SDK usado com o OpenRouter),
`python-dotenv`, `chromadb` e `opencv-python`.

### Chave de API (arquivo `.env`)

O programa lê a chave do arquivo `.env`, que **não** está no código e está no `.gitignore`.

- **Professor:** o `.env` entregue no .zip **já contém uma chave de teste**
  com limite de crédito. Não é preciso fazer nada.
- **Para usar a sua própria chave:** copie o modelo e edite:
  ```bash
  cp .env.example .env
  # edite .env e preencha OPENROUTER_API_KEY=sk-or-...
  ```
  As chaves são criadas em https://openrouter.ai/keys.

Outras variáveis do `.env`: `OPENROUTER_MODEL` (padrão `google/gemini-2.5-flash-lite`,
que precisa aceitar imagem), `CAMERA_INDICE` (padrão 0), `CONFIANCA_MINIMA` (padrão 0.7),
`MAX_PASSOS_REACT` (padrão 8) e `CONFIRMAR_VARIEDADE` (padrão `auto`:
pergunta só quando há dúvida; `sempre`: pergunta em todo produto com mais de
uma variedade; `nunca`: confia na IA).

> **Primeira execução:** o ChromaDB baixa automaticamente o modelo de
> embeddings (~80 MB, uma única vez) e indexa o catálogo na pasta `.chroma/`.

---

## Execução

```bash
python main.py
```

Menu:

```
[1] Capturar produto pela câmera   → abre a webcam; ESPAÇO captura, ESC cancela
[2] Usar arquivo de imagem         → informe o caminho de uma foto (.jpg/.png)
[3] Ver cupom atual
[4] Cancelar último item
[5] Finalizar venda (salvar cupom) → salva em cupons/cupom_AAAAMMDD_HHMMSS.csv
[0] Sair
```

Outras formas de execução:

```bash
python main.py --imagem imagens_exemplo/banana.jpg   # processa a imagem e abre o menu
python main.py --buscar "limão verde"                # testa só o RAG (sem custo de API)
```

Sem webcam, use a opção **[2]** ou `--imagem` com fotos da pasta
`imagens_exemplo/`.

---

## Exemplos de uso

### 1. Teste do RAG (sem API)

```
$ python main.py --buscar "limão taiti"
1030  Limão Taiti                     kg  R$ 4.49  relevância=1.167
1032  Limão Cravo                     kg  R$ 5.49  relevância=0.858
1031  Limão Siciliano                 kg  R$ 12.99  relevância=0.696
```

### 2. Produto ambíguo com confirmação do operador (trecho real da saída)

```
🧠 Etapa 1 — Identificação visual
{ "produto": "limão", "variedade": null, "confianca": 0.55, ... }

🤖 Etapa 2 — Agente ReAct (RAG + ferramentas)
── Passo 1 ──
💭 Pensamento: preciso buscar limão no catálogo.
🔧 Ação: buscar_catalogo
🔧 Entrada da Ação: {"consulta": "limão verde"}
👁️  Observação: - código 1030 | Limão Taiti | vendido por kg | R$ 4,49/kg ...
── Passo 2 ──
💭 Pensamento: confiança baixa, há várias variedades.
🔧 Ação: perguntar_operador
🙋 PERGUNTA AO OPERADOR: Qual variedade?   [1] Limão Taiti  [2] Limão Siciliano
── Passo 3 ──
🔧 Ação: ler_balanca
⚖️  BALANÇA SIMULADA — digite o peso em kg: 0,532
── Passo 4 ──
🔧 Ação: registrar_pdv   {"codigo": "1030"}
⌨️  [emulação de teclado → PDV] 1030 <TAB> 0,532 <ENTER>
✅ Resposta Final: Limão Taiti registrado.

 1 1030  Limão Taiti               0,532 kg     R$ 2,39
TOTAL                                              R$ 2,39
```

### Sugestões de teste

| Produto na frente da câmera | Comportamento esperado |
|---|---|
| Banana, maçã, laranja, tomate | Identifica → busca no catálogo → lê a balança → registra |
| Limão (taiti × siciliano), maçã (gala × fuji) | Se houver dúvida, **pergunta ao operador** |
| Abacaxi, alface, coco | Item por **unidade**: pede a quantidade em vez do peso |
| Objeto que não é hortifruti (caneca, celular) | "Nenhum hortifruti identificado" |
| Produto fora do catálogo (ex.: pitaya) | Agente **não registra** e explica o motivo |

---

## Estrutura do projeto

```
hortifruti_vision/
├── main.py            # CLI e orquestração do fluxo
├── config.py          # .env e cliente OpenRouter (SDK OpenAI)
├── camera.py          # webcam (OpenCV) e preparo da imagem
├── visao.py           # Etapa 1: identificação com LLM multimodal (Zero-Shot)
├── agente.py          # Etapa 2: agente ReAct
├── ferramentas.py     # ferramentas do agente
├── catalogo.py        # RAG com ChromaDB
├── operador.py        # interação com o operador (terminal)
├── pdv.py             # PDV simulado e cupom
├── dados/catalogo.csv # catálogo da loja (código, preço, unidade, sinônimos, aparência)
├── imagens_exemplo/   # fotos para teste sem webcam
├── requirements.txt
├── .env.example       # modelo de configuração
└── .gitignore         # ignora .env, .venv, .chroma, capturas e cupons
```

## Limitações e próximos passos

- O MVP usa um LLM de uso geral. No produto, o plano é um modelo treinado
  com imagens coletadas nas lojas, rodando localmente no minicomputador
  (menor latência e sem custo por imagem).
- A balança e o PDV são simulados. A integração real será por porta serial
  (balança) e emulação de teclado (PDV).
- O catálogo é fictício. No piloto, ele seria importado do cadastro da loja.
