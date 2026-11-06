"""Monta e atualiza os Precedentes Vinculantes do TST (Recursos de Revista Repetitivos).

Fonte: tabela oficial em https://www.tst.jus.br/nugep-sp/recursos-repetitivos/precedentes-vinculantes,
extraída no navegador com ferramentas/extrair-tst.js (JSON com as linhas da tabela).

Uso (na raiz do repositório):
    python3 ferramentas/tst.py --fonte tst-precedentes --tabela /caminho/tabela.json [--data AAAA-MM-DD]
    python3 ferramentas/tst.py --fonte tst-precedentes            # só regenera (após revisar anotações)

Comparação com a conferência anterior (fontes/<fonte>/unidades.json):
  - tese alterada ou tema novo  -> análise marcada como pendente de revisão;
  - mudança só no andamento, suspensão, relator ou representativos -> registrada no CHANGELOG.
Saída: JSON na última linha (sem_alteracao / alterado / erro).
"""
import argparse, datetime, json, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPOS = ['tema', 'representativos', 'tese', 'movimento', 'suspensao', 'relator']


def carregar_tabela(path):
    d = json.load(open(path, encoding='utf-8'))
    linhas = d['linhas']
    if [c.strip().lower()[:4] for c in linhas[0]][:3] != ['tema', 'repr', 'tese']:
        raise SystemExit('cabeçalho inesperado na tabela: ' + repr(linhas[0]))
    temas = []
    for r in linhas[1:]:
        if len(r) != 6 or not r[0].strip():
            continue
        u = dict(zip(CAMPOS, [c.strip() for c in r]))
        u['tema'] = re.sub(r'\D', '', u['tema'])
        temas.append(u)
    return d, temas


def ler_anotacoes(path):
    ann, cur = {}, None
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('@'):
            cur = ann.setdefault(line[1:].split()[1], {})
        elif cur is not None and line[:3] in ('I: ', 'P: ', 'K: ', 'T: '):
            cur[line[0]] = line[3:].strip()
    return ann


def esc(l):
    if re.match(r'^\d+\.\s', l): l = l.replace('.', '\\.', 1)
    elif re.match(r'^\d+\)\s', l): l = l.replace(')', '\\)', 1)
    if re.match(r'^[-*+]\s', l) or l.startswith(('#', '>', '|')): l = '\\' + l
    return l.replace('<', '&lt;')


def unesc(l):
    if l.startswith('\\'): l = l[1:]
    elif re.match(r'^\d+\\[.)]', l): l = l.replace('\\', '', 1)
    return l.replace('&lt;', '<')


NORMA = r'(?:da CLT|do CPC(?: de 2015| de 1973|/2015)?|do Código Civil|do Código Penal|da Constituição(?: Federal| da República)?(?: de 1988)?|da CF|do ADCT|do Ato das Disposições Constitucionais Transitórias|da Lei(?: Complementar)? n[º°o.]* ?[\d.]+(?:/\d+)?|da NR[- ]?\d+)'


def remissoes(tese):
    t = re.sub(r'\s+', ' ', tese)
    disp, enun = [], []
    for m in re.finditer(r'\b(?:arts?\.|artigos?)\s*\d+[º°o]?(?:-[A-Z])?[^;.()]{0,80}?' + NORMA, t):
        x = m.group(0).strip()
        if x not in disp: disp.append(x)
    for m in re.finditer(r'\b(CPC|CLT|CF|CRFB|Código Civil|ADCT),\s*arts?\.\s*\d+[º°o]?(?:-[A-Z])?(?:,?\s*(?:§\s*\d+[º°o]?|inc(?:iso|\.)?\s*[IVXLC]+|[IVXLC]+\b|\"?[a-z]\"?\b|caput))*', t):
        x = m.group(0).strip().rstrip(',')
        if x not in disp: disp.append(x)
    for m in re.finditer(r'\b(Súmula(?: Vinculante)?|OJ|Orientação Jurisprudencial)\s*(?:n[º°o.]*\s*)?(\d+)(?:,\s*([IVX]+))?(?:\s*(?:da SB?DI-?1|da SbDI-1))?(?:\s*(?:do|deste|desta)\s*(TST|STF|STJ|Tribunal|Corte))?', t):
        x = m.group(0).strip().rstrip(',')
        if x not in enun: enun.append(x)
    for m in re.finditer(r'\b(?:Lei(?: Complementar)?|Decreto(?:-Lei)?|Portaria(?: MTE)?|Medida Provisória|Resolução|Instrução Normativa)\s*n?[º°o.]*\s*[\d.]+(?:/\d+)?(?:,\s*de\s*\d{1,2}[^,;)]{0,25}\d{4})?', t):
        x = m.group(0).strip().rstrip(',')
        if x not in enun: enun.append(x)
    for m in re.finditer(r'\bTemas?\s*(?:n[º°o.]*\s*)?[\d.]+(?: e [\d.]+)?\s*(?:da Tabela de [^.;]{0,60}?(?:do STF|do Supremo Tribunal Federal|do TST)|do STJ|do STF)', t):
        x = m.group(0).strip()
        if x not in enun: enun.append(x)
    return disp, enun


def bloco(u, a, pend):
    tit = (a or {}).get('T')
    L = [f'### Tema {u["tema"]} — {tit}\n' if tit else f'### Tema {u["tema"]}\n']
    L.append(f'**Situação (último movimento, conforme o TST):** {u["movimento"].replace(chr(10), " · ") or "—"}\n')
    L.append(f'**Há decisão de suspensão?** {u["suspensao"].replace(chr(10), " · ") or "—"}\n')
    L.append(f'**Relator(a):** {u["relator"].replace(chr(10), " · ") or "—"}\n')
    L.append(f'**Representativo(s) da controvérsia:** {u["representativos"].replace(chr(10), " · ") or "—"}\n')
    L.append('**Tese / Questão jurídica (texto oficial):**\n')
    for l in u['tese'].split('\n'):
        if l.strip(): L.append(esc(l) + '\n')
    L.append('#### Interpretação\n')
    if pend:
        L.append(f"> ⚠️ **Tese {pend['tipo']} no site do TST (detectado em {pend['data']}).** A análise abaixo pode se referir à redação anterior e está pendente de revisão.\n")
    a = a or {'I': 'Tema incluído na tabela oficial do TST; interpretação pendente de elaboração.', 'P': 'Tese oficial reproduzida acima || Análise jurídica pendente', 'K': 'tema novo; pendente de análise'}
    L.append(a.get('I', '') + '\n')
    L.append('#### Pontos Importantes\n')
    L.append('\n'.join('- ' + x.strip() for x in a.get('P', '').split('||') if x.strip()) + '\n')
    L.append('#### Palavras-chave\n')
    L.append('\n'.join('- ' + x.strip() for x in a.get('K', '').split(';') if x.strip()) + '\n')
    disp, enun = remissoes(u['tese'])
    L.append('#### Remissões de Lei\n')
    if not disp and not enun:
        L.append('Sem remissões expressas a dispositivos ou normas no texto da tese.\n')
    else:
        if disp: L.append('**Dispositivos citados na tese:**\n\n' + '\n'.join('- ' + x for x in disp) + '\n')
        if enun: L.append('**Normas, súmulas, orientações e temas citados:**\n\n' + '\n'.join('- ' + x for x in enun) + '\n')
    L.append('---\n')
    return '\n'.join(L)


def validar(md, temas):
    corpo = md.split('\n## Texto Estruturado\n', 1)[1].split('\n## Direitos Garantidos\n', 1)[0]
    blocos = re.split(r'\n### Tema ', corpo)[1:]
    if len(blocos) != len(temas):
        return False, f'{len(blocos)} blocos para {len(temas)} temas'
    for u, b in zip(temas, blocos):
        if not (b.startswith(u['tema'] + '\n') or b.startswith(u['tema'] + ' — ')):
            return False, f'ordem divergente no tema {u["tema"]}'
        tx = b.split('**Tese / Questão jurídica (texto oficial):**\n', 1)[1].split('\n#### Interpretação\n', 1)[0]
        got = [unesc(l) for l in tx.split('\n') if l.strip()]
        exp = [l for l in u['tese'].split('\n') if l.strip()]
        if got != exp:
            return False, f'tese do tema {u["tema"]} difere do texto oficial'
    return True, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fonte', required=True)
    ap.add_argument('--tabela')
    ap.add_argument('--data', default=datetime.date.today().isoformat())
    a = ap.parse_args()
    F = os.path.join(RAIZ, 'fontes', a.fonte)
    cfg = json.load(open(os.path.join(F, 'config.json'), encoding='utf-8'))
    oficial = os.path.join(F, 'tabela-oficial.json')
    meta, temas = carregar_tabela(a.tabela or oficial)
    if len(temas) < cfg.get('minimo_temas', 0):
        print(json.dumps({'fonte': a.fonte, 'status': 'erro', 'detalhe': f'apenas {len(temas)} temas extraídos'}, ensure_ascii=False)); sys.exit(1)

    dbr = datetime.date.fromisoformat(a.data).strftime('%d/%m/%Y')
    unid_path = os.path.join(F, 'unidades.json'); pend_path = os.path.join(F, 'pendentes.json')
    antigos = {u['tema']: u for u in json.load(open(unid_path, encoding='utf-8'))['temas']} if os.path.exists(unid_path) else None
    pend = json.load(open(pend_path, encoding='utf-8')) if os.path.exists(pend_path) else {}
    ann = ler_anotacoes(os.path.join(F, 'anotacoes.txt'))

    alt_tese, novos, retirados, andamento = [], [], [], []
    if antigos is not None:
        atuais = {u['tema'] for u in temas}
        for u in temas:
            v = antigos.get(u['tema'])
            if v is None: novos.append(u['tema']); continue
            if v['tese'] != u['tese']: alt_tese.append(u['tema'])
            elif any(v[c] != u[c] for c in CAMPOS if c != 'tese'): andamento.append(u['tema'])
        retirados = [t for t in antigos if t not in atuais]
        for t in alt_tese: pend[t] = {'tipo': 'alterada', 'data': dbr}
        for t in novos: pend[t] = {'tipo': 'incluída', 'data': dbr}
        for t in retirados: pend.pop(t, None)
    mudou_tese = bool(alt_tese or novos or retirados)
    mudou = mudou_tese or bool(andamento) or antigos is None

    if antigos is not None and mudou:
        log = os.path.join(F, 'CHANGELOG.md')
        antigo = open(log, encoding='utf-8').read() if os.path.exists(log) else f'# Histórico de alterações — {cfg["nome"]}\n'
        j = lambda xs: ', '.join(xs) or '—'
        ent = (f'\n## {dbr}\n\n- Teses alteradas: {j(alt_tese)}\n- Temas incluídos: {j(novos)}\n- Temas retirados da tabela: {j(retirados)}\n'
               f'- Mudanças apenas de andamento, suspensão, relator ou representativos: {j(andamento)}\n')
        if mudou_tese: ent += '- Análises dos temas com tese alterada ou incluída marcadas como pendentes de revisão.\n'
        h, _, c = antigo.partition('\n'); open(log, 'w', encoding='utf-8').write(h + '\n' + ent + c)
    json.dump(pend, open(pend_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1) if pend or os.path.exists(pend_path) else None

    ab = open(os.path.join(F, 'abertura.md'), encoding='utf-8').read()
    ab = re.sub(r'(\| Informações atualizadas pelo TST \| )[^|]+(\|)', r'\g<1>' + (meta.get('atualizacao', '').replace('Informações atualizadas em ', '').rstrip('.') or '—') + r' \2', ab)
    ab = re.sub(r'(\| Temas na tabela \| )[^|]+(\|)', r'\g<1>' + str(len(temas)) + r' \2', ab)
    if True:
        ab = re.sub(r'(\| Conferido com o site do TST em \| )[^|]+(\|)', r'\g<1>' + dbr + r' \2', ab)
    open(os.path.join(F, 'abertura.md'), 'w', encoding='utf-8').write(ab)
    fe = open(os.path.join(F, 'fechamento.md'), encoding='utf-8').read()
    from collections import Counter
    sit = Counter(re.sub(r'\s+', ' ', u['movimento'].split('\n')[0]).strip().rstrip('.').capitalize() or '—' for u in temas)
    grupos = {}
    for u in temas:
        k = re.sub(r'\s+', ' ', u['movimento'].split('\n')[0]).strip().rstrip('.').capitalize() or '—'
        grupos.setdefault(k, []).append(u['tema'])
    est = ['| Situação informada pelo TST (último movimento) | Quantidade | Temas |', '| --- | --- | --- |']
    for k, n in sit.most_common():
        est.append(f'| {k} | {n} | {", ".join(grupos[k])} |')
    est.append(f'| **Total** | **{len(temas)}** | Temas {temas[0]["tema"]} a {temas[-1]["tema"]} (a numeração tem lacunas, pois a tabela traz apenas os precedentes vinculantes) |')
    ab = ab.replace('<!-- ESTRUTURA_TST -->', '\n'.join(est))
    corpo = '\n'.join(bloco(u, ann.get(u['tema']), pend.get(u['tema'])) for u in temas)
    md = ab.rstrip('\n') + '\n\n## Texto Estruturado\n\n' + corpo + '\n' + fe.strip('\n') + '\n'
    ok, msg = validar(md, temas)
    sem_ann = [u['tema'] for u in temas if u['tema'] not in ann and u['tema'] not in pend]
    if not ok or sem_ann:
        print(json.dumps({'fonte': a.fonte, 'status': 'erro', 'detalhe': msg if not ok else f'temas sem análise: {sem_ann[:20]}'}, ensure_ascii=False)); sys.exit(1)
    saida = os.path.join(RAIZ, cfg['saida']); os.makedirs(os.path.dirname(saida), exist_ok=True)
    open(saida, 'w', encoding='utf-8').write(md)
    json.dump(meta, open(oficial, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump({'temas': temas}, open(unid_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

    rd = os.path.join(RAIZ, 'README.md'); s = open(rd, encoding='utf-8').read().split('\n')
    for i, ln in enumerate(s):
        if ln.startswith('|') and f'({cfg["saida"]})' in ln:
            cols = ln.split('|'); cols[-2] = f' {dbr} '; s[i] = '|'.join(cols)
    open(rd, 'w', encoding='utf-8').write('\n'.join(s))
    print(json.dumps({'fonte': a.fonte, 'status': 'alterado' if (mudou and antigos is not None) else 'sem_alteracao', 'temas': len(temas),
                      'teses_alteradas': alt_tese, 'incluidos': novos, 'retirados': retirados, 'so_andamento': andamento,
                      'pendentes_de_revisao': len(pend)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
