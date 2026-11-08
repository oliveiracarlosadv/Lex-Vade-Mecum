"""Atualiza uma norma do Lex Vade Mecum a partir do texto extraído do Planalto.

Uso (na raiz do repositório):
    python3 ferramentas/atualizar.py --lei cpc --texto /caminho/texto-extraido.txt [--data AAAA-MM-DD]
    python3 ferramentas/atualizar.py --lei cpc          # só regenera (após revisar anotações)

O texto é obtido com ferramentas/extrair-planalto.js na página oficial da norma.
O script:
  1. converte as marcas ⟦ ⟧ de dispositivos revogados em ~~tachado~~;
  2. separa os artigos e compara cada um com fontes/<lei>/unidades.json;
  3. registra artigos alterados, incluídos ou retirados em fontes/<lei>/CHANGELOG.md
     e marca os alterados/incluídos como pendentes de revisão (fontes/<lei>/pendentes.json);
  4. regenera leis/<lei>/<lei>-completa.md (texto oficial + análises) e valida
     que o texto de cada artigo é idêntico ao extraído;
  5. atualiza a data de conferência com o Planalto no README.
Saída: um resumo em JSON na última linha (sem_alteracao / alterado / erro).
"""
import argparse, json, os, re, subprocess, sys, datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FERR = os.path.join(RAIZ, 'ferramentas')

LAB = r'(?:(?:Art|Ar|At)\.[ \xa0]?\d+(?:\.\d{3})?(?:º|o|°)?(?:-[A-Z])?\.?|§ ?\d+(?:º|o|°)?(?:-[A-Z])?\.?|Parágrafo único\.?|[IVXLC]+(?:-[A-Z])? ?[-–]|[a-z]\))'


def converter_tachados(t):
    def fix(m):
        inner = m.group(1)
        mm = re.match(r'^(' + LAB + r')\s*(.*)$', inner, re.S)
        if mm and mm.group(2).strip():
            return mm.group(1) + ' ~~' + mm.group(2).strip() + '~~'
        return '~~' + inner.strip() + '~~' if inner.strip() else ''
    t = re.sub(r'⟦(.*?)⟧', fix, t, flags=re.S)
    return re.sub(r'^\s+', '', t, flags=re.M)


def descartar_vigencia_encerrada(t):
    """Remove redações de Medidas Provisórias que perderam a validade ("Vigência encerrada").

    O Planalto as mantém tachadas ao lado do texto vigente (comum na CLT). Uma linha é
    descartada quando, tirando o que está tachado, as notas entre parênteses e rótulos
    soltos, não sobra texto vigente. Quando um artigo tem várias versões, fica a vigente
    (não tachada) ou, se todas estão tachadas, a última (situação atual, ex.: revogado)."""
    def encerrada(l):
        if '⟦' not in l:
            return False
        if 'ncerrada' not in l:
            return False
        r = re.sub(r'⟦.*?⟧', '', l, flags=re.S)
        r = re.sub(r'\([^()]*\)', '', r)
        r = re.sub(r'Vig[eê]ncia encerrada', '', r, flags=re.I)
        r = re.sub(r'^\s*(§\s*\d+[ºo°]?(-[A-Z])?|Parágrafo único|Art|[A-Za-z]|[IVXLC]+\s*-)\s*', '', r)
        return len(re.findall(r'[A-Za-zÀ-ÿ]', r)) < 3
    # "A⟦rt. 28" (só a letra A fora do tachado) vira "⟦Art. 28"; marcas vazias "⟦⟧" saem.
    t = re.sub(r'^(\W*)A⟦rt', r'\1⟦Art', t.replace('⟦⟧', ''), flags=re.M)
    linhas = [l for l in t.split('\n') if not encerrada(l)]
    # Artigo com versão vigente (não tachada): versões tachadas do mesmo artigo são histórico
    # e saem junto com os parágrafos tachados que as acompanham.
    rot = re.compile(r'^\W*⟦?\s*(?:Art\.?|Ar\.|At\.)\s*(?:\.\s*)?(\d+(?:\.\d{3})*)(?:º|o|°)?(-[A-Z]|[A-Z](?=[.\s-]))?')
    def num(l):
        m = rot.match(l.replace('\xa0', ' '))
        return m and (m.group(1).replace('.', '') + (m.group(2) or '').lstrip('-'))
    vigentes = {num(l) for l in linhas if num(l) and not l.strip().startswith('⟦')}
    # Sem versão vigente, vale a última versão tachada (a situação atual, ex.: "Revogado por...").
    ultima = {}
    for i, l in enumerate(linhas):
        if num(l) and l.strip().startswith('⟦'):
            ultima[num(l)] = i
    saida, pulando = [], False
    for i, l in enumerate(linhas):
        n = num(l)
        if n:
            pulando = l.strip().startswith('⟦') and (n in vigentes or ultima.get(n) != i)
        elif pulando and not l.strip().startswith('⟦'):
            pulando = False
        if not pulando:
            saida.append(l)
    return '\n'.join(saida)


def data_br(iso):
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    d = datetime.date.fromisoformat(iso)
    return f'{d.day} de {meses[d.month - 1]} de {d.year}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lei', required=True)
    ap.add_argument('--texto', help='texto extraído do Planalto; se omitido, regenera a partir de fontes/<lei>/texto-oficial.txt (após revisar análises)')
    ap.add_argument('--data', default=datetime.date.today().isoformat())
    a = ap.parse_args()

    fonte = os.path.join(RAIZ, 'fontes', a.lei)
    cfg = json.load(open(os.path.join(fonte, 'config.json'), encoding='utf-8'))
    tmp = os.path.join(fonte, '.tmp')
    os.makedirs(tmp, exist_ok=True)

    oficial = os.path.join(fonte, 'texto-oficial.txt')
    bruto = open(a.texto or oficial, encoding='utf-8').read()
    if cfg.get('descartar_vigencia_encerrada'):
        bruto = descartar_vigencia_encerrada(bruto)
    texto = converter_tachados(bruto)
    texto_path = os.path.join(tmp, 'texto.txt')
    open(texto_path, 'w', encoding='utf-8').write(texto)

    saida = os.path.join(RAIZ, cfg['saida'])
    pend_path = os.path.join(fonte, 'pendentes.json')
    build_cfg = {
        'text': texto_path,
        'parts': cfg['parts'],
        'ann': sorted(os.path.join(fonte, f) for f in os.listdir(fonte) if f.startswith('anotacoes') and f.endswith('.txt')),
        'front': os.path.join(fonte, 'abertura.md'),
        'back': os.path.join(fonte, 'fechamento.md'),
        'out': os.path.join(tmp, 'saida.md'),
        'units_out': os.path.join(tmp, 'unidades-novas.json'),
        'pendentes': pend_path,
    }
    cfg_path = os.path.join(tmp, 'build.json')
    json.dump(build_cfg, open(cfg_path, 'w', encoding='utf-8'), ensure_ascii=False)

    # 1ª passagem: só para obter as unidades novas
    r = subprocess.run([sys.executable, '-I', os.path.join(FERR, 'lexbuild.py'), cfg_path], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        print(json.dumps({'lei': a.lei, 'status': 'erro', 'etapa': 'extração de artigos', 'detalhe': (r.stderr or r.stdout)[-500:]}, ensure_ascii=False))
        sys.exit(1)
    novas = json.load(open(build_cfg['units_out'], encoding='utf-8'))['units']
    antigas = json.load(open(os.path.join(fonte, 'unidades.json'), encoding='utf-8'))['units']
    minimo = cfg.get('minimo_artigos', 0)
    if len(novas) < minimo:
        print(json.dumps({'lei': a.lei, 'status': 'erro', 'etapa': 'conferência', 'detalhe': f'apenas {len(novas)} artigos extraídos (mínimo esperado {minimo}); extração provavelmente incompleta'}, ensure_ascii=False))
        sys.exit(1)

    k = lambda u: u['part'] + ' ' + u['num']
    A = {k(u): u['lines'] for u in antigas}
    B = {k(u): u['lines'] for u in novas}
    alterados = [x for x in B if x in A and A[x] != B[x]]
    incluidos = [x for x in B if x not in A]
    retirados = [x for x in A if x not in B]

    pend = json.load(open(pend_path, encoding='utf-8')) if os.path.exists(pend_path) else {}
    dbr = datetime.date.fromisoformat(a.data).strftime('%d/%m/%Y')
    for x in alterados:
        pend[x] = {'tipo': 'alterado', 'data': dbr}
    for x in incluidos:
        pend[x] = {'tipo': 'incluído', 'data': dbr}
    for x in retirados:
        pend.pop(x, None)
    mudou = bool(alterados or incluidos or retirados)

    if mudou:
        json.dump(pend, open(pend_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        ab = os.path.join(fonte, 'abertura.md')
        s = open(ab, encoding='utf-8').read()
        s = re.sub(r'(\| Texto obtido em \| )[^|]+(\|)', r'\g<1>' + data_br(a.data) + r' \2', s)
        open(ab, 'w', encoding='utf-8').write(s)
        log = os.path.join(fonte, 'CHANGELOG.md')
        antigo = open(log, encoding='utf-8').read() if os.path.exists(log) else f'# Histórico de alterações do texto oficial — {cfg["nome"]}\n'
        rot = lambda xs: ', '.join(x.split(' ', 1)[1] if x.split(' ', 1)[0] == cfg['parts'][0]['id'] else x for x in xs) or '—'
        entrada = (f'\n## {dbr}\n\n- Artigos com texto alterado no Planalto: {rot(alterados)}\n'
                   f'- Artigos incluídos: {rot(incluidos)}\n- Artigos retirados do texto: {rot(retirados)}\n'
                   f'- Interpretações dos artigos alterados ou incluídos marcadas como pendentes de revisão.\n')
        head, _, corpo = antigo.partition('\n')
        open(log, 'w', encoding='utf-8').write(head + '\n' + entrada + corpo)

    # 2ª passagem: gera o Markdown final com as pendências
    r = subprocess.run([sys.executable, '-I', os.path.join(FERR, 'lexbuild.py'), cfg_path], capture_output=True, text=True)
    if r.returncode != 0:
        print(json.dumps({'lei': a.lei, 'status': 'erro', 'etapa': 'geração', 'detalhe': (r.stderr or r.stdout)[-500:]}, ensure_ascii=False))
        sys.exit(1)
    v = subprocess.run([sys.executable, '-I', os.path.join(FERR, 'validate.py'), build_cfg['units_out'], build_cfg['out']], capture_output=True, text=True)
    m = re.search(r'idênticos ao texto oficial: (\d+) / (\d+)', v.stdout)
    if not m or m.group(1) != m.group(2) or 'seções presentes e em ordem: True' not in v.stdout:
        print(v.stdout)
        print(json.dumps({'lei': a.lei, 'status': 'erro', 'etapa': 'validação', 'detalhe': v.stdout[-500:]}, ensure_ascii=False))
        sys.exit(1)

    os.makedirs(os.path.dirname(saida), exist_ok=True)
    os.replace(build_cfg['out'], saida)
    open(oficial, 'w', encoding='utf-8').write(texto)
    if mudou:
        snap = [{'part': u['part'], 'num': u['num'], 'lines': u['lines']} for u in novas]
        json.dump({'units': snap}, open(os.path.join(fonte, 'unidades.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

    # data de conferência no README
    rd = os.path.join(RAIZ, 'README.md')
    s = open(rd, encoding='utf-8').read()
    link = f'({cfg["saida"]})'
    linhas = s.split('\n')
    for i, ln in enumerate(linhas):
        if ln.startswith('|') and link in ln:
            cols = ln.split('|')
            cols[-2] = f' {dbr} '
            linhas[i] = '|'.join(cols)
    open(rd, 'w', encoding='utf-8').write('\n'.join(linhas))
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print(json.dumps({'lei': a.lei, 'status': 'alterado' if mudou else 'sem_alteracao', 'artigos': len(novas),
                      'alterados': alterados, 'incluidos': incluidos, 'retirados': retirados,
                      'pendentes_de_revisao': len(pend)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
