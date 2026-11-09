# Ferramentas de atualização do Lex Vade Mecum

Objetivo: os artigos publicados em `leis/` devem espelhar sempre o texto vigente e exato do Portal da Legislação do Planalto.

## Por que a extração é feita pelo navegador

O Planalto recusa conexões automatizadas (downloads por linha de comando ou de servidores em nuvem). Por isso, o texto é extraído de uma página aberta em um navegador comum, com `extrair-planalto.js`, e copiado pela área de transferência.

## Conferência automática a cada 12 horas

- **NR do MTE (`"tipo": "pdf-nr"`):** na nuvem do GitHub, pelo workflow `.github/workflows/conferencia-nr.yml` (6h17 e 18h17, horário de Brasília). Ele roda `nr.py --baixar` para cada NR, publica direto no `main` se algo mudar (inclusive só a data de conferência) e pede a atualização do GitHub Pages. Pode ser disparado à mão na aba Actions ("Run workflow"). Se o PDF não puder ser baixado ou validado, a execução falha e o GitHub avisa o dono do repositório por e-mail.
- **Planalto, TST e TRT8:** esses sites bloqueiam acesso a partir de servidores de nuvem (testado em 07/11/2026: o Planalto recusa a conexão, o TST devolve página vazia de proteção contra robôs e o TRT8 responde 403). Eles são conferidos pela tarefa agendada no computador do curador, às 7h e às 19h, seguindo os passos abaixo. O acesso não é disfarçado nem contornado.

### Passos da tarefa agendada (leis do Planalto)

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
| `config.json` | Nome, link oficial, arquivo de saída, marcadores de início e fim do texto e mínimo de artigos esperado. Opção `descartar_vigencia_encerrada: true` (usada na CLT): omite redações tachadas de medidas provisórias com "(Vigência encerrada)" quando há redação em vigor do mesmo artigo; se todas estiverem tachadas, mantém a última |
| `texto-oficial.txt` | Último texto oficial extraído (já com as marcações de tachado) |
| `unidades.json` | Texto de cada artigo na última conferência (base da comparação) |
| `anotacoes*.txt` | Interpretação, pontos importantes e palavras-chave de cada artigo. Leis grandes podem dividir as anotações em vários arquivos (`anotacoes-01.txt`, `anotacoes-02.txt`…); todos são lidos em ordem alfabética |
| `abertura.md` / `fechamento.md` | Seções analíticas antes e depois do Texto Estruturado |
| `pendentes.json` | Artigos com análise pendente de revisão |
| `CHANGELOG.md` | Histórico de alterações detectadas no texto oficial |

## Classificação da norma na página (esfera, gênero e espécie)

A página agrupa as leis como um vade mecum (função `classificar()` do `index.html`):

- **Espécie:** sai sozinha da coluna "Número" do README ("Lei Complementar nº", "Lei nº", "Decreto-Lei nº", "Decreto nº", "Medida Provisória", "Resolução", "Portaria", "Lei Orgânica").
- **Gênero:** sai do nome ("Constituição…" → Constituição; "Código…"/"Consolidação…" → Códigos e Consolidações; "Precedentes…"/"Súmulas…" → Jurisprudência; o resto → Legislação Complementar e Estatutos).
- **Esfera:** federal por padrão. Para uma norma **estadual** ou **municipal**, ou para corrigir o gênero, inclua a lei em `CLASSIFICACAO` no `index.html`, por exemplo `'constituicao-para': { esfera: 'estadual', uf: 'Pará', genero: 'constituicao' }` ou `'lom-belem': { esfera: 'municipal', uf: 'PA', municipio: 'Belém' }`.

## Outros scripts

- `lexbuild.py`: monta o Markdown (texto oficial + análises + remissões e alterações extraídas do próprio texto).
- `lexbuild.py` reconhece cabeçalhos com letras espaçadas ("P A R T E G E R A L"), sem acento ("TITULO", "CAPITULO") e o nível SUBTÍTULO, presentes no Código Civil; aceita também "Art. 759.(Revogado...)" sem espaço. A mudança corrigiu o Capítulo VII (Das Penalidades) da CLT, cujo cabeçalho sem acento estava dentro do art. 721.
- `lexbuild.py` também aceita os Livros por ordinal ("LIVRO PRIMEIRO", "LIVRO SEGUNDO"), blocos revogados em uma linha ("Arts. 52 a 58 (Revogados...)"), que viram um único dispositivo identificado pelo primeiro artigo, e títulos soltos sem número ("DISPOSIÇÃO PRELIMINAR", "DISPOSIÇÕES FINAIS E TRANSITÓRIAS"), presentes no CTN.
- Na Lei nº 8.213/1991, `lexbuild.py` passou a reconhecer "Capítulo" e "Único" em minúsculas e artigos escritos sem espaço depois do ponto ("Art. 131.O Ministro"), e `atualizar.py` aceita o espaço não separável depois de "Art." nos trechos tachados (arts. 147 e 150). O Código Civil ganhou, com isso, a "Seção Única" correta nos arts. 1.088 e 1.089; nenhum texto de artigo mudou.
- Uma parte do `config.json` com `"unidade"` e `"rotulo"` (e opcionalmente `"root_name"`) vira um único dispositivo, sem separar artigos. É usada no Anexo I do CTB (conceitos e definições), que fica depois das assinaturas; o fim da parte é o marcador `"*"` do Planalto.
- No Código Eleitoral, `lexbuild.py` passou a reconhecer as Partes por ordinal feminino ("PARTE PRIMEIRA" a "PARTE QUINTA") e os artigos grafados "Ar." ou "At." no Planalto (arts. 248, 337, 352 e 373); `atualizar.py` e a página aceitam os mesmos rótulos. O erro de digitação é mantido no texto, como no original.
- No Código Penal, a parte do `config.json` tem `"rubricas": true`: o título marginal solto logo antes de um artigo ("Anterioridade da Lei", "Homicídio simples") vira a primeira linha desse artigo, e não a última do anterior nem parte do nome do Título. Rubrica e artigo na mesma linha, e dois artigos revogados na mesma linha (arts. 190 e 191), são separados sem alterar o texto. Também passaram a ser reconhecidos artigos com sufixo de duas letras ("Art. 359-M-A") e a divisão solta "DISPOSIÇÕES FINAIS". Na página, a rubrica aparece em itálico, centralizada.
- No Código de Processo Penal (também com `"rubricas": true`), `lexbuild.py` passou a reconhecer artigo revogado com o texto tachado colado ao número ("Art. 35.~~", arts. 35, 556, 558 e 635), a não tomar por rubrica o nome de Seção em minúsculas logo após o cabeçalho, a aceitar o inciso grafado "Vl" e a manter com o artigo a nota "(Incluído...)" entre a rubrica e o artigo. Os arts. 632 a 636, revogados sem parênteses na nota, têm análise escrita à mão em `anotacoes-12.txt`.
- `extrair-planalto.js`: roda na página do Planalto (navegador). Mantém tachado o caput de artigo revogado quando a nota de revogação está em parágrafo separado e não existe redação vigente do mesmo artigo (casos como os arts. 88, 287, 375 e 387 da CLT).
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

## Código de Ética e Disciplina da OAB (`fontes/ced-oab/`, `"tipo": "pdf-oab"`)

O texto vem do PDF oficial publicado pelo Conselho Federal da OAB (link em `config.json`), não do Planalto. O download direto do PDF funciona; para remontar o texto:

```bash
curl -sL -o ced.pdf "<url do config.json>"
pdftohtml -xml -i -q ced.pdf ced          # gera ced.xml
python3 -I ferramentas/oab-pdf2txt.py ced.xml texto.txt
python3 ferramentas/atualizar.py --lei ced-oab --texto texto.txt
```

`oab-pdf2txt.py` descarta o cabeçalho e o número das páginas, junta as linhas de cada dispositivo (mantendo o hífen das palavras compostas no fim da linha) e coloca cada nota de rodapé entre parênteses no fim do dispositivo que tem a chamada; notas em nomes de Capítulo ficam numa linha própria, como notas do cabeçalho. Os números de fonte usados (corpo, chamadas e rodapé) são os deste PDF e devem ser conferidos se a OAB publicar nova diagramação.

**Esta norma não entra na conferência automática** (a tarefa agendada só cobre Planalto, TST e TRT8, e o workflow da nuvem só as NR). Deve ser conferida com o PDF da OAB quando houver nova resolução do Conselho Federal.

## Normas Regulamentadoras (`fontes/nr-01/`, `"tipo": "pdf-nr"`)

As NR são publicadas pelo Ministério do Trabalho e Emprego em PDF no portal gov.br, que aceita download direto. É preciso ter o `pdftotext` (pacote poppler, `brew install poppler`).

```bash
python3 ferramentas/nr.py --fonte nr-01 --baixar        # baixa o PDF oficial (url do config.json) e atualiza
python3 ferramentas/nr.py --fonte nr-01 --pdf nr01.pdf  # usa um PDF já salvo
python3 ferramentas/nr.py --fonte nr-01                 # só regenera (após revisar análises)
```

O script extrai o texto do PDF, tira os rodapés "Este texto não substitui o publicado no DOU" e os sumários, junta as linhas quebradas pelo PDF e confere que o resultado, sem espaços, é idêntico ao corpo do PDF. Depois separa os dispositivos:
- cada subitem com conteúdo normativo é um dispositivo e leva junto seus subitens internos (o 1.4.3 reúne 1.4.3.1 a 1.4.3.3);
- itens que só nomeiam divisões ("1.5.3 Responsabilidades") e títulos sem número viram a localização;
- notas soltas antes de um título (ex.: "Redação dada pela Portaria MTE nº 1.419...") ficam no início do primeiro dispositivo da divisão;
- o glossário de cada anexo é um único dispositivo;
- redações com vigência encerrada indicadas em `"descartar"` no `config.json` (expressões regulares) não são reproduzidas.

Anotações em `anotacoes-*.txt` com blocos `@NR 1.4.1`, `@AII 2.1` (Anexo II) e `@AI glossario`. Dispositivo alterado ou incluído no PDF → análise marcada como pendente de revisão e registro no `CHANGELOG.md`. O quadro da estrutura é gerado no lugar de `<!-- ESTRUTURA_NR -->` em `abertura.md`.

## Página de consulta (`index.html`)

A página na raiz do repositório (publicada pelo GitHub Pages em https://oliveiracarlosadv.github.io/Lex-Vade-Mecum/) lê a tabela "Acesso direto às leis" do README e os arquivos `leis/*/*-completa.md`. Uma lei nova aparece na página assim que entra na tabela; não há nada a gerar.

Para a cópia que abre direto do computador (sem internet nem servidor), rode `python3 ferramentas/gerar-offline.py <pasta>` e copie para a mesma pasta `index.html`, `README.md`, `assets/` e `leis/`. O `dados-offline.js` gerado não vai para o GitHub.

Detalhes da página (formato esperado dos `.md`, rotas, busca, ações, publicação e sincronização com o Drive): [`docs/documentacao-tecnica.md`](../docs/documentacao-tecnica.md).
