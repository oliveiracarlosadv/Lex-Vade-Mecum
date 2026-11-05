// Leitura das análises jurídicas escritas à mão (pasta leis/<id>/analises).
// A análise nunca guarda o texto oficial: ele vem sempre do Planalto.
import { readFile, writeFile, access } from 'node:fs/promises';
import { chaveArtigo } from './parser-planalto.mjs';

const RE_HASH = /<!--\s*hash-analisado:\s*([0-9a-f]+)\s*-->/;
const RE_TITULO_ARTIGO = /^### (Art\.?\s*\d+.*)$/;

async function existe(caminho) {
  try {
    await access(caminho);
    return true;
  } catch {
    return false;
  }
}

function semFrontmatter(texto) {
  return texto.replace(/^---\n[\s\S]*?\n---\n/, '');
}

// Devolve { secoes: Map(nome -> markdown), artigos: Map(chave -> {corpo, hash}) }.
export function interpretarAnalise(texto) {
  const secoes = new Map();
  const artigos = new Map();
  const corpo = semFrontmatter(texto).replace(/<!--(?![\s]*hash-analisado)[\s\S]*?-->/g, '');
  const partes = corpo.split(/^## /m).slice(1);
  for (const parte of partes) {
    const quebra = parte.indexOf('\n');
    const nome = parte.slice(0, quebra < 0 ? undefined : quebra).trim();
    const conteudo = quebra < 0 ? '' : parte.slice(quebra + 1);
    if (nome === 'Texto Estruturado') {
      const blocos = conteudo.split(/^(?=### Art)/m);
      for (const bloco of blocos) {
        const linhas = bloco.split('\n');
        const m = RE_TITULO_ARTIGO.exec(linhas[0]);
        if (!m) continue;
        const chave = chaveArtigo(m[1].replace(/^Art\s/, 'Art. '));
        if (!chave) continue;
        const resto = linhas.slice(1).join('\n');
        const h = RE_HASH.exec(resto);
        artigos.set(chave, { corpo: resto.replace(RE_HASH, '').trim(), hash: h ? h[1] : null });
      }
    } else {
      secoes.set(nome, conteudo.trim());
    }
  }
  return { secoes, artigos };
}

export async function lerAnalise(caminho) {
  if (!(await existe(caminho))) return { secoes: new Map(), artigos: new Map(), existe: false };
  const texto = await readFile(caminho, 'utf8');
  return { ...interpretarAnalise(texto), existe: true };
}

// Grava o hash do texto oficial nas análises que ainda não o têm, para que uma
// mudança futura no texto do Planalto marque a análise como desatualizada.
export async function carimbarHashes(caminho, hashPorChave) {
  if (!(await existe(caminho))) return 0;
  const linhas = (await readFile(caminho, 'utf8')).split('\n');
  const saida = [];
  let dentro = false;
  let carimbados = 0;
  for (let i = 0; i < linhas.length; i++) {
    const linha = linhas[i];
    saida.push(linha);
    if (/^## /.test(linha)) dentro = linha.trim() === '## Texto Estruturado';
    const m = dentro && RE_TITULO_ARTIGO.exec(linha);
    if (!m) continue;
    const chave = chaveArtigo(m[1]);
    const hash = chave && hashPorChave.get(chave);
    if (!hash) continue;
    // Procura um hash já existente até o próximo título de artigo.
    let j = i + 1;
    let tem = false;
    while (j < linhas.length && !/^##/.test(linhas[j])) {
      if (RE_HASH.test(linhas[j])) tem = true;
      j++;
    }
    if (!tem) {
      saida.push(`<!-- hash-analisado: ${hash} -->`);
      carimbados++;
    }
  }
  if (carimbados) await writeFile(caminho, saida.join('\n'), 'utf8');
  return carimbados;
}
