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

A página **não tem conteúdo próprio**: ela lê os mesmos arquivos que a conferência automática atualiza a cada 12 horas. Assim, quando o Planalto, o TST, o TRT8 ou o MTE mudam um texto e a rotina publica a correção, a página passa a exibir o texto novo sem nenhuma outra ação.

```
Fontes oficiais ──(conferência a cada 12 h: extração + validação)──▶ leis/*.md + README.md (GitHub)
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
| `manifest.webmanifest` | Nome, cores e ícones do atalho na tela inicial (Android/Chrome); abre em tela cheia (`display: standalone`) |
| `assets/apple-touch-icon.png` (e cópia na raiz) | Ícone 180 × 180 do atalho no iPhone/iPad |
| `assets/icone-192.png`, `assets/icone-512.png` | Ícones do manifesto (Android) |
| `assets/icone-maskable-512.png` | Ícone com margem extra para recortes circulares do Android |
| `assets/favicon-32.png` | Favicon PNG para navegadores sem suporte a SVG |
| `assets/icone-app.svg`, `assets/icone-maskable.svg` | Originais quadrados (fundo creme) dos ícones acima; os PNGs foram gerados com `qlmanage` e `sips` do macOS |
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
| `#/<lei>/<dispositivo>` | Lei aberta no dispositivo (`art-5`, `art-1-035`, `adct-art-10`, `tema-75`, `irdr-n-7`, `iac-n-5`) |
| `#/<lei>/s-<seção>` | Seção. As partes antes de `## Texto Estruturado` abrem na janela `#painel` (`abrirSecao()`); as de análise geral rolam até a seção (por exemplo `s-glossario-juridico`) |
| `…?q=termo1|termo2` | Realça os termos buscados |

### 4.2 Busca

- **Índice por lei** (`indexar()`), montado uma vez em segundo plano (`preCarregarBusca()`, logo após abrir o site, todas as leis em paralelo): para cada dispositivo, as palavras do título (peso 3), do texto oficial (2), da localização e campos (0,7) e da análise (0,6).
- **Normalização:** sem acento e em minúsculas; números sem pontos (`13.105` = `13105`); palavras comuns ignoradas (`PARADAS`); **radical** em português (`radical()`: plural e feminino — `gestantes`→`gestant`, `ações`→`acao`, `morais`→`moral`, `mulheres`→`mulher`).
- **Consulta** (`prepararConsulta()`): artigos/temas/precedentes reconhecidos por expressão regular (resultado único abre direto); expressões entre aspas são obrigatórias; palavras soltas exigem todas (E); se nada casar, cai para "parte das palavras" (OU) com aviso. Palavras com 4+ letras aceitam começo incompleto (`penhor`).
- **Ranking:** soma por termo de `idf × Σ peso_campo × tf/(tf+1,2)`, com bônus para a expressão inteira no texto (+6) ou na análise (+2), para aspas (+8) e para presença no texto oficial (+1,5).
- **Correção:** termos sem ocorrência recebem sugestão por distância de edição (1 ou 2 letras), escolhendo a forma mais frequente.
- **Destaque:** por palavra (`casador()` + `realcar()`/`marcar()`), o mesmo critério da busca; o trecho exibido é a janela com mais ocorrências (`janela()`).
- **Interface:** sugestões enquanto digita (`sugerir()`, a cada 160 ms, 7 itens, teclado ↑ ↓ Enter Esc); lista completa com filtros por lei e "Mostrar mais" (40 por vez). Endereço do resultado: `#/<lei>/<dispositivo>?q=<consulta>`.

### 4.3 Ações

| Ação | Implementação |
| --- | --- |
| Compartilhar (artigo ou seleção) | Menu próprio com links `wa.me`, `mailto:`, cópia de link/texto (`navigator.clipboard`, com alternativa `execCommand`) e `navigator.share` quando o aparelho oferece |
| Texto enviado | `linhaPlana()`: remove marcações; trecho tachado vira `[revogado]` (mantendo o rótulo do inciso/parágrafo), para não circular texto revogado como vigente |
| Copiar seleção | Trecho entre aspas + fonte (`— Art. X, Lei`) + link |
| Imprimir artigo | Clona o dispositivo em `#areaImpressao`, aplica `body.imprimindo` e chama `window.print()`; o CSS de impressão esconde o resto |
| Imprimir lei | `window.print()` com CSS de impressão (sem menu, sem botões, cores claras, artigos sem quebra no meio quando possível) |
| Imagem | Monta um cartão de 1080 px fora da tela e o converte em PNG com `html2canvas` (carregado só nesse momento). Computador: download; celular: tela de compartilhamento |
| Story | `desenharStory()` desenha a imagem direto em canvas 1080 × 1920, sem depender da diagramação do navegador (resultado igual no iPhone, Android e computador): logo no topo, trecho no centro e dispositivo, lei, número e site no rodapé. As linhas são quebradas por `quebrarLinhas()` com hifenização em português (`pontosSilabicos()`) e justificadas por `escreverJustificado()`, que distribui a sobra igualmente entre as palavras; a última linha de cada parágrafo fica alinhada à esquerda. A fonte parte de 64 px e diminui até o trecho caber inteiro |
| Ir à expressão buscada | Resultados levam `?q=termos`; `irPara()` rola até o primeiro `<mark>` do texto oficial (ou da análise), a um terço da altura da tela, e o destaca com `mark.foco` |
| Marca-texto | Botão **Marcar** da barra de seleção. `trechosDaSelecao()` divide a seleção por parágrafo do texto oficial (`.oficial p`) e guarda, para cada parte: lei, dispositivo (`uid`), índice do parágrafo, posição inicial e final no `textContent` e o próprio trecho; partes de uma mesma seleção compartilham o grupo `g`. `aplicarMarcas()` remove e redesenha os `<mark class="mt">` a cada abertura da lei; `localizar()` confere o trecho na posição salva e, se o texto mudou, procura-o no mesmo dispositivo. Clique numa marca abre `menuMarca()` (cor, copiar, remover) |
| Favoritos e perfil | `alternarFavorita()` (botão ☆ na lei; ★ no menu e na página inicial). O perfil (`nome`, `@`) é saneado por `limparPerfil()` e entra no rodapé do story e da imagem via `linhaPerfil()` ("Compartilhado por …") |
| Progresso de leitura | Botão `data-acao="parei"` em cada dispositivo chama `marcarLeitura()`, que grava `dados.leitura[lei] = {uid, idx, total, rot, em}`; `pctLeitura()` = (idx + 1) / total. `aplicarLeitura()` desenha a barra em `#progLei`, marca `.dispositivo.parei` e troca o rótulo para "Você parou aqui"; `blocoLeituras()` e `listaLeituras()` mostram a lista na página inicial e em `#/marcacoes`; o menu exibe o percentual. Na importação, prevalece o ponto mais recente (`em`) |
| Armazenamento | `localStorage['lex-dados']` = `{versao, perfil, favoritos[], marcas[], leitura{}}`; cor preferida em `lex-cor`. Leitura e gravação sempre com `try/catch` (modo privado ou cota cheia mostram aviso). Nada é enviado a servidor |
| Backup | `exportarBackup()` gera `lex-vade-mecum-backup-AAAA-MM-DD.json` (`app: "Lex Vade Mecum"`, `tipo: "backup"`); `importarBackup()` valida o arquivo e cada marcação, e junta (sem duplicar por `id`) ou substitui. Página `#/marcacoes` |
| Desmarcar e @ no story | `marcasNaSelecao()` mostra o botão **Desmarcar** quando a seleção cruza `mark.mt`; `desmarcarSelecao()` remove os grupos. `pedirArrobaEGerar()` abre `#janelaArroba` antes do story quando não há @ salvo; o story desenha "Compartilhado por [nome]" e o @ em linha própria (50 px) |
| Barra de seleção | Aparece em `selectionchange` dentro do conteúdo; no celular fica fixa embaixo para não colidir com o menu nativo |

### 4.4 Aparência

- Cores definidas como variáveis CSS em `:root`; tema escuro por `prefers-color-scheme` ou pela escolha do botão ◐ (guardada em `localStorage`, com tratamento de erro).
- Folha centralizada de até 44rem, margens proporcionais à tela, texto justificado com hifenização em português.
- Nada ultrapassa a largura da tela: rolagem lateral bloqueada (`overflow-x`), palavras e links longos quebram linha (`overflow-wrap:anywhere`) e endereços longos aparecem encurtados (`encurtarUrl()`: domínio/…/arquivo). No celular, o campo de busca usa 16 px para o iPhone não dar zoom automático.
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
- [ ] Parei aqui: barra e percentual no início da lei, Continuar leitura, percentual no menu e Continuar lendo na página inicial.
- [ ] Marcar trecho (inclusive de dois parágrafos), recarregar a página e conferir; mudar cor e remover; favoritar lei; salvar perfil e gerar Story; backup e importação.
- [ ] Tema escuro; largura de celular (375 px) e de computador.
- [ ] Cópia do Drive abre com dois cliques (sem servidor).

## 9. Histórico

| Data | Mudança |
| --- | --- |
| 06/11/2026 | Primeira versão: menu de leis, sumário, busca, diagramação de livro, tema escuro, página Sobre, títulos dos temas do TST |
| 06/11/2026 | Nova busca: índice com radicais, ranking por relevância, sugestões ao digitar, correção de digitação, filtros por lei e pré-carregamento |
| 06/11/2026 | Ícone e manifesto para atalho na tela inicial (iPhone e Android) |
| 06/11/2026 | Código Civil publicado; progresso de leitura (Parei aqui, percentual, Continuar leitura) salvo no navegador e no backup |
| 06/11/2026 | Barra de seleção cabe na tela do celular (ícone sobre rótulo, largura total); botão Desmarcar; story pede o @ quando não há perfil e o destaca no rodapé |
| 06/11/2026 | Código Tributário Nacional (CTN) publicado, com as alterações das LC nº 214/2025, 227/2026 e 236/2026 |
| 07/11/2026 | NR-01 publicada a partir do PDF oficial do MTE (`ferramentas/nr.py`); subitens das NR diagramados como dispositivos |
| 07/11/2026 | Manual de uso (`docs/manual-de-uso.md`) no menu do site (`#/manual`), na página inicial, no rodapé e no README |
| 07/11/2026 | Botão "Instalar como aplicativo" no menu: usa o pedido de instalação do navegador (Chrome/Edge) ou mostra o passo a passo por aparelho; `sw.js` mínimo, sem cache, só para habilitar a instalação |
| 07/11/2026 | Conferência a cada 12 horas: NR na nuvem (`.github/workflows/conferencia-nr.yml`); Planalto, TST e TRT8 pela tarefa agendada no computador do curador (7h e 19h), pois bloqueiam servidores de nuvem |
| 08/11/2026 | Lei de Benefícios da Previdência Social (Lei nº 8.213/1991) publicada; foto do criador na página Sobre |
| 08/11/2026 | Código de Defesa do Consumidor (CDC) publicado, com o superendividamento (Lei nº 14.181/2021) e a MP nº 1.393/2026 |
| 08/11/2026 | Código de Trânsito Brasileiro (CTB) publicado, com o Anexo I como dispositivo único |
| 08/11/2026 | Menu: ordenar as leis em ordem alfabética (A–Z) ou pela data de publicação (Data), com a escolha salva no navegador (`lex-ordem`) |
| 08/11/2026 | Código Eleitoral (Lei nº 4.737/1965) publicado; leitor reconhece PARTE PRIMEIRA a QUINTA e os rótulos "Ar."/"At." grafados assim no Planalto |
| 08/11/2026 | Código Penal (Decreto-Lei nº 2.848/1940) publicado; leitor passa a tratar as rubricas (títulos marginais) e artigos com sufixo de duas letras (359-M-A) |
| 06/11/2026 | CLT publicada; marca-texto nos artigos, leis favoritas, perfil (nome e @ nos stories e imagens) e backup/importação, tudo salvo no navegador |
| 06/11/2026 | Assinatura "Lex Vade Mecum por Carlos A. A. Oliveira" no Story e nas imagens |
| 06/11/2026 | Story desenhado direto em canvas: justificado idêntico em qualquer aparelho |
| 06/11/2026 | Celular: página fixa na largura da tela, sem rolagem lateral; links longos encurtados |
| 06/11/2026 | Story e imagem de citação justificados com hifenização em português |
| 06/11/2026 | Precedentes do TRT8 (IRDR e IAC) na página; busca por `irdr 7` e `iac 5` |
| 06/11/2026 | Story sem cortes (fonte ajustável, tamanho fixo de story); assinatura "Lex Vade Mecum by Carlos A. A. Oliveira" no topo, na página inicial e no rodapé |
| 06/11/2026 | Lei abre direto no texto; partes introdutórias viram botões que abrem em janela |
| 06/11/2026 | Busca leva direto à expressão encontrada; botão Story (1080 × 1920) na barra de seleção |
| 06/11/2026 | Lista de leis na página inicial; Compartilhar, Copiar, Imprimir e Imagem por artigo e por trecho selecionado; Imprimir lei |
