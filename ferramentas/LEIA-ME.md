# Ferramentas de atualização do Lex Vade Mecum

Objetivo: os artigos publicados em `leis/` devem espelhar sempre o texto vigente e exato do Portal da Legislação do Planalto.

## Por que a extração é feita pelo navegador

O Planalto recusa conexões automatizadas (downloads por linha de comando ou de servidores em nuvem). Por isso, o texto é extraído de uma página aberta em um navegador comum, com `extrair-planalto.js`, e copiado pela área de transferência.

## Rotina semanal (executada por tarefa agendada no computador do curador)

Para cada norma em `fontes/<lei>/config.json`:

1. Abrir a página indicada em `url` no navegador.
2. Executar o conteúdo de `ferramentas/extrair-planalto.js` no console da página.
3. Clicar no botão **COPIAR TEXTO DA LEI** que aparece no topo e salvar a área de transferência em um arquivo (no macOS: `LANG=en_US.UTF-8 pbpaste > texto.txt`).
4. Rodar, na raiz do repositório:

   ```bash
   python3 ferramentas/atualizar.py --lei <lei> --texto texto.txt
   ```

5. Se algum status for `alterado`, ou se a data de conferência mudar, publicar por branch + pull request e incorporar ao `main`.

## O que o `atualizar.py` faz

- Separa os artigos do texto extraído e compara cada um com `fontes/<lei>/unidades.json`.
- Artigos alterados ou incluídos: atualiza o texto oficial e marca a análise como **pendente de revisão** (`fontes/<lei>/pendentes.json`), exibindo um aviso no artigo.
- Registra a mudança em `fontes/<lei>/CHANGELOG.md`.
- Regenera `leis/<lei>/<lei>-completa.md` e só grava o arquivo se o texto de todos os artigos for idêntico ao extraído e todas as seções estiverem presentes.
- Atualiza a coluna "Conferido com o Planalto em" do README.

## Regras da extração

- Parágrafos inteiramente tachados (redações antigas substituídas) são descartados.
- Dispositivos revogados que o Planalto mantém tachados junto da nota "(Revogado …)" aparecem como `~~texto~~ (Revogado …)`.
- Trechos tachados dentro de parágrafos vigentes (ex.: expressão afastada pelo STF) aparecem como `~~trecho~~`.
- Tachados sem palavra (ex.: apenas o "º") são ruído de formatação e ficam como texto normal.

## Como revisar uma análise pendente

1. Editar o bloco `@<parte> <número>` em `fontes/<lei>/anotacoes.txt` (linhas `I:`, `P:` e `K:`; nos temas do TST, também `T:`, o título curto que aparece ao lado do número, como em `### Tema 75 — Penhora de salário para pagamento de crédito trabalhista`).
2. Remover a chave correspondente de `fontes/<lei>/pendentes.json`.
3. Regenerar sem navegador: `python3 ferramentas/atualizar.py --lei <lei>`.

## Arquivos por norma (`fontes/<lei>/`)

| Arquivo | Conteúdo |
| --- | --- |
| `config.json` | Nome, link oficial, arquivo de saída, marcadores de início e fim do texto e mínimo de artigos esperado |
| `texto-oficial.txt` | Último texto oficial extraído (já com as marcações de tachado) |
| `unidades.json` | Texto de cada artigo na última conferência (base da comparação) |
| `anotacoes.txt` | Interpretação, pontos importantes e palavras-chave de cada artigo |
| `abertura.md` / `fechamento.md` | Seções analíticas antes e depois do Texto Estruturado |
| `pendentes.json` | Artigos com análise pendente de revisão |
| `CHANGELOG.md` | Histórico de alterações detectadas no texto oficial |

## Outros scripts

- `lexbuild.py`: monta o Markdown (texto oficial + análises + remissões e alterações extraídas do próprio texto).
- `validate.py`: confere artigo por artigo o texto publicado contra o extraído.
- `estrutura2.py`: gera o quadro estrutural (Partes, Livros, Títulos, Capítulos).

## Precedentes Vinculantes do TST (`fontes/tst-precedentes/`)

Fonte com estrutura diferente das leis: uma tabela de temas, em que cada tema traz tese, representativos, último movimento, suspensão e relator.

1. Abrir https://www.tst.jus.br/nugep-sp/recursos-repetitivos/precedentes-vinculantes no navegador (o site também recusa downloads diretos).
2. Executar `ferramentas/extrair-tst.js` no console, clicar em **COPIAR TABELA DO TST** e salvar: `LANG=en_US.UTF-8 pbpaste > tabela.json`.
3. Rodar `python3 ferramentas/tst.py --fonte tst-precedentes --tabela tabela.json`.

Regras de comparação:
- tese alterada ou tema novo → análise marcada como pendente de revisão;
- mudança apenas de andamento, suspensão, relator ou representativos → registrada no `CHANGELOG.md`, sem pendência;
- o quadro "Estrutura" (temas por situação) é gerado a cada montagem.

Para regenerar após revisar análises: `python3 ferramentas/tst.py --fonte tst-precedentes`.

## Precedentes do TRT8 (`fontes/trt8-precedentes/`)

Teses firmadas pelo TRT da 8ª Região em IRDR e IAC. O site do TRT8 aceita download direto, então não é preciso usar o navegador:

```bash
python3 ferramentas/trt8.py --fonte trt8-precedentes --baixar
```

O script lê a página https://www.trt8.jus.br/jurisprudencia/precedentes, separa cada precedente (tipo, número, título oficial, tese, processo, links do acórdão e da página), compara com a conferência anterior e monta `leis/trt8-precedentes/trt8-precedentes-completa.md`, validando que título e tese são idênticos aos do site. Anotações em `anotacoes.txt` com blocos `@IRDR 7` / `@IAC 5` (linhas `T:`, `I:`, `P:`, `K:`).

Regras de comparação:
- tese ou título oficial alterado, ou precedente novo → análise marcada como pendente de revisão;
- mudança apenas no processo ou no link do acórdão → registrada no `CHANGELOG.md`, sem pendência.

Para regenerar após revisar análises: `python3 ferramentas/trt8.py --fonte trt8-precedentes`.

## Página de consulta (`index.html`)

A página na raiz do repositório (publicada pelo GitHub Pages em https://oliveiracarlosadv.github.io/Lex-Vade-Mecum/) lê a tabela "Acesso direto às leis" do README e os arquivos `leis/*/*-completa.md`. Uma lei nova aparece na página assim que entra na tabela; não há nada a gerar.

Para a cópia que abre direto do computador (sem internet nem servidor), rode `python3 ferramentas/gerar-offline.py <pasta>` e copie para a mesma pasta `index.html`, `README.md`, `assets/` e `leis/`. O `dados-offline.js` gerado não vai para o GitHub.

Detalhes da página (formato esperado dos `.md`, rotas, busca, ações, publicação e sincronização com o Drive): [`docs/documentacao-tecnica.md`](../docs/documentacao-tecnica.md).
