#!/usr/bin/env node
// Conferência autônoma do Lex Vade Mecum, sem o Claude.
//
// Roda no Mac do curador (LaunchAgent às 7h e às 19h) e, para cada fonte em fontes/<lei>/:
//   - leis do Planalto: abre a página num Google Chrome controlado pelo Playwright (modo
//     invisível, sem alterar a identificação do navegador), executa ferramentas/extrair-planalto.js
//     e passa o texto ao atualizar.py;
//   - TST: abre a tabela, executa extrair-tst.js e roda tst.py;
//   - TRT8: trt8.py --baixar (o site aceita download direto);
//   - Código de Ética da OAB (pdf-oab): baixa o PDF, pdftohtml + oab-pdf2txt.py + atualizar.py;
//   - LegisWeb: baixa a página, extrair-legisweb.py + atualizar.py;
//   - NR (pdf-nr): já conferidas na nuvem pelo GitHub Actions; ignoradas aqui.
// Fonte com erro não é publicada (as mudanças dela são desfeitas). Se algo mudou, publica por
// branch + PR + merge (gh), sincroniza a pasta do Google Drive e gera a cópia offline.
//
// Uso: node conferencia-local.mjs  (variáveis opcionais: LEX_REPO, LEX_DRIVE, LEX_NODE, LEX_SO=lei1,lei2,
//      LEX_SEM_PUBLICAR=1 para testar sem publicar)
import { createRequire } from 'module';
import { spawnSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const BASE = path.join(os.homedir(), 'Library/Application Support/LexVadeMecum');
const REPO = process.env.LEX_REPO || path.resolve(AQUI, '..');
const DRIVE = process.env.LEX_DRIVE || path.join(os.homedir(), 'Library/CloudStorage/GoogleDrive-carlos.0109adv@gmail.com/Meu Drive/00.4 -  LexTecnologias/01 - Sistemas/08 - Lex Vade Mecum');
const NODE_DIR = process.env.LEX_NODE || path.join(BASE, 'conferencia');
const LOGS = path.join(os.homedir(), 'Library/Logs/LexVadeMecum');
const SO = (process.env.LEX_SO || '').split(',').filter(Boolean);
const PUBLICAR = !process.env.LEX_SEM_PUBLICAR;
const PATH_EXTRA = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin';
process.env.PATH = PATH_EXTRA + ':' + (process.env.PATH || '');
process.env.LANG = process.env.LC_ALL = 'en_US.UTF-8';

const { chromium } = createRequire(path.join(NODE_DIR, 'package.json'))('playwright');
fs.mkdirSync(LOGS, { recursive: true });
const agora = new Date();
const dois = (n) => String(n).padStart(2, '0');
const hoje = `${agora.getFullYear()}-${dois(agora.getMonth() + 1)}-${dois(agora.getDate())}`;
const log = (...a) => console.log(`[${new Date().toLocaleTimeString('pt-BR')}]`, ...a);

function rodar(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { cwd: REPO, encoding: 'utf8', maxBuffer: 1 << 28, ...opts });
  if (opts.exigir && r.status !== 0) throw new Error(`${cmd} ${args.join(' ')}: ${(r.stderr || r.stdout || '').slice(-800)}`);
  return r;
}
const git = (...a) => rodar('git', a, { exigir: true }).stdout.trim();
const ultimoJson = (s) => { const l = (s || '').trim().split('\n').reverse().find((x) => x.startsWith('{')); try { return JSON.parse(l); } catch { return null; } };
async function baixar(url, destino) {
  const r = await fetch(url, { redirect: 'follow' });
  if (!r.ok) throw new Error(`download ${url}: HTTP ${r.status}`);
  fs.writeFileSync(destino, Buffer.from(await r.arrayBuffer()));
}

// 1) Repositório limpo e atualizado (clone exclusivo da automação)
if (PUBLICAR) {
  git('fetch', '-q', 'origin');
  git('checkout', '-q', 'main');
  rodar('git', ['reset', '-q', '--hard', 'origin/main'], { exigir: true });
  rodar('git', ['clean', '-fdq', 'fontes', 'leis'], { exigir: true });
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lexvm-'));
const fontes = fs.readdirSync(path.join(REPO, 'fontes')).filter((d) => fs.existsSync(path.join(REPO, 'fontes', d, 'config.json')) && (!SO.length || SO.includes(d))).sort();
const resultados = [];
let navegador = null;
const pagina = async () => {
  navegador = navegador || await chromium.launch({ channel: 'chrome', headless: true });
  return navegador.newPage();
};
async function extrairNoNavegador(url, script, variavel) {
  const p = await pagina();
  try {
    let ultimoErro;
    for (let tentativa = 1; tentativa <= 3; tentativa++) {
      try {
        await p.goto(url, { waitUntil: 'load', timeout: 180000 });
        await p.evaluate(fs.readFileSync(path.join(REPO, 'ferramentas', script), 'utf8'));
        const t = await p.evaluate((v) => window[v], variavel);
        if (t && t.length > 1000) return t;
        ultimoErro = new Error('texto vazio ou curto demais');
      } catch (e) { ultimoErro = e; }
      await new Promise((r) => setTimeout(r, 15000 * tentativa));
    }
    throw ultimoErro;
  } finally { await p.close(); }
}

for (const lei of fontes) {
  const cfg = JSON.parse(fs.readFileSync(path.join(REPO, 'fontes', lei, 'config.json'), 'utf8'));
  const tipo = cfg.tipo || 'planalto';
  const t0 = Date.now();
  let res;
  try {
    if (tipo === 'pdf-nr') { res = { status: 'ignorada', detalhe: 'conferida na nuvem (GitHub Actions)' }; }
    else if (tipo === 'planalto') {
      const arq = path.join(tmp, lei + '.txt');
      fs.writeFileSync(arq, await extrairNoNavegador(cfg.url, 'extrair-planalto.js', '__TEXTO_LEX__'));
      res = ultimoJson(rodar('python3', ['-I', 'ferramentas/atualizar.py', '--lei', lei, '--texto', arq]).stdout);
    } else if (tipo === 'tabela-tst') {
      const arq = path.join(tmp, lei + '.json');
      fs.writeFileSync(arq, await extrairNoNavegador(cfg.url, 'extrair-tst.js', '__TABELA_TST__'));
      res = ultimoJson(rodar('python3', ['-I', 'ferramentas/tst.py', '--fonte', lei, '--tabela', arq]).stdout);
    } else if (tipo === 'pagina-trt8') {
      res = ultimoJson(rodar('python3', ['-I', 'ferramentas/trt8.py', '--fonte', lei, '--baixar']).stdout);
    } else if (tipo === 'pdf-oab') {
      const pdf = path.join(tmp, lei + '.pdf'), base = path.join(tmp, lei), txt = path.join(tmp, lei + '.txt');
      await baixar(cfg.url, pdf);
      rodar('pdftohtml', ['-xml', '-i', '-q', pdf, base], { exigir: true });
      rodar('python3', ['-I', 'ferramentas/oab-pdf2txt.py', base + '.xml', txt], { exigir: true });
      res = ultimoJson(rodar('python3', ['-I', 'ferramentas/atualizar.py', '--lei', lei, '--texto', txt]).stdout);
    } else if (tipo === 'legisweb') {
      const html = path.join(tmp, lei + '.html'), txt = path.join(tmp, lei + '.txt');
      await baixar(cfg.url, html);
      fs.writeFileSync(txt, rodar('python3', ['-I', 'ferramentas/extrair-legisweb.py', html], { exigir: true }).stdout);
      res = ultimoJson(rodar('python3', ['-I', 'ferramentas/atualizar.py', '--lei', lei, '--texto', txt]).stdout);
    } else res = { status: 'ignorada', detalhe: `tipo desconhecido: ${tipo}` };
    if (!res) res = { status: 'erro', detalhe: 'o script não devolveu resultado' };
  } catch (e) { res = { status: 'erro', detalhe: String(e.message || e).slice(0, 600) }; }
  res.lei = lei; res.segundos = Math.round((Date.now() - t0) / 1000);
  if (res.teses_alteradas) res.alterados = res.teses_alteradas;          // TST
  const andamento = [...(res.so_andamento || []), ...(res.so_processo_ou_link || [])]; // TST e TRT8: sem pendência
  if (andamento.length) res.so_andamento_ou_link = andamento;
  if (res.status === 'erro') {
    // Não publica nada desta fonte
    rodar('git', ['checkout', '-q', '--', `fontes/${lei}`, `leis/${lei}`]);
    rodar('git', ['clean', '-fdq', `fontes/${lei}`, `leis/${lei}`]);
  }
  resultados.push(res);
  log(lei, res.status, res.alterados?.length ? `alterados: ${res.alterados.join(', ')}` : '', res.incluidos?.length ? `incluídos: ${res.incluidos.join(', ')}` : '', res.retirados?.length ? `retirados: ${res.retirados.join(', ')}` : '', res.detalhe || '');
}
if (navegador) await navegador.close();
fs.rmSync(tmp, { recursive: true, force: true });

// 2) Publicação
const rot = (xs) => (xs || []).map((x) => String(x).replace(/^\S+ /, '')).join(', ');
const resumo = resultados.filter((r) => r.status !== 'ignorada').map((r) => {
  if (r.status === 'erro') return `- ${r.lei}: ERRO (não publicado) — ${r.detalhe}`;
  const partes = [];
  if (r.alterados?.length) partes.push(`alterados ${rot(r.alterados)}`);
  if (r.incluidos?.length) partes.push(`incluídos ${rot(r.incluidos)}`);
  if (r.retirados?.length) partes.push(`retirados ${rot(r.retirados)}`);
  if (r.so_andamento_ou_link) partes.push(`andamento, processo ou link atualizado em ${r.so_andamento_ou_link.join(', ')}`);
  if (r.so_forma) partes.push(`${r.so_forma} só com ajuste de espaços`);
  return `- ${r.lei}: ${partes.length ? partes.join('; ') : 'conferido, sem alterações'}`;
}).join('\n');
const mudancas = rodar('git', ['status', '--porcelain']).stdout.trim();
let publicado = null;
if (mudancas && PUBLICAR) {
  const ramo = `conferencia-${hoje}-${dois(agora.getHours())}h`;
  try {
    git('checkout', '-q', '-B', ramo);
    git('add', '-A');
    const real = resultados.some((r) => r.alterados?.length || r.incluidos?.length || r.retirados?.length);
    const titulo = real ? `Conferência ${hoje} ${dois(agora.getHours())}h: texto oficial atualizado` : `Conferência ${hoje} ${dois(agora.getHours())}h: conferido com as fontes oficiais`;
    git('commit', '-q', '-m', `${titulo}\n\n${resumo}\n\nConferência automática local (sem o Claude): ferramentas/conferencia-local.mjs.`);
    git('push', '-q', '-f', '-u', 'origin', ramo);
    const corpo = `${resumo}\n\nArtigos alterados ou incluídos ficam com a análise marcada como pendente de revisão (fontes/<lei>/pendentes.json).\n\nConferência automática local, feita pelo LaunchAgent do Mac do curador (ferramentas/conferencia-local.mjs), sem o Claude.`;
    const pr = rodar('gh', ['pr', 'create', '--base', 'main', '--head', ramo, '--title', titulo, '--body', corpo], { exigir: true }).stdout.trim();
    rodar('gh', ['pr', 'merge', pr, '--squash', '--delete-branch'], { exigir: true });
    git('checkout', '-q', 'main'); git('pull', '-q', '--ff-only');
    publicado = pr;
    log('publicado:', pr);
  } catch (e) { log('ERRO ao publicar:', e.message); publicado = 'erro: ' + e.message.slice(0, 300); rodar('git', ['checkout', '-q', 'main']); }
}
// 3) Pasta do Google Drive (espelho do repositório) e cópia offline
let drive = null;
if (PUBLICAR && fs.existsSync(DRIVE)) {
  const r1 = rodar('rsync', ['-a', '--exclude', '.git', '--exclude', 'node_modules', '--exclude', '.DS_Store', '--exclude', 'fontes/*/.tmp/', REPO + '/', DRIVE + '/']);
  const r2 = rodar('python3', ['-I', 'ferramentas/gerar-offline.py', DRIVE]);
  drive = r1.status === 0 && r2.status === 0 ? 'sincronizado' : 'erro: ' + (r1.stderr || r2.stderr || '').slice(-300);
  log('Drive:', drive);
}
const registro = { quando: agora.toISOString(), resultados, publicado, drive };
fs.appendFileSync(path.join(LOGS, 'conferencias.jsonl'), JSON.stringify(registro) + '\n');
const erros = resultados.filter((r) => r.status === 'erro').map((r) => r.lei);
const alteradas = resultados.filter((r) => r.alterados?.length || r.incluidos?.length || r.retirados?.length).map((r) => r.lei);
const aviso = erros.length ? `Erro em: ${erros.join(', ')}` : alteradas.length ? `Texto oficial atualizado: ${alteradas.join(', ')}` : 'Tudo conferido, sem alterações';
rodar('osascript', ['-e', `display notification ${JSON.stringify(aviso)} with title "Lex Vade Mecum — conferência"`]);
log('fim:', aviso);
process.exit(erros.length ? 2 : 0);
