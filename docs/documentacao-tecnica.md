# Documentação técnica — página on-line do Lex Vade Mecum

Este documento descreve como a página de consulta é construída, publicada e mantida. Para o uso da página, veja o [Guia de uso](guia-de-uso.md). Para a extração e a atualização das leis, veja [`ferramentas/LEIA-ME.md`](../ferramentas/LEIA-ME.md).

## 1. Visão geral

| Item | Valor |
| --- | --- |
| Endereço | https://oliveiracarlosadv.github.io/Lex-Vade-Mecum/ |
| Hospedagem | GitHub Pages, ramo `main`, pasta raiz (`/`) |
| Arquivo da página | `index.html` (HTML, CSS e JavaScript em um só arquivo, sem etapa de build) |
| Dados | `README.md` (lista de leis) e `leis/<norma>/<norma>-completa.md` (conteúdo) |
| Dependências externas | Google Fonts (Literata e Cormorant Garamond) e, só ao gerar imagem, `html2canvas` 1.4.1 do cdnjs |
| Cópia sem internet | Pasta do projeto no Google Drive, com `dados-offline.js` |

A página **não tem conteúdo próprio**: ela lê os mesmos arquivos que a conferência semanal atualiza. Assim, quando o Planalto ou o TST mudam um texto e a rotina publica a correção, a página passa a exibir o texto novo sem nenhuma outra ação.

```
Planalto / TST ──(conferência semanal: extração + validação)──▶ leis/*.md + README.md (GitHub)
                                                                     │
                                                    GitHub Pages ────┤──▶ index.html lê via fetch
                                                                     │
                                       gerar-offline.py ─────────────┘──▶ dados-offline.js (Drive)
```

## 2. Arquivos

| Caminho | Função |
| --- | --- |
| `index.html` | A página |
| `.nojekyll` | Faz o GitHub Pages servir os arquivos como estão (sem Jekyll), inclusive os `.md` |
| `assets/lex-vade-mecum-logo.svg` | Logo da página inicial |
| `assets/lex-vade-mecum-icone.svg` | Ícone do topo, favicon e marca das imagens geradas |
| `README.md` | A tabela entre `<!-- catalogo:inicio -->` e `<!-- catalogo:fim -->` é a lista de leis da página |
| `leis/<norma>/<norma>-completa.md` | Conteúdo de cada lei |
| `ferramentas/gerar-offline.py` | Gera `dados-offline.js` para a cópia local |
| `docs/` | Esta documentação e o guia de uso |

`dados-offline.js` está no `.gitignore`: só existe na cópia do Drive.

## 3. Formato que a página espera

### 3.1 Lista de leis (README)

Cada linha da tabela do catálogo vira uma lei no menu e na página inicial. Colunas usadas:

| Coluna | Uso na página |
| --- | --- |
| 1 Norma | Nome no menu, na lista inicial e no cabeçalho |
| 2 Número | Exibido após o nome (um travessão inicial é removido) |
| 3 Data de publicação | Lista inicial e cabeçalho da lei |
| 4 Leitura on-line | Link `leis/<id>/<arquivo>.md`; a pasta `<id>` vira o identificador da lei nas rotas |
| 5 Texto oficial | Botão "Texto oficial ↗" |
| 6 Conferido em | Data exibida na lista, no cabeçalho, na impressão e nas imagens |

### 3.2 Arquivo da lei

| Marcador no `.md` | Interpretação |
| --- | --- |
| `# Título` | Título da lei |
| `## …` antes de `## Texto Estruturado` | Seções iniciais (Metadados, Resumo…) |
| `## Texto Estruturado` | Início dos dispositivos |
| `### Art. 5º`, `### ADCT — Art. 10`, `### Tema 75 — Título` | Um dispositivo; o que vem após ` — ` em temas é o título do assunto |
| `**Localização:** …` | Localização (Título › Capítulo › Seção), usada também no sumário |
| `> **Alterações …` | Nota de alterações |
| Linhas `**Campo:** valor` | Campos dos temas do TST (situação, relator, representativos…) |
| Demais linhas até `#### Interpretação` | Texto oficial, linha a linha |
| `#### Interpretação` em diante | Análise do dispositivo |
| `## Direitos Garantidos` em diante | Seções de análise geral |

Linhas do texto oficial recebem uma classe conforme o início: `Art.` (caput), `§`/`Parágrafo único` (parágrafo), algarismo romano + travessão (inciso), `a)` (alínea), `1.` (item), `(`…`)`/`Vide` (nota). As classes definem os recuos de livro.

O renderizador de Markdown é mínimo (títulos, parágrafos, listas, tabelas, citações, negrito, ~~tachado~~, links). Novos recursos de Markdown nos arquivos podem exigir ajuste em `md()`/`inline()`.

## 4. Funcionamento

### 4.1 Rotas

| Endereço | Tela |
| --- | --- |
| `#/` | Página inicial |
| `#/sobre` | Sobre (objetivo, atualização e criador; biografia e contato vêm do README, seções "Sobre o criador" e "Contato") |
| `#/<lei>` | Lei inteira |
| `#/<lei>/<dispositivo>` | Lei aberta no dispositivo (`art-5`, `art-1-035`, `adct-art-10`, `tema-75`) |
| `#/<lei>/s-<seção>` | Seção. As partes antes de `## Texto Estruturado` abrem na janela `#painel` (`abrirSecao()`); as de análise geral rolam até a seção (por exemplo `s-glossario-juridico`) |
| `…?q=termo1|termo2` | Realça os termos buscados |

### 4.2 Busca

- Normalização sem acentos e sem maiúsculas.
- Consulta de artigo (`art. 5º`, `artigo 1.035-A`, `adct 10`, `tema 75`) é reconhecida por expressão regular e comparada com a chave do dispositivo; `tema` busca só temas, `art` só artigos. Resultado único abre direto.
- Consulta de texto: palavras soltas (todas devem aparecer) e expressões entre aspas. Pontuação: ocorrências no texto oficial valem mais que na análise. Limite de 300 resultados exibidos.
- Escopo "Nesta lei" ou "Em todas"; as leis são carregadas sob demanda e guardadas em memória.

### 4.3 Ações

| Ação | Implementação |
| --- | --- |
| Compartilhar (artigo ou seleção) | Menu próprio com links `wa.me`, `mailto:`, cópia de link/texto (`navigator.clipboard`, com alternativa `execCommand`) e `navigator.share` quando o aparelho oferece |
| Texto enviado | `linhaPlana()`: remove marcações; trecho tachado vira `[revogado]` (mantendo o rótulo do inciso/parágrafo), para não circular texto revogado como vigente |
| Copiar seleção | Trecho entre aspas + fonte (`— Art. X, Lei`) + link |
| Imprimir artigo | Clona o dispositivo em `#areaImpressao`, aplica `body.imprimindo` e chama `window.print()`; o CSS de impressão esconde o resto |
| Imprimir lei | `window.print()` com CSS de impressão (sem menu, sem botões, cores claras, artigos sem quebra no meio quando possível) |
| Imagem | Monta um cartão de 1080 px fora da tela e o converte em PNG com `html2canvas` (carregado só nesse momento). Computador: download; celular: tela de compartilhamento |
| Story | Mesmo mecanismo da Imagem, com `htmlStory()`: cartão 1080 × 1920 com o logo no topo, o trecho inteiro, nunca cortado (`ajustarStory()` parte de 76 px e reduz a fonte até a caixa do texto caber na área central, com 4% de folga; o PNG sai sempre com 1080 × 1920) e, no rodapé, dispositivo, lei, número e endereço do site |
| Ir à expressão buscada | Resultados levam `?q=termos`; `irPara()` rola até o primeiro `<mark>` do texto oficial (ou da análise), a um terço da altura da tela, e o destaca com `mark.foco` |
| Barra de seleção | Aparece em `selectionchange` dentro do conteúdo; no celular fica fixa embaixo para não colidir com o menu nativo |

### 4.4 Aparência

- Cores definidas como variáveis CSS em `:root`; tema escuro por `prefers-color-scheme` ou pela escolha do botão ◐ (guardada em `localStorage`, com tratamento de erro).
- Folha centralizada de até 44rem, margens proporcionais à tela, texto justificado com hifenização em português.
- Pontos de quebra: até 900 px o menu vira gaveta (☰); até 600 px a folha ocupa a largura toda e os recuos diminuem.

## 5. Publicação

1. Alterações na página entram por ramo + pull request + merge em `main`, como todo o repositório.
2. O GitHub Pages publica automaticamente cada commit em `main` (ação "pages build and deployment", 1 a 10 minutos).
3. Configuração do Pages (feita uma vez): origem `main`, pasta `/`. Pela linha de comando:
   ```bash
   gh api -X POST repos/oliveiracarlosadv/Lex-Vade-Mecum/pages -f 'source[branch]=main' -f 'source[path]=/'
   ```
4. Conferir: abrir o endereço, uma lei, um link direto (`#/cpc/art-1-035`) e uma busca.

## 6. Cópia no Google Drive

A pasta `08 - Lex Vade Mecum` no Google Drive guarda uma cópia de todos os arquivos do repositório (sem a pasta `.git`), mais o `dados-offline.js`. Arquivos que existem só no Drive (logos de trabalho, anotações) não são apagados pela sincronização. Para sincronizar depois de uma atualização, a partir de um clone atualizado:

```bash
rsync -a --exclude '.git' --exclude 'node_modules' --exclude '.DS_Store' ./ "<pasta do Drive>/"
python3 ferramentas/gerar-offline.py "<pasta do Drive>"
```

Com isso, `index.html` na raiz da pasta abre a página com dois cliques. O navegador não permite que uma página aberta como arquivo leia outros arquivos; por isso `gerar-offline.py` embute o README e as leis em `window.LEX_DADOS`, que a página usa quando o endereço começa com `file:`.

## 7. Incluir uma nova lei na página

Nada a programar. Ao publicar a lei pelo processo normal (`fontes/<lei>/` + `ferramentas/atualizar.py`), a linha entra na tabela do README e a lei aparece na página, com busca, sumário e ações. Requisitos: arquivo em `leis/<lei>/<lei>-completa.md` com a estrutura da seção 3.2.

## 8. Lista de verificação após mudanças na página

- [ ] Página inicial lista todas as leis (nome — número).
- [ ] Cada lei abre; sumário leva às seções e aos Títulos.
- [ ] Links diretos: `#/constituicao-federal/art-5`, `#/cpc/art-1-035`, `#/tst-precedentes/tema-75`.
- [ ] Busca: `dano moral` (todas), `"direito adquirido"`, `art 5`, `tema 75`, `adct 10`.
- [ ] Compartilhar artigo e seleção; Copiar; Imprimir artigo e lei; Imagem.
- [ ] Tema escuro; largura de celular (375 px) e de computador.
- [ ] Cópia do Drive abre com dois cliques (sem servidor).

## 9. Histórico

| Data | Mudança |
| --- | --- |
| 06/11/2026 | Primeira versão: menu de leis, sumário, busca, diagramação de livro, tema escuro, página Sobre, títulos dos temas do TST |
| 06/11/2026 | Story sem cortes (fonte ajustável, tamanho fixo de story); assinatura "Lex Vade Mecum by Carlos A. A. Oliveira" no topo, na página inicial e no rodapé |
| 06/11/2026 | Lei abre direto no texto; partes introdutórias viram botões que abrem em janela |
| 06/11/2026 | Busca leva direto à expressão encontrada; botão Story (1080 × 1920) na barra de seleção |
| 06/11/2026 | Lista de leis na página inicial; Compartilhar, Copiar, Imprimir e Imagem por artigo e por trecho selecionado; Imprimir lei |
