import { test } from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chaveArtigo, cabecalho, parsearNorma } from '../lib/parser-planalto.mjs';
import { lerHtmlLocal, htmlParaBlocos } from '../lib/obter-texto.mjs';
import { interpretarAnalise } from '../lib/analises.mjs';

const aqui = path.dirname(fileURLToPath(import.meta.url));

test('reconhece rótulos de artigos do Planalto', () => {
  assert.equal(chaveArtigo('Art. 1º - Esta Consolidação'), '1');
  assert.equal(chaveArtigo('Art. 5º - A todo trabalho de igual valor'), '5');
  assert.equal(chaveArtigo('Art. 477-A. As dispensas'), '477-A');
  assert.equal(chaveArtigo('Art. 401A. (VETADO)'), '401-A');
  assert.equal(chaveArtigo('Art. 6o Não se distingue'), '6');
  assert.equal(chaveArtigo('Art.\n10 - Qualquer'.replace(/\s+/g, ' ')), '10');
  assert.equal(chaveArtigo('§ 1º Texto'), null);
});

test('reconhece cabeçalhos sem confundir palavras comuns', () => {
  assert.deepEqual(cabecalho('TíTULO VI'), { tipo: 'titulo', numero: 'VI', resto: '' });
  assert.equal(cabecalho('Seção civil de exemplo'), null);
  assert.equal(cabecalho('SEÇÃO XII-A').numero, 'XII-A');
});

test('extrai o Título I da CLT do fixture', async () => {
  const html = await lerHtmlLocal(path.join(aqui, 'fixtures', 'clt-titulo-i.html'));
  const blocos = htmlParaBlocos(html);
  const r = parsearNorma(blocos, { marcoInicial: 'CONSOLIDAÇÃO DAS LEIS DO TRABALHO', tituloDoAnexo: 'XI' });
  const arts = r.itens.filter((i) => i.tipo === 'artigo');
  const doTituloI = arts.filter((a) => a.titulo === 'I').map((a) => a.chave);
  assert.deepEqual(doTituloI, ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '10-A', '11', '11-A', '12']);
  const art2 = arts.find((a) => a.chave === '2');
  assert.equal(art2.blocos.length, 4, 'caput e três parágrafos; o texto riscado é descartado');
  assert.ok(art2.notas.some((n) => n.startsWith('(Redação dada pela Lei nº 13.467, de 2017)')));
  assert.ok(r.preambulo.some((b) => b.startsWith('Art. 1º Fica aprovada')), 'artigos do decreto ficam no preâmbulo');
  const sec = r.itens.find((i) => i.tipo === 'secao');
  assert.equal(sec.nome, 'Da Carteira de Trabalho e Previdência Social');
  assert.equal(sec.capitulo, 'I');
  assert.equal(arts.find((a) => a.chave === '401-A').situacao, 'vetado');
});

test('lê análises por artigo e preserva o hash', () => {
  const md = '---\nlei: clt\n---\n## Resumo Executivo\n\nTexto.\n\n## Texto Estruturado\n\n### Art. 2º\n<!-- hash-analisado: abc123 -->\n\n#### Interpretação\n\nX.\n\n### Art. 10-A\n\n#### Interpretação\n\nY.\n\n## Prazos Relevantes\n\nZ.\n';
  const a = interpretarAnalise(md);
  assert.equal(a.secoes.get('Resumo Executivo'), 'Texto.');
  assert.equal(a.artigos.get('2').hash, 'abc123');
  assert.match(a.artigos.get('10-A').corpo, /Y\./);
  assert.equal(a.secoes.get('Prazos Relevantes'), 'Z.');
});
