// Extrator do texto vigente de uma norma no Portal da Legislação (Planalto).
// Executar no console da página da norma, aberta no navegador.
//
// - Redações antigas (parágrafos inteiros tachados) são descartadas, salvo o caput de
//   artigo revogado sem versão vigente, que é mantido tachado.
// - Trechos tachados dentro de parágrafos vigentes são mantidos entre ⟦ ⟧.
// - Dispositivos revogados cujo texto o Planalto mantém tachado junto da nota
//   "(Revogado ...)" são preservados entre ⟦ ⟧; o script atualizar.py os converte
//   para ~~tachado~~ no Markdown.
// - O resultado fica em window.__TEXTO_LEX__ e um botão "COPIAR TEXTO DA LEI" é
//   inserido no topo da página: um clique copia o texto para a área de transferência
//   (o navegador só permite copiar a partir de um clique).
(() => {
  document.querySelectorAll('*').forEach((e) => {
    if (getComputedStyle(e).textDecorationLine.includes('line-through')) e.setAttribute('data-struck', '1');
  });
  const c = document.body.cloneNode(true);
  c.querySelector('#lex-copiar')?.remove();
  // Artigos que têm versão vigente (parágrafo não tachado começando por "Art. N").
  const rotulo = (txt) => { const m = txt.replace(/\u00a0/g, ' ').trim().match(/^A?rt\.?\s*\.?\s*(\d+(?:\.\d{3})*)\s*(?:º|o|°)?(-?[A-Z](?=[.\s-]))?/); return m && m[1].replace(/\./g, '') + (m[2] || '').replace('-', ''); };
  const vigentes = new Set();
  c.querySelectorAll('p').forEach((p) => {
    const sobra = p.cloneNode(true);
    sobra.querySelectorAll('strike,s,del,[data-struck]').forEach((e) => e.remove());
    if (!p.hasAttribute('data-struck')) { const r = rotulo(sobra.textContent); if (r) vigentes.add(r); }
  });
  c.querySelectorAll('p').forEach((p) => {
    const struck = [...p.querySelectorAll('strike,s,del,[data-struck]')].filter(
      (e) => !e.parentElement.closest('strike,s,del,[data-struck]')
    );
    if (!struck.length && !p.hasAttribute('data-struck')) return;
    // Parte não riscada do parágrafo, sem a nota "(Revogado ...)". Se sobrar só uma letra ou
    // espaços (o Planalto às vezes deixa o "A" de "Art." fora do riscado, como no CPM), o
    // parágrafo conta como inteiramente riscado.
    const restoSemRisco = (() => { const s = p.cloneNode(true); s.querySelectorAll('strike,s,del,[data-struck]').forEach((e) => e.remove()); return s.textContent.replace(/\(Revogad[\s\S]*$/, '').replace(/[\s.,;:()]+/g, ''); })();
    const pst = p.hasAttribute('data-struck') || restoSemRisco.length <= 1;
    const revoked = /Revogad/.test(p.innerText);
    const targets = pst ? [p] : struck;
    if (revoked) {
      targets.forEach((e) => {
        if (e === p) {
          const t = p.innerText;
          const m = t.match(/^([\s\S]*?)(\s*\(Revogad[\s\S]*)$/);
          p.textContent = m ? '⟦' + m[1].trim() + '⟧ ' + m[2].trim() : '⟦' + t.trim() + '⟧';
        } else {
          e.replaceWith(document.createTextNode('⟦' + e.innerText.trim() + '⟧'));
        }
      });
    } else {
      // Parágrafo inteiro tachado = redação antiga substituída: sai do texto.
      // Trecho tachado dentro de parágrafo vigente (ex.: expressão afastada pelo STF):
      // permanece marcado como tachado, como o Planalto exibe.
      const sobra = p.cloneNode(true);
      sobra.querySelectorAll('strike,s,del,[data-struck]').forEach((e) => e.remove());
      const vigente = pst ? '' : sobra.textContent.replace(/[\s.,;:()]+/g, '');
      const r = rotulo(p.innerText);
      if (!vigente && r && !vigentes.has(r)) {
        // Caput de artigo revogado cuja nota "(Revogado ...)" está em outro parágrafo
        // (ex.: CLT, arts. 88, 287, 375 e 387): mantém como tachado.
        targets.forEach((e) => e.replaceWith(document.createTextNode('⟦' + e.innerText.replace(/\s+/g, ' ').trim() + '⟧')));
      } else if (!vigente) {
        p.remove();
      } else {
        targets.forEach((e) => {
          const parte = e.innerText.replace(/\s+/g, ' ').trim();
          // Fragmentos sem palavra (ex.: só o "º" de "§ 6º") são ruído de formatação.
          const ruido = (parte.match(/[A-Za-zÀ-ÿ]/g) || []).length < 2;
          e.replaceWith(document.createTextNode(ruido ? parte : '⟦' + parte + '⟧'));
        });
      }
    }
  });
  c.querySelectorAll('strike,s,del,[data-struck]').forEach((e) => e.remove());
  const h = document.createElement('div');
  h.style.cssText = 'position:absolute;left:-99999px';
  h.appendChild(c);
  document.body.appendChild(h);
  const t = c.innerText
    .replace(/\t/g, ' ')
    .replace(/[  ]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{2,}/g, '\n');
  h.remove();
  window.__TEXTO_LEX__ = t;
  document.getElementById('lex-copiar')?.remove();
  const b = document.createElement('button');
  b.id = 'lex-copiar';
  b.textContent = 'COPIAR TEXTO DA LEI';
  b.style.cssText = 'position:fixed;top:10px;left:10px;z-index:99999;padding:20px;font-size:16px';
  b.onclick = () => {
    const ta = document.createElement('textarea');
    ta.value = window.__TEXTO_LEX__;
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    ta.remove();
    b.textContent = ok ? 'COPIADO ✓' : 'FALHOU';
  };
  document.body.prepend(b);
  window.scrollTo(0, 0);
  return { caracteres: t.length, artigos: (t.match(/\nArt\. ?\d/g) || []).length, revogadosTachados: (t.match(/⟦/g) || []).length };
})();
