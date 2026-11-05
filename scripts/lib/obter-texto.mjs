// Obtém o HTML oficial de uma norma no Planalto e o converte em blocos de texto.
import { readFile } from 'node:fs/promises';
import * as cheerio from 'cheerio';
import { normalizar } from './parser-planalto.mjs';

const USER_AGENT = 'LexVadeMecum/1.0 (+https://github.com/oliveiracarlosadv/Lex-Vade-Mecum)';

function decodificar(buffer, contentType = '') {
  const bytes = new Uint8Array(buffer);
  // Charset declarado no cabeçalho HTTP ou na meta tag; o Planalto usa windows-1252.
  let charset = (/charset=([\w-]+)/i.exec(contentType) || [])[1];
  if (!charset) {
    const cabeca = new TextDecoder('latin1').decode(bytes.slice(0, 4096));
    charset = (/charset=["']?([\w-]+)/i.exec(cabeca) || [])[1] || 'windows-1252';
  }
  charset = charset.toLowerCase();
  if (charset === 'iso-8859-1' || charset === 'latin1') charset = 'windows-1252';
  return new TextDecoder(charset).decode(bytes);
}

export async function baixarHtml(url) {
  let resp;
  try {
    resp = await fetch(url, { headers: { 'User-Agent': USER_AGENT, Accept: 'text/html' } });
  } catch (e) {
    const causa = e.cause ? ` (${e.cause.code || ''} ${e.cause.message || e.cause})` : '';
    throw new Error(`Não foi possível conectar a ${url}: ${e.message}${causa}`);
  }
  const buffer = await resp.arrayBuffer();
  const html = decodificar(buffer, resp.headers.get('content-type') || '');
  if (!resp.ok) throw new Error(`O Planalto respondeu HTTP ${resp.status} para ${url}.`);
  verificarBloqueio(html, url);
  return html;
}

export async function lerHtmlLocal(caminho) {
  const buffer = await readFile(caminho);
  const html = decodificar(buffer);
  verificarBloqueio(html, caminho);
  return html;
}

function verificarBloqueio(html, origem) {
  if (/Acesso Negado|Esta requisi[çc][ãa]o foi bloqueada/i.test(html) && html.length < 20000) {
    const erro = new Error(
      `O Planalto bloqueou o acesso automatizado a ${origem}. ` +
        'Rode o script em um computador pessoal ou salve a página pelo navegador e use --html arquivo.htm.'
    );
    erro.codigo = 'BLOQUEADO';
    throw erro;
  }
}

const SELETOR = 'p, h1, h2, h3, h4, h5, h6, td, li, div';

// Converte o HTML em blocos de texto, um por parágrafo, na ordem do documento.
// Texto riscado (redação antiga) é descartado; quebras <br> separam blocos.
export function htmlParaBlocos(html) {
  const $ = cheerio.load(html, { decodeEntities: true });
  $('strike, s, del, script, style').remove();
  $('[style*="line-through"]').remove();
  $('br').replaceWith(' ');
  const blocos = [];
  $(SELETOR)
    .filter((_, el) => $(el).find(SELETOR).length === 0)
    .each((_, el) => {
      for (const parte of $(el).text().split(' ')) {
        const t = normalizar(parte);
        if (t) blocos.push(t);
      }
    });
  return blocos;
}
