// Geração dos arquivos Markdown a partir do texto oficial (dados) e das análises.
import { semNotas } from './parser-planalto.mjs';

export const SECOES_INICIAIS = ['Resumo Executivo', 'Objeto da Lei', 'Contexto Jurídico', 'Principais Conceitos'];
export const SECOES_FINAIS = [
  'Direitos Garantidos',
  'Obrigações',
  'Proibições',
  'Penalidades',
  'Competências e Responsabilidades',
  'Prazos Relevantes',
  'Relação com Outras Normas',
  'Glossário Jurídico',
  'Perguntas e Respostas',
  'Palavras-chave para Busca',
];
const CAMPOS_RAG = [
  'Tema principal',
  'Subtemas',
  'Área do Direito',
  'Esfera',
  'Órgãos envolvidos',
  'Assuntos relacionados',
  'Termos de indexação',
];

const PENDENTE_SECAO = '_Seção em elaboração: a análise desta parte será publicada em etapa posterior do Lex Vade Mecum._';
const NOMES_NIVEL = { livro: 'Livro', titulo: 'Título', capitulo: 'Capítulo', secao: 'Seção', subsecao: 'Subseção' };
const MESES = ['jan.', 'fev.', 'mar.', 'abr.', 'maio', 'jun.', 'jul.', 'ago.', 'set.', 'out.', 'nov.', 'dez.'];
const MINUSCULAS = new Set(['a', 'à', 'ao', 'aos', 'as', 'às', 'com', 'da', 'das', 'de', 'do', 'dos', 'e', 'em', 'na', 'nas', 'no', 'nos', 'o', 'os', 'ou', 'para', 'pela', 'pelas', 'pelo', 'pelos', 'por']);

// ---------- utilitários ----------

export function capitalizar(nome) {
  if (!nome) return '';
  return nome
    .toLowerCase()
    .split(' ')
    .map((p, i) => {
      if (/^[ivxlc]+(-[a-z])?$/.test(p) && p.length <= 6 && !['di', 'lixo', 'vil'].includes(p)) return p.toUpperCase();
      if (i > 0 && MINUSCULAS.has(p)) return p;
      return p.charAt(0).toUpperCase() + p.slice(1);
    })
    .join(' ');
}

export function slug(texto) {
  return String(texto)
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)
    .replace(/-+$/, '');
}

export function dataAbnt(iso) {
  const [a, m, d] = iso.split('-').map(Number);
  return `${d} ${MESES[m - 1]} ${a}`;
}

export function dataExtenso(iso) {
  const nomes = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const [a, m, d] = iso.split('-').map(Number);
  return `${d === 1 ? '1º' : d} de ${nomes[m - 1]} de ${a}`;
}

function numeroBr(n) {
  return n.toLocaleString('pt-BR');
}

// Escapa apenas o que o Markdown interpretaria indevidamente no texto legal.
function escaparMd(linha) {
  let s = linha.replace(/[*_`<]/g, (c) => (c === '<' ? '&lt;' : '\\' + c));
  s = s.replace(/^(\d+)([.)])(\s)/, '$1\\$2$3');
  s = s.replace(/^([#+>|-])(\s|$)/, '\\$1$2');
  return s;
}

function citacao(blocos) {
  return blocos.map((b) => '> ' + escaparMd(b)).join('\n>\n');
}

function rebaixarTitulos(md, niveis = 1) {
  return md.replace(/^(#{1,5}) /gm, (_, h) => '#'.repeat(Math.min(6, h.length + niveis)) + ' ');
}

function notasRelevantes(notas) {
  const vistas = new Set();
  const saida = [];
  for (const n of notas) {
    if (/^\((Vig[êe]ncia|Produ[çc][ãa]o de efeitos?)\)$/i.test(n)) continue;
    if (vistas.has(n)) continue;
    vistas.add(n);
    saida.push(n);
  }
  return saida;
}

const RE_NORMA = /(Emenda Constitucional|Lei Complementar|Decreto-[Ll]ei|Decreto Legislativo|Decreto|Medida Provis[óo]ria|Lei)\s+n[ºo°.]*\s*([\d.]+)(?:\s*,\s*(?:de\s*)?((?:\d{1,2}\.\d{1,2}\.)?\d{4}|\d{1,2}\s+de\s+\w+\s+de\s+\d{4}))?/g;

export function normasCitadas(notas) {
  const mapa = new Map();
  for (const nota of notas) {
    for (const m of nota.matchAll(RE_NORMA)) {
      const tipo = m[1].replace(/Decreto-lei/, 'Decreto-Lei').replace('Provisoria', 'Provisória');
      const numero = m[2].replace(/\.$/, '');
      const ano = m[3] ? (/(\d{4})$/.exec(m[3]) || [])[1] : null;
      const chave = `${tipo} ${numero}`;
      const atual = mapa.get(chave) || { tipo, numero, ano: null, vezes: 0 };
      atual.ano = atual.ano || ano;
      atual.vezes++;
      mapa.set(chave, atual);
    }
  }
  return [...mapa.values()].sort((a, b) => b.vezes - a.vezes || String(a.ano).localeCompare(String(b.ano)));
}

// ---------- organização da norma em partes ----------

export function organizarPartes(dados, particionarPor) {
  const partes = [];
  let atual = null;
  const nova = (id, numero, nome, cab) => {
    atual = { id, numero, nome, cabecalho: cab, itens: [] };
    partes.push(atual);
  };
  for (const it of dados.itens) {
    if (particionarPor === 'titulo' && it.tipo === 'titulo') {
      nova(`titulo-${it.numero.toLowerCase()}`, it.numero, it.nome, it);
      continue;
    }
    if (!atual) nova(particionarPor === 'titulo' ? 'disposicoes-iniciais' : 'texto', null, 'Disposições iniciais', null);
    atual.itens.push(it);
  }
  partes.forEach((p, i) => {
    p.ordem = i + 1;
    p.artigos = p.itens.filter((x) => x.tipo === 'artigo');
    p.arquivo = p.numero
      ? `${String(p.ordem).padStart(2, '0')}-titulo-${p.numero.toLowerCase()}-${slug(p.nome)}.md`
      : `${String(p.ordem).padStart(2, '0')}-${p.id}.md`;
  });
  return partes;
}

function intervalo(artigos) {
  if (!artigos.length) return 'sem artigos';
  const a = artigos[0].rotulo.replace('Art.', 'art.');
  const b = artigos[artigos.length - 1].rotulo.replace('Art.', 'art.');
  return artigos.length === 1 ? a : `${a} a ${b.replace('art. ', '')}`;
}

function contarSituacao(artigos) {
  const c = { vigente: 0, revogado: 0, vetado: 0 };
  for (const a of artigos) c[a.situacao] = (c[a.situacao] || 0) + 1;
  return c;
}

function nomeParte(meta, parte) {
  if (!parte.numero) return parte.nome;
  return `Título ${parte.numero}, ${capitalizar(parte.nome)}`;
}

// ---------- blocos de conteúdo ----------

function blocoMetadados(meta, extras = []) {
  const linhas = [
    `- **Número:** ${meta.numero}`,
    `- **Data:** ${dataExtenso(meta.data)}`,
    `- **Tipo:** ${meta.tipo}`,
    `- **Situação:** ${meta.situacao}`,
    `- **Fonte oficial:** ${meta.fonte}`,
    `- **Link oficial:** [${meta.url}](${meta.url})`,
    `- **Ementa:** ${meta.ementa}`,
  ];
  if (meta.publicacao) linhas.push(`- **Publicação:** ${meta.publicacao}`);
  linhas.push(
    `- **Texto oficial obtido em:** ${dataAbnt(meta.obtidoEm)} (data da última alteração detectada no texto do Planalto)`,
    `- **Identificador da versão do texto (SHA-256 abreviado):** \`${meta.hash}\``,
    ...extras
  );
  return linhas.join('\n');
}

function blocoReferencias(meta) {
  return [
    `- **Fonte oficial da lei:** ${meta.referenciaAbnt.replace('{ACESSO}', dataAbnt(meta.obtidoEm))}`,
    `- **Link oficial utilizado:** [${meta.url}](${meta.url})`,
    `- **Autor institucional:** ${meta.autor}`,
    `- **Data de acesso:** ${dataAbnt(meta.obtidoEm)}`,
    '- **Observação:** o texto oficial reproduzido neste repositório é extraído automaticamente do Portal da Legislação do Planalto e não substitui o publicado no Diário Oficial da União. As interpretações são de responsabilidade do Lex Vade Mecum e não têm caráter oficial.',
  ].join('\n');
}

function linhaNivel(cab) {
  const nome = cab.nome ? `: ${cab.nome}` : '';
  return `**${NOMES_NIVEL[cab.tipo].toUpperCase()} ${cab.numero}${nome}**`;
}

function localizacao(art, cabecalhos) {
  const partes = [];
  for (const nivel of ['livro', 'titulo', 'capitulo', 'secao', 'subsecao']) {
    if (!art[nivel]) continue;
    const chave = nivel + ':' + ['livro', 'titulo', 'capitulo', 'secao'].slice(0, ['livro', 'titulo', 'capitulo', 'secao', 'subsecao'].indexOf(nivel)).map((n) => art[n] || '').join('/') + ':' + art[nivel];
    const cab = cabecalhos.get(chave);
    const nome = cab && cab.nome ? ` (${capitalizar(cab.nome)})` : '';
    partes.push(`${NOMES_NIVEL[nivel]} ${art[nivel]}${nome}`);
  }
  return partes.join(', ') || 'Disposições gerais';
}

export function indiceCabecalhos(itens) {
  const mapa = new Map();
  const niveis = ['livro', 'titulo', 'capitulo', 'secao', 'subsecao'];
  for (const it of itens) {
    if (it.tipo === 'artigo') continue;
    const sup = niveis.slice(0, niveis.indexOf(it.tipo)).slice(0, 4).map((n) => it[n] || '').join('/');
    mapa.set(`${it.tipo}:${sup}:${it.numero}`, it);
  }
  return mapa;
}

function blocoArtigo(art, analise, cabecalhos, estatisticas) {
  const notas = notasRelevantes(art.notas);
  const linhas = [`### ${art.rotulo}`, '', `<!-- lvm:artigo chave=${art.chave} hash=${art.hash} -->`, ''];
  linhas.push(`**Localização:** ${localizacao(art, cabecalhos)}  `);
  linhas.push(`**Situação:** ${art.situacao}  `);
  if (notas.length) linhas.push(`**Alterações registradas no texto oficial:** ${notas.join('; ')}`);
  else linhas.push('**Alterações registradas no texto oficial:** nenhuma nota de alteração no dispositivo.');
  linhas.push('', '**Texto oficial:**', '', citacao(art.blocos), '');

  if (analise) {
    if (analise.hash && analise.hash !== art.hash) {
      estatisticas.desatualizadas.push(art.rotulo);
      linhas.push('> [!WARNING]', '> O texto oficial deste artigo mudou desde a última análise. A interpretação abaixo precisa ser revisada.', '');
    }
    estatisticas.analisados++;
    linhas.push(analise.corpo.trim(), '');
  } else if (art.situacao !== 'vigente') {
    estatisticas.analisados++;
    const tipo = art.situacao === 'revogado' ? 'revogado' : 'vetado';
    linhas.push(
      '#### Interpretação',
      '',
      `Dispositivo ${tipo}, conforme a nota que o acompanha no texto oficial. Permanece neste repositório apenas como registro histórico e para preservar as remissões feitas por outros artigos e normas.`,
      '',
      '#### Pontos Importantes',
      '',
      `- O número do artigo foi mantido no texto compilado, mas o conteúdo normativo não está em vigor (${tipo}).`,
      '- Consulte a norma indicada na nota de alteração para identificar a origem e a data da mudança.',
      '',
      '#### Palavras-chave',
      '',
      `- dispositivo ${tipo}`,
      `- ${art.rotulo.toLowerCase()} da ${'{SIGLA}'}`,
      ''
    );
  } else {
    estatisticas.pendentes++;
    linhas.push('> [!NOTE]', '> A interpretação jurídica, os pontos importantes e as palavras-chave deste artigo serão publicados em etapa posterior.', '');
  }
  return linhas.join('\n');
}

function blocoEstrutura(itens, comLinks = null) {
  const artigosPorCab = new Map();
  let pilha = [];
  const linhas = ['| Nível | Identificação | Denominação | Dispositivos |', '| --- | --- | --- | --- |'];
  const cabs = [];
  for (const it of itens) {
    if (it.tipo === 'artigo') {
      for (const c of pilha) artigosPorCab.get(c).push(it);
    } else {
      const ordem = ['livro', 'titulo', 'capitulo', 'secao', 'subsecao'];
      pilha = pilha.filter((c) => ordem.indexOf(c.tipo) < ordem.indexOf(it.tipo));
      pilha.push(it);
      artigosPorCab.set(it, []);
      cabs.push(it);
    }
  }
  for (const c of cabs) {
    const nome = c.nome ? capitalizar(c.nome) : '';
    const ident = comLinks && c.tipo === 'titulo' && comLinks.get(c.numero) ? `[${NOMES_NIVEL[c.tipo]} ${c.numero}](${comLinks.get(c.numero)})` : `${NOMES_NIVEL[c.tipo]} ${c.numero}`;
    linhas.push(`| ${NOMES_NIVEL[c.tipo]} | ${ident} | ${nome} | ${intervalo(artigosPorCab.get(c))} |`);
  }
  return linhas.join('\n');
}

function blocoNormasAuto(artigos) {
  const normas = normasCitadas(artigos.flatMap((a) => a.notas));
  if (!normas.length) return '';
  const linhas = [
    '### Normas que alteraram ou são remetidas por este texto',
    '',
    'Levantamento automático feito a partir das notas de alteração do texto oficial (ex.: "Redação dada pela", "Incluído pela", "Vide").',
    '',
    '| Norma | Ano | Ocorrências nas notas |',
    '| --- | --- | --- |',
  ];
  for (const n of normas) linhas.push(`| ${n.tipo} nº ${n.numero} | ${n.ano || 'não indicado'} | ${n.vezes} |`);
  return linhas.join('\n');
}

function blocoRag(analiseRag, padrao) {
  // Se a análise trouxe a seção pronta, ela prevalece; senão, usa o padrão gerado.
  if (analiseRag) return analiseRag;
  return CAMPOS_RAG.map((c) => `- **${c}:** ${padrao[c] || 'em elaboração'}`).join('\n');
}

function secao(nome, conteudo) {
  return `## ${nome}\n\n${conteudo && conteudo.trim() ? conteudo.trim() : PENDENTE_SECAO}\n`;
}

// ---------- documentos ----------

export function gerarParte({ meta, parte, partes, analise, cabecalhos, geral }) {
  const est = { analisados: 0, pendentes: 0, desatualizadas: [] };
  const sigla = meta.sigla || meta.id.toUpperCase();
  const titulo = `${meta.nome} (${sigla}): ${nomeParte(meta, parte)}`;
  const idx = partes.indexOf(parte);
  const nav = [`[Índice da ${sigla}](../README.md)`, `[${sigla} completa em um arquivo](../${meta.id}-completa.md)`];
  if (idx > 0) nav.push(`[Anterior: ${nomeParte(meta, partes[idx - 1])}](${partes[idx - 1].arquivo})`);
  if (idx < partes.length - 1) nav.push(`[Próximo: ${nomeParte(meta, partes[idx + 1])}](${partes[idx + 1].arquivo})`);

  const sit = contarSituacao(parte.artigos);
  const out = [];
  out.push(`# ${titulo}`, '', nav.join(' | '), '');
  out.push(
    '## Metadados',
    '',
    blocoMetadados(meta, [
      `- **Parte deste arquivo:** ${nomeParte(meta, parte)} (${intervalo(parte.artigos)})`,
      `- **Dispositivos nesta parte:** ${parte.artigos.length} artigos (${sit.vigente} vigentes, ${sit.revogado} revogados, ${sit.vetado} vetados)`,
      ...(parte.cabecalho && notasRelevantes(parte.cabecalho.notas).length
        ? [`- **Notas do cabeçalho no texto oficial:** ${notasRelevantes(parte.cabecalho.notas).join('; ')}`]
        : []),
    ]),
    ''
  );
  for (const s of SECOES_INICIAIS) out.push(secao(s, analise.secoes.get(s)));

  out.push('## Estrutura da Lei', '', `Mapa estrutural de ${nomeParte(meta, parte)}, gerado a partir do texto oficial.`, '');
  out.push(blocoEstrutura(parte.cabecalho ? [parte.cabecalho, ...parte.itens] : parte.itens), '');

  out.push('## Texto Estruturado', '');
  out.push('O texto de cada artigo reproduz a redação oficial vigente do Planalto, com as notas de alteração que a acompanham. A redação revogada (riscada no site oficial) não é reproduzida.', '');
  if (parte.cabecalho) out.push(linhaNivel(parte.cabecalho), '');
  for (const it of parte.itens) {
    if (it.tipo === 'artigo') {
      out.push(blocoArtigo(it, analise.artigos.get(it.chave), cabecalhos, est).replace('{SIGLA}', sigla));
    } else {
      out.push(linhaNivel(it), '');
    }
  }

  for (const s of SECOES_FINAIS) {
    let conteudo = analise.secoes.get(s) || '';
    if (s === 'Relação com Outras Normas') {
      const auto = blocoNormasAuto(parte.artigos);
      conteudo = [conteudo.trim() || PENDENTE_SECAO, auto].filter(Boolean).join('\n\n');
    }
    out.push(secao(s, conteudo));
  }
  out.push('## Referências', '', blocoReferencias(meta), '');
  const capitulos = parte.itens.filter((x) => x.tipo === 'capitulo').map((c) => capitalizar(c.nome));
  out.push(
    '## Metadados RAG',
    '',
    blocoRag(analise.secoes.get('Metadados RAG'), {
      'Tema principal': `${meta.nome}: ${nomeParte(meta, parte)}`,
      Subtemas: capitulos.join('; ') || capitalizar(parte.nome || ''),
      'Área do Direito': meta.area,
      Esfera: meta.esfera,
      'Órgãos envolvidos': meta.orgaos || 'em elaboração',
      'Assuntos relacionados': (geral && meta.assuntos) || 'em elaboração',
      'Termos de indexação': `${sigla}; ${meta.tipo} ${meta.numero}; ${intervalo(parte.artigos)}`,
    }),
    ''
  );
  return { md: out.join('\n'), estatisticas: est };
}

export function gerarIndice({ meta, partes, geral, progresso, dados }) {
  const sigla = meta.sigla || meta.id.toUpperCase();
  const total = partes.flatMap((p) => p.artigos);
  const sit = contarSituacao(total);
  const out = [];
  out.push(`# ${meta.nome} (${sigla})`, '', `[Voltar ao Lex Vade Mecum](../../README.md) | [${sigla} completa em um único arquivo](${meta.id}-completa.md) | [Histórico de alterações](CHANGELOG.md)` + (dados.anexos.length ? ' | [Anexos](anexos.md)' : ''), '');
  out.push('## Metadados', '', blocoMetadados(meta, [`- **Dispositivos:** ${numeroBr(total.length)} artigos (${numeroBr(sit.vigente)} vigentes, ${sit.revogado} revogados, ${sit.vetado} vetados)`]), '');
  for (const s of SECOES_INICIAIS) out.push(secao(s, geral.secoes.get(s)));

  out.push('## Estrutura da Lei', '');
  const linhas = ['| Parte | Denominação | Dispositivos | Artigos | Análise concluída | Arquivo |', '| --- | --- | --- | --- | --- | --- |'];
  for (const p of partes) {
    const pr = progresso.get(p.id) || { analisados: 0 };
    const pct = p.artigos.length ? Math.round((100 * pr.analisados) / p.artigos.length) : 100;
    linhas.push(`| ${p.numero ? 'Título ' + p.numero : p.nome} | ${capitalizar(p.nome)} | ${intervalo(p.artigos)} | ${p.artigos.length} | ${pct}% | [abrir](titulos/${p.arquivo}) |`);
  }
  out.push(linhas.join('\n'), '');
  out.push('### Mapa completo de Títulos, Capítulos e Seções', '', blocoEstrutura(dados.itens, new Map(partes.filter((p) => p.numero).map((p) => [p.numero, `titulos/${p.arquivo}`]))), '');

  if (dados.preambulo.length) {
    out.push('## Texto do Ato de Aprovação', '', 'Texto oficial que antecede o corpo da norma no Planalto (cabeçalho, ementa, preâmbulo e fecho do ato).', '', citacao(dados.preambulo), '');
  }
  out.push(secao('Relação com Outras Normas', [geral.secoes.get('Relação com Outras Normas') || '', blocoNormasAuto(total)].filter(Boolean).join('\n\n')));
  out.push('## Referências', '', blocoReferencias(meta), '');
  out.push('## Metadados RAG', '', blocoRag(geral.secoes.get('Metadados RAG'), { 'Tema principal': meta.nome, 'Área do Direito': meta.area, Esfera: meta.esfera }), '');
  return out.join('\n');
}

export function gerarCompleta({ meta, partes, geral, analises, cabecalhos, dados }) {
  const sigla = meta.sigla || meta.id.toUpperCase();
  const total = partes.flatMap((p) => p.artigos);
  const sit = contarSituacao(total);
  const est = { analisados: 0, pendentes: 0, desatualizadas: [] };
  const out = [];
  out.push(`# ${meta.nome} (${sigla})`, '', `Versão consolidada em um único arquivo. Para leitura no GitHub, prefira os [arquivos por Título](README.md).`, '');
  out.push('## Metadados', '', blocoMetadados(meta, [`- **Dispositivos:** ${numeroBr(total.length)} artigos (${numeroBr(sit.vigente)} vigentes, ${sit.revogado} revogados, ${sit.vetado} vetados)`]), '');
  for (const s of SECOES_INICIAIS) out.push(secao(s, geral.secoes.get(s)));
  out.push('## Estrutura da Lei', '', blocoEstrutura(dados.itens), '');
  out.push('## Texto Estruturado', '');
  if (dados.preambulo.length) out.push('**ATO DE APROVAÇÃO**', '', citacao(dados.preambulo), '');
  for (const p of partes) {
    const analise = analises.get(p.id);
    if (p.cabecalho) out.push(linhaNivel(p.cabecalho), '');
    for (const it of p.itens) {
      if (it.tipo === 'artigo') out.push(blocoArtigo(it, analise.artigos.get(it.chave), cabecalhos, est).replace('{SIGLA}', sigla));
      else out.push(linhaNivel(it), '');
    }
  }
  if (dados.anexos.length) {
    for (const a of dados.anexos) out.push(`**${a.nome}**`, '', citacao(a.blocos), '');
  }
  for (const s of SECOES_FINAIS) {
    const blocos = [];
    const g = geral.secoes.get(s);
    if (g) blocos.push(g.trim());
    for (const p of partes) {
      const c = analises.get(p.id).secoes.get(s);
      if (c && c.trim()) blocos.push(`### ${nomeParte(meta, p)}\n\n${rebaixarTitulos(c.trim(), 1)}`);
    }
    if (s === 'Relação com Outras Normas') blocos.push(blocoNormasAuto(total));
    out.push(secao(s, blocos.join('\n\n')));
  }
  out.push('## Referências', '', blocoReferencias(meta), '');
  out.push('## Metadados RAG', '', blocoRag(geral.secoes.get('Metadados RAG'), { 'Tema principal': meta.nome, 'Área do Direito': meta.area, Esfera: meta.esfera }), '');
  return out.join('\n');
}

export function gerarAnexos({ meta, dados }) {
  const sigla = meta.sigla || meta.id.toUpperCase();
  const out = [`# ${meta.nome} (${sigla}): Anexos`, '', `[Índice da ${sigla}](README.md)`, ''];
  out.push('## Metadados', '', blocoMetadados(meta), '');
  out.push('## Texto Estruturado', '', 'Anexos reproduzidos a partir do texto oficial do Planalto. Os quadros foram convertidos em texto corrido, célula por célula, na ordem em que aparecem.', '');
  for (const a of dados.anexos) out.push(`### ${a.nome}`, '', citacao(a.blocos), '');
  out.push('## Referências', '', blocoReferencias(meta), '');
  return out.join('\n');
}

export { semNotas };
