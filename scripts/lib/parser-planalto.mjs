// Parser genérico de textos normativos publicados no Portal da Legislação do
// Planalto (planalto.gov.br/ccivil_03). Funções puras: recebem a lista de blocos
// de texto (um por parágrafo do HTML, na ordem do documento) e devolvem a
// estrutura da norma (preâmbulo, cabeçalhos, artigos, fecho e anexos).
// O mesmo código roda no Node e pode ser colado no console do navegador.

// Aceita "Art. 1º", "Art. 10.", "Art. 477-A." e "Art. 401A."; não confunde
// "Art. 5º - A todo trabalho" com um artigo 5-A.
export const RE_ART = /^Art\.?\s*(\d+)\s*[ºo°]?(?:[-–]?([A-Z]{1,2})(?![a-zà-úA-Z]))?(?!\d)/;
const ROMANO = '([IVXLC]+(?:-[A-Z])?|[ÚU]NIC[OA]|PRELIMINAR)';
const FIM = '(?![A-Za-zÀ-ú])\\s*(.*)$';
// Sem a flag "i" para que o numeral romano não case com palavras comuns.
export const RE_LIVRO = new RegExp('^(?:LIVRO|Livro|PARTE|Parte)\\s+' + ROMANO + FIM);
export const RE_TITULO = new RegExp('^(?:T[ÍIí]TULO|Título)\\s+' + ROMANO + FIM);
export const RE_CAPITULO = new RegExp('^(?:CAP[ÍIí]TULO|Capítulo)\\s+' + ROMANO + FIM);
export const RE_SECAO = new RegExp('^(?:SE[ÇC][ÃA]O|Seção|Secão)\\s+' + ROMANO + FIM);
export const RE_SUBSECAO = new RegExp('^(?:SUBSE[ÇC][ÃA]O|Subseção|Subsecão)\\s+' + ROMANO + FIM);
export const RE_NOTA = /\((?:Reda[çc][ãa]o dad|Inclu[íi]d|Inclus[ãa]o|Revogad|Vide|Acrescid|Acrescentad|Renumerad|Vig[êe]ncia|Produ[çc][ãa]o de efeito|Regulamento|Express[ãa]o|Execu[çc][ãa]o suspensa|Suprimid|Restabelecid|Vetad|Mantid|Revigorad|Partes? mantida|Promulga[çc][ãa]o|Convers[ãa]o|Retificad|Revoga[çc][ãa]o|Ver |Veja )[^()]*(?:\([^()]*\)[^()]*)*\)/gi;
const RE_FECHO = /^(Bras[íi]lia|Rio de Janeiro|Este texto n[ãa]o substitui)/;
const RE_ANEXO = /^(ANEXO|QUADRO|TABELA)\b/;

const NIVEIS = ['livro', 'titulo', 'capitulo', 'secao', 'subsecao'];

export function normalizar(s) {
  return String(s)
    .replace(/ /g, ' ')
    .replace(/[​﻿]/g, '')
    .replace(/[ \t\r\n\f\v]+/g, ' ')
    .trim();
}

// Chave estável do artigo: "1", "477-A".
export function chaveArtigo(texto) {
  const m = RE_ART.exec(texto);
  if (!m) return null;
  return m[2] ? `${Number(m[1])}-${m[2]}` : String(Number(m[1]));
}

export function rotuloArtigo(chave) {
  const base = chave.split('~')[0];
  const [n, suf] = base.split('-');
  if (suf) return `Art. ${n}-${suf}`;
  return Number(n) <= 9 ? `Art. ${n}º` : `Art. ${n}`;
}

export function extrairNotas(texto) {
  return (texto.match(RE_NOTA) || []).map((n) => normalizar(n));
}

export function semNotas(texto) {
  return normalizar(texto.replace(RE_NOTA, ' '));
}

export function cabecalho(texto) {
  for (const [tipo, re] of [
    ['livro', RE_LIVRO],
    ['titulo', RE_TITULO],
    ['capitulo', RE_CAPITULO],
    ['subsecao', RE_SUBSECAO],
    ['secao', RE_SECAO],
  ]) {
    const m = re.exec(texto);
    if (m) return { tipo, numero: m[1].toUpperCase(), resto: m[2] || '' };
  }
  return null;
}

function pareceNome(texto) {
  if (!texto || texto.length > 300) return false;
  if (RE_ART.test(texto) || cabecalho(texto)) return false;
  if (/^\(/.test(texto)) return false;
  if (/^(§|Parágrafo|[IVXLC]+\s*[-–.]|[a-z]\))/.test(texto)) return false;
  return true;
}

// blocos: array de strings já normalizadas, na ordem do documento.
// opcoes.marcoInicial: texto exato do bloco a partir do qual começa a norma
// (ex.: "CONSOLIDAÇÃO DAS LEIS DO TRABALHO"); sem ele, começa no primeiro artigo.
// opcoes.tituloDoAnexo: número do Título em que podem aparecer anexos (opcional).
export function parsearNorma(blocos, opcoes = {}) {
  let inicio;
  if (opcoes.marcoInicial) {
    inicio = blocos.findIndex((b) => b === opcoes.marcoInicial);
    if (inicio < 0) throw new Error(`Marco inicial "${opcoes.marcoInicial}" não encontrado no texto oficial.`);
    inicio += 1;
  } else {
    inicio = blocos.findIndex((b) => RE_ART.test(b) || cabecalho(b));
    if (inicio < 0) throw new Error('Nenhum artigo encontrado no texto oficial.');
  }

  const preambulo = blocos.slice(0, inicio).filter(Boolean);
  const itens = [];
  const ctx = { livro: null, titulo: null, capitulo: null, secao: null, subsecao: null };
  const fecho = [];
  const anexos = [];
  let artigo = null;
  let cab = null;
  let modo = 'corpo'; // corpo | fecho | anexo

  const fecharArtigo = () => {
    if (artigo) itens.push(artigo);
    artigo = null;
  };

  for (let i = inicio; i < blocos.length; i++) {
    const b = blocos[i];
    if (!b) continue;

    if (RE_ANEXO.test(b) && (modo !== 'corpo' || !opcoes.tituloDoAnexo || (ctx.titulo && ctx.titulo.numero === opcoes.tituloDoAnexo))) {
      fecharArtigo();
      modo = 'anexo';
      anexos.push({ nome: b, blocos: [] });
      continue;
    }
    if (modo === 'anexo') {
      anexos[anexos.length - 1].blocos.push(b);
      continue;
    }
    if (modo === 'corpo' && RE_FECHO.test(b)) {
      fecharArtigo();
      modo = 'fecho';
    }
    if (modo === 'fecho') {
      fecho.push(b);
      continue;
    }

    const c = cabecalho(b);
    if (c) {
      fecharArtigo();
      cab = { tipo: c.tipo, numero: c.numero, nome: semNotas(c.resto), notas: extrairNotas(b) };
      const nivel = NIVEIS.indexOf(c.tipo);
      ctx[c.tipo] = cab;
      for (const inferior of NIVEIS.slice(nivel + 1)) ctx[inferior] = null;
      for (const sup of NIVEIS.slice(0, nivel)) cab[sup] = ctx[sup] ? ctx[sup].numero : null;
      itens.push(cab);
      continue;
    }

    if (cab && !artigo && !cab.nome && pareceNome(b)) {
      cab.nome = semNotas(b);
      cab.notas.push(...extrairNotas(b));
      continue;
    }
    if (cab && !artigo && /^\(/.test(b)) {
      cab.notas.push(...extrairNotas(b));
      continue;
    }

    const chave = chaveArtigo(b);
    if (chave) {
      fecharArtigo();
      cab = null;
      artigo = { tipo: 'artigo', chave, blocos: [b] };
      for (const n of NIVEIS) artigo[n] = ctx[n] ? ctx[n].numero : null;
      continue;
    }

    if (artigo) artigo.blocos.push(b);
    else if (cab) cab.notas.push(b);
    else preambulo.push(b);
  }
  fecharArtigo();

  const vistos = new Map();
  for (const it of itens) {
    if (it.tipo !== 'artigo') continue;
    const n = (vistos.get(it.chave) || 0) + 1;
    vistos.set(it.chave, n);
    if (n > 1) it.chave = `${it.chave}~${n}`; // número repetido no texto oficial
    it.rotulo = rotuloArtigo(it.chave);
    it.texto = it.blocos.join('\n');
    it.notas = extrairNotas(it.texto);
    const caput = it.blocos[0];
    const resto = semNotas(caput).replace(RE_ART, '').replace(/^[\s.ºo°-]+/, '').replace(/[.\s]/g, '');
    if (/\(Revogad/i.test(caput) && resto.length < 3) it.situacao = 'revogado';
    else if (/\(Vetad/i.test(caput) && resto.length < 3) it.situacao = 'vetado';
    else it.situacao = 'vigente';
  }

  return { preambulo, itens, fecho, anexos };
}
