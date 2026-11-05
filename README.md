# Lex Vade Mecum

Biblioteca de leis brasileiras em Markdown, extraídas diretamente do texto oficial publicado no Portal da Legislação do Planalto e estruturadas para consulta por modelos de linguagem (Claude, GPT, Cursor, Windsurf, Copilot e similares), buscas semânticas e recuperação de contexto (RAG).

Cada norma é mantida em duas camadas. A primeira é o texto oficial, que nunca é digitado à mão: um script baixa a página do Planalto, separa Títulos, Capítulos, Seções e artigos, registra as notas de alteração ("Redação dada pela", "Incluído pela", "Revogado pela") e grava tudo em `leis/<norma>/dados/`. A segunda é a análise jurídica (resumo, interpretação de cada artigo, pontos importantes, palavras-chave, direitos, obrigações, prazos, glossário e perguntas frequentes), escrita em `leis/<norma>/analises/`. Os arquivos finais em Markdown são gerados pela combinação das duas camadas.

## Normas disponíveis

<!-- catalogo:inicio -->
| Norma | Tipo e número | Área | Artigos | Análise concluída | Texto obtido em | Arquivos |
| --- | --- | --- | --- | --- | --- | --- |
| Consolidação das Leis do Trabalho (CLT) | Decreto-Lei nº 5.452 | Direito do Trabalho e Direito Processual do Trabalho | pendente | pendente | pendente | [índice](leis/clt/README.md), [arquivo único](leis/clt/clt-completa.md) |
<!-- catalogo:fim -->

## Como o repositório se mantém atualizado

O fluxo do GitHub Actions em `.github/workflows/atualizar-leis.yml` roda toda segunda-feira e também pode ser disparado manualmente na aba Actions. Ele baixa novamente cada norma do catálogo no Planalto, compara com a versão anterior e, quando o texto oficial muda, regrava os arquivos, registra no `CHANGELOG.md` da norma quais artigos foram incluídos, alterados ou retirados e marca com um aviso as interpretações cujo artigo mudou desde a última análise. Quando apenas uma análise é editada, o mesmo fluxo regenera os Markdown sem baixar nada.

O Planalto pode bloquear acessos automatizados vindos de servidores. Se isso acontecer, o fluxo falha com uma mensagem clara e a atualização pode ser feita em um computador pessoal, de duas formas: rodando `npm run atualizar` diretamente ou salvando a página da lei pelo navegador e usando `node scripts/atualizar.mjs --lei clt --html pagina-salva.htm`. Depois, basta enviar as alterações ao GitHub.

## Estrutura de pastas

| Caminho | Conteúdo |
| --- | --- |
| `leis/catalogo.json` | Lista das normas da biblioteca, com link oficial, metadados e forma de divisão em arquivos |
| `leis/<norma>/README.md` | Índice da norma: metadados, resumo, mapa estrutural e andamento da análise (gerado) |
| `leis/<norma>/titulos/` | Um arquivo por Título, no modelo completo de documentação (gerado) |
| `leis/<norma>/<norma>-completa.md` | A norma inteira em um único arquivo, ideal para indexação em RAG (gerado) |
| `leis/<norma>/analises/` | Análise jurídica escrita à mão, sem o texto oficial |
| `leis/<norma>/dados/` | Texto oficial estruturado em JSON, extraído do Planalto (gerado) |
| `leis/<norma>/CHANGELOG.md` | Histórico de alterações detectadas no texto oficial (gerado) |
| `scripts/` | Extração, geração e testes |

Os arquivos marcados como gerados não devem ser editados à mão, pois são sobrescritos a cada atualização.

## Como incluir uma nova lei

Acrescente um item em `leis/catalogo.json` com o identificador, o nome, o tipo, o número, a data, a ementa, o link do texto compilado no Planalto, a referência no padrão ABNT (com `{ACESSO}` no lugar da data de acesso) e a forma de divisão (`"particionarPor": "titulo"` para códigos e consolidações, ou `"texto"` para leis curtas, que ficam em um único arquivo). Em seguida rode `npm install` uma vez e `npm run atualizar -- --lei <identificador>`. O script cria os arquivos de análise em branco, que podem ser preenchidos aos poucos.

## Uso com ferramentas de IA

Para consultas pontuais, aponte a ferramenta para o arquivo do Título correspondente. Para indexação vetorial, use o arquivo `<norma>-completa.md` ou os arquivos por Título, dividindo os trechos pelos títulos `### Art.`: cada artigo traz sua localização na norma, sua situação (vigente, revogado ou vetado), as notas de alteração, o texto oficial e a análise, o que mantém o contexto mesmo quando o trecho é recuperado isoladamente.

## Aviso

O texto normativo é reproduzido do Portal da Legislação da Presidência da República e não substitui o publicado no Diário Oficial da União. Atos oficiais não são protegidos por direitos autorais (Lei nº 9.610, de 1998, art. 8º, inciso IV). As interpretações aqui reunidas têm finalidade informativa e didática, não constituem parecer jurídico e não dispensam a consulta a um profissional habilitado.

## Sobre o criador

Carlos Alexandre Albuquerque Oliveira é advogado, empreendedor jurídico e pesquisador permanente do Direito, reconhecendo na aprendizagem contínua um dos pilares de sua atuação profissional. Natural de Belém do Pará, desenvolve seu trabalho junto a pessoas físicas e jurídicas, aliando sólida experiência na advocacia contenciosa à constante busca por inovação e eficiência na prestação de serviços jurídicos.

Ao longo de sua trajetória, consolidou-se como profissional comprometido com a excelência técnica e com a transformação digital do setor jurídico. Entre 2020 e 2026, foi sócio-fundador do escritório Sampaio & Oliveira Advogados, onde exerceu a função de Diretor do Setor de Demandas Contenciosas, liderando estratégias processuais, equipes e soluções voltadas à defesa dos interesses de clientes em diferentes áreas do Direito.

Apaixonado por música, tecnologia e conhecimento, Carlos dedica parte significativa de sua atuação ao desenvolvimento de soluções tecnológicas para advogados, acreditando que a inovação é um instrumento essencial para tornar a advocacia mais eficiente, acessível e conectada às necessidades da sociedade contemporânea.

Na internet, compartilha conhecimento, reflexões e experiências práticas sobre advocacia, tecnologia jurídica e transformação digital, ao mesmo tempo em que mantém uma postura aberta ao aprendizado colaborativo com profissionais do Direito, desenvolvedores e entusiastas da tecnologia aplicada ao setor jurídico.

Sua visão combina tradição jurídica e inovação, buscando criar pontes entre o conhecimento técnico, a inteligência digital e os desafios enfrentados pelos profissionais do Direito. Essa atuação multidisciplinar o posiciona como um agente ativo na construção de uma advocacia mais moderna, estratégica e preparada para o futuro.

Carlos Alexandre Albuquerque Oliveira acredita que o Direito evolui quando conhecimento, tecnologia e pessoas caminham juntos, transformando desafios em oportunidades e promovendo soluções capazes de gerar impacto real para profissionais, empresas e cidadãos.
