// Extrator da tabela de Precedentes Vinculantes (Recursos de Revista Repetitivos) do TST.
// Executar na página https://www.tst.jus.br/nugep-sp/recursos-repetitivos/precedentes-vinculantes
// aberta no navegador. Gera um JSON com as linhas da tabela em window.__TABELA_TST__ e
// insere no topo o botão "COPIAR TABELA DO TST"; um clique copia o JSON para a área de
// transferência. Não aceite banners de cookies além do necessário.
(() => {
  const norm = (s) =>
    s.replace(/\t/g, ' ').replace(/[  ]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{2,}/g, '\n').trim();
  const tb = document.querySelector('table');
  if (!tb) return { erro: 'tabela não encontrada' };
  const linhas = [...tb.querySelectorAll('tr')].map((r) => [...r.children].map((c) => norm(c.innerText)));
  const atualizacao = (document.body.innerText.match(/Informações atualizadas em [^\n]+/) || [''])[0].trim();
  window.__TABELA_TST__ = JSON.stringify({ fonte: location.href, atualizacao, linhas });
  document.getElementById('lex-copiar')?.remove();
  const b = document.createElement('button');
  b.id = 'lex-copiar';
  b.textContent = 'COPIAR TABELA DO TST';
  b.style.cssText = 'position:fixed;top:10px;left:10px;z-index:99999;padding:20px;font-size:16px';
  b.onclick = () => {
    const ta = document.createElement('textarea');
    ta.value = window.__TABELA_TST__;
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    ta.remove();
    b.textContent = ok ? 'COPIADO ✓' : 'FALHOU';
  };
  document.body.prepend(b);
  window.scrollTo(0, 0);
  const cols = {};
  linhas.forEach((l) => (cols[l.length] = (cols[l.length] || 0) + 1));
  return { atualizacao, linhas: linhas.length, colunas: cols, caracteres: window.__TABELA_TST__.length };
})();
