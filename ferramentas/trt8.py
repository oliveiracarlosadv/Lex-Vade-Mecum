"""Monta e atualiza os Precedentes do TRT da 8ª Região (teses firmadas em IRDR e IAC).

Fonte: https://www.trt8.jus.br/jurisprudencia/precedentes (o site aceita download direto).

Uso (na raiz do repositório):
    python3 ferramentas/trt8.py --fonte trt8-precedentes --baixar          # baixa a página oficial e atualiza
    python3 ferramentas/trt8.py --fonte trt8-precedentes --html pagina.html # usa um HTML já salvo
    python3 ferramentas/trt8.py --fonte trt8-precedentes                    # só regenera (após revisar anotações)

Comparação com a conferência anterior (fontes/<fonte>/unidades.json):
  - tese ou título oficial alterado, ou precedente novo -> análise marcada como pendente de revisão;
  - mudança só no processo ou no link do acórdão -> registrada no CHANGELOG.
Saída: JSON na última linha (sem_alteracao / alterado / erro).
"""
import argparse, datetime, html, json, os, re, sys, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tst import esc, unesc, remissoes  # mesmas regras de escape e de remissões

BASE = 'https://www.trt8.jus.br'
TIPOS = {'IRDR': 'Incidente de Resolução de Demandas Repetitivas', 'IAC': 'Incidente de Assunção de Competência'}


def baixar(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'LexVadeMecum/1.0 (+https://github.com/oliveiracarlosadv/Lex-Vade-Mecum)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')


def texto(fragmento):
    t = re.sub(r'<br\s*/?>', '\n', fragmento)
    t = re.sub(r'</p>|</li>|</div>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', '', t)).replace('\xa0', ' ')
    linhas = [re.sub(r'[ \t]+', ' ', l).strip() for l in t.split('\n')]
    return '\n'.join(l for l in linhas if l)


def extrair(pagina):
    """Lê os blocos 'views-row' da página oficial (título, tese, processo e PDF de cada precedente)."""
    prec = []
    for bloco in re.split(r'<div class="views-row\b', pagina)[1:]:
        m = re.search(r'<a href="(/jurisprudencia/precedente/(irdr|iac)/(\d+))">(.*?)</a>', bloco, re.S)
        if not m:
            continue
        titulo = texto(m.group(4))
        mt = re.match(r'Precedente (IRDR|IAC) n[º°o]\s*(\d+)\s*-\s*(.*)$', titulo, re.S)
        if not mt:
            raise SystemExit('título inesperado: ' + titulo)
        corpo = re.search(r'views-field-body">\s*<div class="field-content">(.*?)</div>\s*</div>', bloco, re.S)
        proc = re.search(r'views-field-field-precedente-processo.*?<a href="([^"]+)"[^>]*>(.*?)</a>', bloco, re.S)
        prec.append({
            'tipo': mt.group(1), 'numero': mt.group(2), 'titulo': mt.group(3).strip(),
            'tese': texto(corpo.group(1)) if corpo else '',
            'processo': texto(proc.group(2)) if proc else '',
            'acordao': proc.group(1) if proc else '',
            'pagina': BASE + m.group(1),
        })
    return prec


def chave(u):
    return f'{u["tipo"]} {u["numero"]}'


def ler_anotacoes(path):
    ann, cur = {}, None
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('@'):
            cur = ann.setdefault(line[1:].strip(), {})
        elif cur is not None and line[:3] in ('I: ', 'P: ', 'K: ', 'T: '):
            cur[line[0]] = line[3:].strip()
    return ann


def bloco(u, a, pend):
    tit = (a or {}).get('T')
    cab = f'{u["tipo"]} nº {u["numero"]}'
    L = [f'### {cab} — {tit}\n' if tit else f'### {cab}\n']
    L.append(f'**Título oficial:** {u["titulo"]}\n')
    L.append(f'**Tipo:** {u["tipo"]} — {TIPOS[u["tipo"]]}\n')
    L.append(f'**Processo do acórdão:** {u["processo"] or "—"}\n')
    L.append(f'**Inteiro teor do acórdão:** {u["acordao"] or "—"}\n')
    L.append(f'**Página oficial:** {u["pagina"]}\n')
    L.append('**Tese firmada (texto oficial):**\n')
    for l in u['tese'].split('\n'):
        if l.strip(): L.append(esc(l) + '\n')
    L.append('#### Interpretação\n')
    if pend:
        L.append(f"> ⚠️ **Tese {pend['tipo']} no site do TRT8 (detectado em {pend['data']}).** A análise abaixo pode se referir à redação anterior e está pendente de revisão.\n")
    a = a or {'I': 'Precedente incluído na página oficial do TRT8; interpretação pendente de elaboração.', 'P': 'Tese oficial reproduzida acima || Análise jurídica pendente', 'K': 'precedente novo; pendente de análise'}
    L.append(a.get('I', '') + '\n')
    L.append('#### Pontos Importantes\n')
    L.append('\n'.join('- ' + x.strip() for x in a.get('P', '').split('||') if x.strip()) + '\n')
    L.append('#### Palavras-chave\n')
    L.append('\n'.join('- ' + x.strip() for x in a.get('K', '').split(';') if x.strip()) + '\n')
    disp, enun = remissoes(u['tese'] + '\n' + u['titulo'])
    L.append('#### Remissões de Lei\n')
    if not disp and not enun:
        L.append('Sem remissões expressas a dispositivos ou normas no texto da tese.\n')
    else:
        if disp: L.append('**Dispositivos citados:**\n\n' + '\n'.join('- ' + x for x in disp) + '\n')
        if enun: L.append('**Normas, súmulas, orientações e temas citados:**\n\n' + '\n'.join('- ' + x for x in enun) + '\n')
    L.append('---\n')
    return '\n'.join(L)


def validar(md, prec):
    corpo = md.split('\n## Texto Estruturado\n', 1)[1].split('\n## Direitos Garantidos\n', 1)[0]
    blocos = re.split(r'\n### (?=IRDR|IAC)', corpo)[1:]
    if len(blocos) != len(prec):
        return False, f'{len(blocos)} blocos para {len(prec)} precedentes'
    for u, b in zip(prec, blocos):
        cab = f'{u["tipo"]} nº {u["numero"]}'
        if not (b.startswith(cab + '\n') or b.startswith(cab + ' — ')):
            return False, f'ordem divergente em {cab}'
        if f'**Título oficial:** {u["titulo"]}\n' not in b:
            return False, f'título oficial de {cab} difere'
        tx = b.split('**Tese firmada (texto oficial):**\n', 1)[1].split('\n#### Interpretação\n', 1)[0]
        got = [unesc(l) for l in tx.split('\n') if l.strip()]
        exp = [l for l in u['tese'].split('\n') if l.strip()]
        if got != exp:
            return False, f'tese de {cab} difere do texto oficial'
    return True, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fonte', required=True)
    ap.add_argument('--baixar', action='store_true')
    ap.add_argument('--html')
    ap.add_argument('--data', default=datetime.date.today().isoformat())
    a = ap.parse_args()
    F = os.path.join(RAIZ, 'fontes', a.fonte)
    cfg = json.load(open(os.path.join(F, 'config.json'), encoding='utf-8'))
    oficial = os.path.join(F, 'tabela-oficial.json')
    if a.baixar or a.html:
        pagina = baixar(cfg['url']) if a.baixar else open(a.html, encoding='utf-8').read()
        prec = extrair(pagina)
        atualiz = re.findall(r'Atualizado em ([\d/]+ - [\d:]+)', pagina)
        meta = {'fonte': cfg['url'], 'atualizacao': atualiz[-1] if atualiz else '', 'precedentes': prec}
    else:
        meta = json.load(open(oficial, encoding='utf-8')); prec = meta['precedentes']
    if len(prec) < cfg.get('minimo', 0):
        print(json.dumps({'fonte': a.fonte, 'status': 'erro', 'detalhe': f'apenas {len(prec)} precedentes extraídos'}, ensure_ascii=False)); sys.exit(1)

    dbr = datetime.date.fromisoformat(a.data).strftime('%d/%m/%Y')
    unid_path = os.path.join(F, 'unidades.json'); pend_path = os.path.join(F, 'pendentes.json')
    antigos = {chave(u): u for u in json.load(open(unid_path, encoding='utf-8'))['precedentes']} if os.path.exists(unid_path) else None
    pend = json.load(open(pend_path, encoding='utf-8')) if os.path.exists(pend_path) else {}
    ann = ler_anotacoes(os.path.join(F, 'anotacoes.txt'))

    alt, novos, retirados, outros = [], [], [], []
    if antigos is not None:
        atuais = {chave(u) for u in prec}
        for u in prec:
            v = antigos.get(chave(u))
            if v is None: novos.append(chave(u)); continue
            if v['tese'] != u['tese'] or v['titulo'] != u['titulo']: alt.append(chave(u))
            elif v != u: outros.append(chave(u))
        retirados = [k for k in antigos if k not in atuais]
        for k in alt: pend[k] = {'tipo': 'alterada', 'data': dbr}
        for k in novos: pend[k] = {'tipo': 'incluída', 'data': dbr}
        for k in retirados: pend.pop(k, None)
    mudou_tese = bool(alt or novos or retirados)
    mudou = mudou_tese or bool(outros)

    if antigos is not None and mudou:
        log = os.path.join(F, 'CHANGELOG.md')
        antigo = open(log, encoding='utf-8').read() if os.path.exists(log) else f'# Histórico de alterações — {cfg["nome"]}\n'
        j = lambda xs: ', '.join(xs) or '—'
        ent = (f'\n## {dbr}\n\n- Teses ou títulos alterados: {j(alt)}\n- Precedentes incluídos: {j(novos)}\n- Precedentes retirados da página: {j(retirados)}\n'
               f'- Mudanças apenas de processo ou link do acórdão: {j(outros)}\n')
        if mudou_tese: ent += '- Análises dos precedentes alterados ou incluídos marcadas como pendentes de revisão.\n'
        h, _, c = antigo.partition('\n'); open(log, 'w', encoding='utf-8').write(h + '\n' + ent + c)
    if pend or os.path.exists(pend_path):
        json.dump(pend, open(pend_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    ab = open(os.path.join(F, 'abertura.md'), encoding='utf-8').read()
    n_irdr = sum(u['tipo'] == 'IRDR' for u in prec); n_iac = len(prec) - n_irdr
    ab = re.sub(r'(\| Precedentes na página \| )[^|]+(\|)', rf'\g<1>{len(prec)} ({n_irdr} IRDR e {n_iac} IAC) \2', ab)
    ab = re.sub(r'(\| Conferido com o site do TRT8 em \| )[^|]+(\|)', rf'\g<1>{dbr} \2', ab)
    open(os.path.join(F, 'abertura.md'), 'w', encoding='utf-8').write(ab)
    est = ['| Tipo | Quantidade | Precedentes |', '| --- | --- | --- |']
    for t in ('IRDR', 'IAC'):
        xs = [u for u in prec if u['tipo'] == t]
        if xs: est.append(f'| {t} — {TIPOS[t]} | {len(xs)} | ' + ', '.join(f'nº {u["numero"]}' for u in xs) + ' |')
    est.append(f'| **Total** | **{len(prec)}** | |')
    ab = ab.replace('<!-- ESTRUTURA_TRT8 -->', '\n'.join(est))
    fe = open(os.path.join(F, 'fechamento.md'), encoding='utf-8').read()
    corpo = '\n'.join(bloco(u, ann.get(chave(u)), pend.get(chave(u))) for u in prec)
    md = ab.rstrip('\n') + '\n\n## Texto Estruturado\n\n' + corpo + '\n' + fe.strip('\n') + '\n'
    ok, msg = validar(md, prec)
    sem_ann = [chave(u) for u in prec if chave(u) not in ann and chave(u) not in pend]
    if not ok or sem_ann:
        print(json.dumps({'fonte': a.fonte, 'status': 'erro', 'detalhe': msg if not ok else f'sem análise: {sem_ann}'}, ensure_ascii=False)); sys.exit(1)
    saida = os.path.join(RAIZ, cfg['saida']); os.makedirs(os.path.dirname(saida), exist_ok=True)
    open(saida, 'w', encoding='utf-8').write(md)
    json.dump(meta, open(oficial, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump({'precedentes': prec}, open(unid_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    rd = os.path.join(RAIZ, 'README.md'); s = open(rd, encoding='utf-8').read().split('\n')
    for i, ln in enumerate(s):
        if ln.startswith('|') and f'({cfg["saida"]})' in ln:
            cols = ln.split('|'); cols[-2] = f' {dbr} '; s[i] = '|'.join(cols)
    open(rd, 'w', encoding='utf-8').write('\n'.join(s))
    print(json.dumps({'fonte': a.fonte, 'status': 'alterado' if (mudou and antigos is not None) else 'sem_alteracao', 'precedentes': len(prec),
                      'alterados': alt, 'incluidos': novos, 'retirados': retirados, 'so_processo_ou_link': outros,
                      'pendentes_de_revisao': len(pend)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
