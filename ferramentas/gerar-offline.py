#!/usr/bin/env python3
"""Gera dados-offline.js para abrir o index.html direto do computador (sem servidor).

O navegador não deixa uma página aberta como arquivo ler outros arquivos; por isso
este script embute o README e as leis em window.LEX_DADOS. Uso:
    python3 ferramentas/gerar-offline.py [pasta-de-saida]
O arquivo gerado não vai para o GitHub (o site on-line lê os .md diretamente).
"""
import json, pathlib, re, sys

raiz = pathlib.Path(__file__).resolve().parent.parent
saida = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else raiz
readme = (raiz / 'README.md').read_text(encoding='utf-8')
dados = {'README.md': readme}
for caminho in re.findall(r'\]\((leis/[^)]+\.md)\)', readme):
    dados[caminho] = (raiz / caminho).read_text(encoding='utf-8')
for extra in ('docs/manual-de-uso.md',):
    if (raiz / extra).exists():
        dados[extra] = (raiz / extra).read_text(encoding='utf-8')
js = 'window.LEX_DADOS = ' + json.dumps(dados, ensure_ascii=False) + ';\n'
(saida / 'dados-offline.js').write_text(js, encoding='utf-8')
print(f'{len([k for k in dados if k.startswith("leis/")])} leis embutidas em {saida / "dados-offline.js"} ({len(js) // 1024} KB)')
