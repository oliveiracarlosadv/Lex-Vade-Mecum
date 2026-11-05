#!/usr/bin/env node
// Lex Vade Mecum: atualiza o texto oficial das leis do catálogo a partir do
// Planalto e regenera os arquivos Markdown.
//
// Uso:
//   node scripts/atualizar.mjs                     atualiza todas as leis do catálogo
//   node scripts/atualizar.mjs --lei clt           atualiza só a CLT
//   node scripts/atualizar.mjs --lei clt --html pagina.htm   usa uma página salva no navegador
//   node scripts/atualizar.mjs --somente-gerar     não baixa nada; regenera a partir de dados/*.json
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile, readdir, rm, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parsearNorma } from './lib/parser-planalto.mjs';
import { baixarHtml, lerHtmlLocal, htmlParaBlocos } from './lib/obter-texto.mjs';
import { lerAnalise, carimbarHashes } from './lib/analises.mjs';
import {
  organizarPartes,
  indiceCabecalhos,
  gerarParte,
  gerarIndice,
  gerarCompleta,
  gerarAnexos,
  capitalizar,
  dataAbnt,
} from './lib/gerador.mjs';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const hoje = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Belem' }).format(new Date());
const sha = (t) => createHash('sha256').update(t, 'utf8').digest('hex');

function args() {
  const a = process.argv.slice(2);
  const op = { lei: null, html: null, somenteGerar: false };
  for (let i = 0; i < a.length; i++) {
    if (a[i] === '--lei') op.lei = a[++i];
    else if (a[i] === '--html') op.html = a[++i];
    else if (a[i] === '--somente-gerar') op.somenteGerar = true;
    else throw new Error(`Opção desconhecida: ${a[i]}`);
  }
  return op;
}

async function existe(p) {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

async function lerJson(p, padrao = null) {
  return (await existe(p)) ? JSON.parse(await readFile(p, 'utf8')) : padrao;
}

function esqueletoAnalise(lei, parteNome) {
  const secoes = [
    'Resumo Executivo',
    'Objeto da Lei',
    'Contexto Jurídico',
    'Principais Conceitos',
    'Texto Estruturado',
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
    'Metadados RAG',
  ];
  return [
    '---',
    `lei: ${lei}`,
    `parte: ${parteNome}`,
    '---',
    '',
    '<!--',
    'Análise jurídica desta parte. O texto oficial NÃO deve ser copiado aqui: ele é',
    'inserido automaticamente a partir do Planalto pelo script scripts/atualizar.mjs.',
    'Em "## Texto Estruturado", crie um bloco por artigo, assim:',
    '',
    '### Art. 1º',
    '',
    '#### Interpretação',
    '#### Pontos Importantes',
    '#### Palavras-chave',
    '',
    'Seções deixadas vazias aparecem como "em elaboração" nos arquivos gerados.',
    '-->',
    '',
    ...secoes.flatMap((s) => [`## ${s}`, '']),
  ].join('\n');
}

async function processarLei(lei, op) {
  const pasta = path.join(RAIZ, 'leis', lei.id);
  const caminhoDados = path.join(pasta, 'dados', `${lei.id}.json`);
  await mkdir(path.join(pasta, 'dados'), { recursive: true });
  await mkdir(path.join(pasta, 'analises'), { recursive: true });
  const anterior = await lerJson(caminhoDados);

  let dados;
  if (op.somenteGerar) {
    if (!anterior) {
      console.warn(`[${lei.id}] ainda não há texto oficial salvo; rode sem --somente-gerar para baixá-lo. Norma ignorada.`);
      return null;
    }
    dados = anterior;
  } else {
    const html = op.html ? await lerHtmlLocal(op.html) : await baixarHtml(lei.url);
    const blocos = htmlParaBlocos(html);
    const r = parsearNorma(blocos, { marcoInicial: lei.marcoInicial, tituloDoAnexo: lei.tituloDoAnexo });
    for (const it of r.itens) if (it.tipo === 'artigo') it.hash = sha(it.texto).slice(0, 16);
    const hashGeral = sha(JSON.stringify([r.preambulo, r.itens.map((i) => i.texto || `${i.tipo}:${i.numero}:${i.nome}`), r.anexos])).slice(0, 32);
    const mudou = !anterior || anterior.meta.hash !== hashGeral;
    dados = {
      meta: { obtidoEm: mudou ? hoje() : anterior.meta.obtidoEm, hash: hashGeral },
      preambulo: r.preambulo,
      itens: r.itens.map(({ blocos: b, texto, ...resto }) => (resto.tipo === 'artigo' ? { ...resto, blocos: b } : resto)),
      fecho: r.fecho,
      anexos: r.anexos,
    };
    for (const it of dados.itens) if (it.tipo === 'artigo') it.texto = it.blocos.join('\n');
    if (mudou) {
      await registrarMudancas(pasta, lei, anterior, dados);
      const paraSalvar = { ...dados, itens: dados.itens.map(({ texto, ...x }) => x) };
      await writeFile(caminhoDados, JSON.stringify(paraSalvar, null, 1) + '\n', 'utf8');
      console.log(`[${lei.id}] texto oficial atualizado (${dados.itens.filter((i) => i.tipo === 'artigo').length} artigos).`);
    } else {
      console.log(`[${lei.id}] texto oficial sem alterações desde ${anterior.meta.obtidoEm}.`);
    }
  }
  for (const it of dados.itens) if (it.tipo === 'artigo' && !it.texto) it.texto = it.blocos.join('\n');

  const meta = { ...lei, ...dados.meta };
  const partes = organizarPartes(dados, lei.particionarPor);
  const cabecalhos = indiceCabecalhos(dados.itens);

  // Análises: cria esqueletos que faltam e carimba hashes novos.
  const hashes = new Map(dados.itens.filter((i) => i.tipo === 'artigo').map((a) => [a.chave, a.hash]));
  const caminhoGeral = path.join(pasta, 'analises', '00-geral.md');
  if (!(await existe(caminhoGeral))) await writeFile(caminhoGeral, esqueletoAnalise(lei.id, 'geral'), 'utf8');
  const geral = await lerAnalise(caminhoGeral);
  const analises = new Map();
  for (const p of partes) {
    const arq = path.join(pasta, 'analises', `${p.id}.md`);
    if (!(await existe(arq))) await writeFile(arq, esqueletoAnalise(lei.id, p.id), 'utf8');
    const n = await carimbarHashes(arq, hashes);
    if (n) console.log(`[${lei.id}] ${n} análise(s) de ${p.id} receberam o hash do texto oficial.`);
    const a = await lerAnalise(arq);
    for (const chave of a.artigos.keys()) {
      if (!p.artigos.some((x) => x.chave === chave)) console.warn(`[${lei.id}] aviso: análise do art. ${chave} em ${p.id}.md não corresponde a nenhum artigo desta parte.`);
    }
    analises.set(p.id, a);
  }

  // Arquivos por parte.
  const pastaTitulos = path.join(pasta, 'titulos');
  await rm(pastaTitulos, { recursive: true, force: true });
  await mkdir(pastaTitulos, { recursive: true });
  const progresso = new Map();
  const desatualizadas = [];
  for (const p of partes) {
    const { md, estatisticas } = gerarParte({ meta, parte: p, partes, analise: analises.get(p.id), cabecalhos, geral });
    await writeFile(path.join(pastaTitulos, p.arquivo), md, 'utf8');
    progresso.set(p.id, estatisticas);
    desatualizadas.push(...estatisticas.desatualizadas);
  }
  if (dados.anexos.length) await writeFile(path.join(pasta, 'anexos.md'), gerarAnexos({ meta, dados }), 'utf8');
  await writeFile(path.join(pasta, 'README.md'), gerarIndice({ meta, partes, geral, progresso, dados }), 'utf8');
  await writeFile(path.join(pasta, `${lei.id}-completa.md`), gerarCompleta({ meta, partes, geral, analises, cabecalhos, dados }), 'utf8');
  if (desatualizadas.length) console.warn(`[${lei.id}] análises desatualizadas: ${desatualizadas.join(', ')}`);

  const total = partes.reduce((s, p) => s + p.artigos.length, 0);
  const analisados = [...progresso.values()].reduce((s, e) => s + e.analisados, 0);
  return { lei, meta, total, analisados, desatualizadas: desatualizadas.length };
}

async function registrarMudancas(pasta, lei, anterior, dados) {
  const caminho = path.join(pasta, 'CHANGELOG.md');
  const atuais = new Map(dados.itens.filter((i) => i.tipo === 'artigo').map((a) => [a.chave, a]));
  const linhas = [];
  if (!anterior) {
    linhas.push(`- Primeira captura do texto oficial: ${atuais.size} artigos.`);
  } else {
    const antigos = new Map(anterior.itens.filter((i) => i.tipo === 'artigo').map((a) => [a.chave, a]));
    const novos = [...atuais.keys()].filter((k) => !antigos.has(k));
    const removidos = [...antigos.keys()].filter((k) => !atuais.has(k));
    const alterados = [...atuais.keys()].filter((k) => antigos.has(k) && antigos.get(k).hash !== atuais.get(k).hash);
    const rot = (ks, m) => ks.map((k) => m.get(k).rotulo).join(', ');
    if (novos.length) linhas.push(`- Artigos incluídos no texto oficial: ${rot(novos, atuais)}.`);
    if (alterados.length) linhas.push(`- Artigos com redação alterada: ${rot(alterados, atuais)}.`);
    if (removidos.length) linhas.push(`- Artigos que deixaram de constar do texto oficial: ${rot(removidos, antigos)}.`);
    if (!linhas.length) linhas.push('- Alterações apenas em cabeçalhos, notas, preâmbulo ou anexos.');
  }
  const cab = `# Histórico de alterações: ${lei.nome}\n\nRegistro automático das mudanças detectadas no texto oficial do Planalto ([link](${lei.url})).\n`;
  const atual = (await existe(caminho)) ? (await readFile(caminho, 'utf8')).replace(/^# [^\n]*\n\n[^\n]*\n/, '') : '';
  await writeFile(caminho, `${cab}\n## ${dataAbnt(dados.meta.obtidoEm)}\n\n${linhas.join('\n')}\n${atual}`, 'utf8');
}

async function atualizarReadmeRaiz(resultados, catalogo) {
  const caminho = path.join(RAIZ, 'README.md');
  if (!(await existe(caminho))) return;
  const texto = await readFile(caminho, 'utf8');
  const porId = new Map(resultados.map((r) => [r.lei.id, r]));
  const linhas = ['| Norma | Tipo e número | Área | Artigos | Análise concluída | Texto obtido em | Arquivos |', '| --- | --- | --- | --- | --- | --- | --- |'];
  for (const lei of catalogo) {
    const r = porId.get(lei.id);
    const dados = r ? null : await lerJson(path.join(RAIZ, 'leis', lei.id, 'dados', `${lei.id}.json`));
    const total = r ? r.total : dados ? dados.itens.filter((i) => i.tipo === 'artigo').length : 0;
    const pct = r && r.total ? `${Math.round((100 * r.analisados) / r.total)}%` : 'ver índice';
    const obtido = r ? dataAbnt(r.meta.obtidoEm) : dados ? dataAbnt(dados.meta.obtidoEm) : 'pendente';
    linhas.push(`| ${lei.nome} (${lei.sigla}) | ${lei.tipo} nº ${lei.numero} | ${lei.area} | ${total} | ${pct} | ${obtido} | [índice](leis/${lei.id}/README.md), [arquivo único](leis/${lei.id}/${lei.id}-completa.md) |`);
  }
  const novo = texto.replace(/<!-- catalogo:inicio -->[\s\S]*?<!-- catalogo:fim -->/, `<!-- catalogo:inicio -->\n${linhas.join('\n')}\n<!-- catalogo:fim -->`);
  if (novo !== texto) await writeFile(caminho, novo, 'utf8');
}

async function main() {
  const op = args();
  const catalogo = await lerJson(path.join(RAIZ, 'leis', 'catalogo.json'), []);
  const alvo = op.lei ? catalogo.filter((l) => l.id === op.lei) : catalogo;
  if (!alvo.length) throw new Error(op.lei ? `Lei "${op.lei}" não está em leis/catalogo.json.` : 'Catálogo vazio.');
  if (op.html && alvo.length > 1) throw new Error('--html exige --lei.');
  const resultados = [];
  let falhas = 0;
  for (const lei of alvo) {
    try {
      const r = await processarLei(lei, op);
      if (r) resultados.push(r);
    } catch (e) {
      falhas++;
      console.error(`[${lei.id}] ${e.message}`);
    }
  }
  await atualizarReadmeRaiz(resultados, catalogo);
  if (falhas) process.exitCode = 2;
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});

export { capitalizar };
