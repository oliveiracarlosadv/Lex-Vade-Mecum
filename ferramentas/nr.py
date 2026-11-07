"""Monta e atualiza Normas Regulamentadoras (NR) do Ministério do Trabalho e Emprego.

Fonte: PDF oficial da NR no portal gov.br (o site aceita download direto).

Uso (na raiz do repositório):
    python3 ferramentas/nr.py --fonte nr-01 --baixar          # baixa o PDF oficial e atualiza
    python3 ferramentas/nr.py --fonte nr-01 --pdf arquivo.pdf # usa um PDF já salvo
    python3 ferramentas/nr.py --fonte nr-01                   # só regenera (após revisar anotações)

O texto é extraído com pdftotext (poppler) e reorganizado em dispositivos:
  - cada subitem numerado com conteúdo normativo é um dispositivo, com seus subitens
    internos (ex.: 1.4.3 reúne 1.4.3.1 a 1.4.3.3);
  - itens que são só títulos (ex.: "1.5.3 Responsabilidades") e títulos sem número
    viram a localização do dispositivo;
  - os glossários dos anexos ficam, cada um, em um único dispositivo.
Linhas descartadas: rodapé "Este texto não substitui o publicado no DOU", sumários e as
redações com vigência encerrada indicadas em config.json ("descartar").

Comparação com a conferência anterior (fontes/<fonte>/unidades.json): dispositivo alterado
ou incluído -> análise marcada como pendente de revisão e registro no CHANGELOG.
Saída: JSON na última linha (sem_alteracao / alterado / erro).
"""
import argparse, datetime, json, os, re, subprocess, sys, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ITEM = re.compile(r'^(\d+(?:\.\d+)+)\s+(?=[A-ZÀ-Ú])')          # 1.4.1 Cabe ...
SECAO_ANEXO = re.compile(r'^(\d+)\.\s+(?=[A-ZÀ-Ú])')           # 1. Objetivo (anexos)
ALINEA = re.compile(r'^[a-z]\)\s')
ROMANO = re.compile(r'^[IVX]+\.\s')
ANEXO = re.compile(r'^Anexo ([IVX]+) da NR-?\d+$')
NOTA_SECAO = re.compile(r'^(Redação dada pel[ao]|Entra em vigor|Incluíd[oa] pel[ao])\b')
NOTA_ALT = re.compile(r'^\((?:inserid|incluíd|alterad|redação|numeração|revogad|acrescentad)', re.I)
RODAPE = re.compile(r'^Este texto não substitui o publicado no DOU\s+\d+$')
VERBO = re.compile(r'\b(deve|devem|deverá|deverão|pode|podem|poderá|poderão|está|estão|é|são|cabe|compete|constitui|'
                   r'serão|será|ficam|fica|obrigam|aplica-se|consideram-se|considera-se|acarretará)\b')


def baixar(url, destino):
    req = urllib.request.Request(url, headers={'User-Agent': 'LexVadeMecum/1.0 (+https://github.com/oliveiracarlosadv/Lex-Vade-Mecum)'})
    with urllib.request.urlopen(req, timeout=120) as r:
        open(destino, 'wb').write(r.read())


def pdf_para_texto(pdf):
    r = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', pdf, '-'], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('pdftotext falhou: ' + r.stderr)
    return r.stdout


def linhas_logicas(bruto, cfg):
    """Junta as linhas quebradas pelo PDF em parágrafos (itens, alíneas, incisos, definições)."""
    L = [l.replace('\f', '').replace('\xa0', ' ').strip() for l in bruto.split('\n')]
    L = [l for l in L if not RODAPE.match(l)]
    # corpo: do marcador de início (após o sumário) até o fim
    ini = next(i for i, l in enumerate(L) if l == cfg['inicio'] and i > L.index(cfg['inicio_apos']) + 1
               and not L[i + 1].startswith(cfg['inicio'].split()[0][:2]))
    cab = [l for l in L[:ini] if l]
    out, branco, titulo_anexo, pular_sumario = [], False, 0, False
    for l in L[ini:]:
        if not l:
            branco = True
            if pular_sumario: pular_sumario = False
            continue
        if pular_sumario:
            continue
        if l.startswith('Sumário'):
            pular_sumario = True; continue
        l = re.sub(r'[ \t]+', ' ', l)
        if ANEXO.match(l):
            out.append({'tipo': 'anexo', 'txt': l}); titulo_anexo = 1; branco = False; continue
        if titulo_anexo:                                   # nome do anexo (pode ocupar 2 linhas)
            a = out[-1]
            if 'nome' not in a:
                a['nome'] = l; branco = False; continue
            if l[0].islower():
                a['nome'] += ' ' + l; branco = False; continue
            titulo_anexo = 0
        prev = out[-1] if out else None
        novo = bool(ITEM.match(l) or SECAO_ANEXO.match(l) or ALINEA.match(l) or ROMANO.match(l) or NOTA_SECAO.match(l))
        if not novo and prev and prev['tipo'] == 'linha':
            fim = prev['txt'][-1]
            if l[0].islower() or l[0].isdigit():
                novo = False                               # continuação da frase
            elif NOTA_ALT.match(l):
                novo = False                               # nota de alteração do parágrafo anterior
            elif l.startswith(('MTE', 'Portaria')) and fim not in '.;:)':
                novo = False
            elif fim in '.;:)!?' or branco:
                novo = True
            if SECAO_ANEXO.match(prev['txt']) and len(prev['txt']) < 60:
                novo = True                                # título de seção de anexo ocupa uma linha
            if re.match(r'^Exemplos?:', l):
                novo = False
        if novo or not prev or prev['tipo'] != 'linha':
            out.append({'tipo': 'linha', 'txt': l})
        else:
            sep = '' if prev['txt'].endswith('-') and not prev['txt'].endswith(' -') else ' '
            prev['txt'] += sep + l
        branco = False
    descartar = [re.compile(x) for x in cfg.get('descartar', [])]
    fora = [o for o in out if o['tipo'] == 'linha' and any(d.search(o['txt']) for d in descartar)]
    cfg['_descartados'] = [o['txt'] for o in fora]
    out = [o for o in out if o not in fora]
    return cab, out


def titulo(txt, num, anexo=None):
    """Item numerado que só nomeia uma divisão (sem verbo normativo)."""
    resto = txt[len(num):].strip()
    if resto.endswith(':'):
        return False
    return (num.count('.') == 1 and not anexo) or (len(resto) < 110 and not VERBO.search(resto))


def montar(L, cfg):
    """Separa títulos (localização) e dispositivos. Notas soltas antes de um título valem para a
    divisão inteira: ficam registradas na estrutura e repetidas no início do primeiro dispositivo."""
    units, estrutura = [], []
    anexo, path, cur, glossario, notas = None, [], None, None, []
    glos = cfg.get('glossarios', ['Termos e definições', 'Glossário'])

    def abre(part, num, rotulo, linhas):
        nonlocal cur, notas
        cur = {'part': part, 'num': num, 'rotulo': rotulo, 'path': list(path), 'lines': notas + linhas}
        notas = []; units.append(cur); return cur

    def cabecalho(nivel, rot):
        nonlocal cur
        estrutura.append({'nivel': nivel, 'rotulo': rot, 'notas': list(notas)}); cur = None

    for o in L:
        t = o['txt']
        if o['tipo'] == 'anexo':
            anexo = ANEXO.match(t).group(1); nome = o.get('nome', '').rstrip('.')
            path = [f'Anexo {anexo} — {nome}']; cabecalho(0, path[0]); glossario = None
            if any(nome.startswith(g) for g in glos):
                glossario = abre('A' + anexo, 'glossario', f'Anexo {anexo} — {nome}', [])
            continue
        if glossario is not None:
            glossario['lines'].append(t); continue
        if NOTA_SECAO.match(t):
            notas.append(t); continue
        m = ITEM.match(t); s = SECAO_ANEXO.match(t)
        if s and anexo and not m:
            path = path[:1] + [t]; cabecalho(1, t)
            if any(t[len(s.group(0)):].startswith(g) for g in glos):
                path = path[:1]; glossario = abre('A' + anexo, 'glossario', f'Anexo {anexo} — {t}', [])
            continue
        if m:
            num = m.group(1)
            if cur and num.startswith(cur['num'] + '.'):
                cur['lines'].append(t); continue
            if titulo(t, num, anexo):
                base = 2 if anexo else 0      # nos anexos: [anexo, seção]
                path = path[:base] + [p for p in path[base:] if ITEM.match(p) and num.startswith(ITEM.match(p).group(1) + '.')] + [t]
                cabecalho(num.count('.'), t); continue
            part = ('A' + anexo) if anexo else cfg['parte']
            abre(part, num, (f'Anexo {anexo} — Item {num}' if anexo else f'Item {num}'), [t]); continue
        solto = (not ALINEA.match(t) and not ROMANO.match(t) and not t.startswith('(') and t[0].isupper()
                 and len(t) < 110 and not VERBO.search(t) and (cur is None or cur['lines'][-1][-1] in '.;'))
        if solto:   # título sem número (ex.: "Aproveitamento de conteúdos de treinamento ...")
            path = [p for p in path if ITEM.match(p) or p.startswith('Anexo')] + [t]
            cabecalho(9, t); continue
        if cur is None:
            raise SystemExit('linha fora de dispositivo: ' + t[:120])
        cur['lines'].append(t)
    return units, estrutura


def conferir_integridade(bruto, cfg, L):
    """O texto reorganizado (sem espaços) deve ser idêntico ao corpo do PDF, tirando só rodapés,
    sumários e as redações descartadas por config."""
    sem = lambda t: re.sub(r'\s+', '', t)
    linhas = [l.replace('\f', '').strip() for l in bruto.split('\n')]
    linhas = [l for l in linhas if not RODAPE.match(l)]
    ini = next(i for i, l in enumerate(linhas) if l == cfg['inicio'] and i > linhas.index(cfg['inicio_apos']) + 1
               and not linhas[i + 1].startswith(cfg['inicio'].split()[0][:2]))
    corpo, pular = [], False
    for l in linhas[ini:]:
        if l.startswith('Sumário'): pular = True; continue
        if pular:
            if not l: pular = False
            continue
        corpo.append(l)
    fonte = sem('\n'.join(corpo))
    obtido = sem(''.join(o['txt'] + o.get('nome', '') for o in L))
    # retira da fonte os parágrafos descartados (procurando cada um, sem espaços)
    for txt in cfg.get('_descartados', []):
        fonte = fonte.replace(sem(txt), '', 1)
    return fonte == obtido


def ler_anotacoes(fonte):
    ann = {}
    for f in sorted(os.listdir(fonte)):
        if not (f.startswith('anotacoes') and f.endswith('.txt')):
            continue
        cur = None
        for line in open(os.path.join(fonte, f), encoding='utf-8'):
            line = line.rstrip('\n')
            if line.startswith('@'):
                cur = ann.setdefault(line[1:].strip(), {})
            elif cur is not None and line[:3] in ('I: ', 'P: ', 'K: '):
                cur[line[0]] = line[3:].strip()
    return ann


NORMA = (r'(?:Portaria(?: [A-Z]{2,5})?|Lei(?: Complementar)?|Decreto(?:-Lei)?|Resolução|Instrução Normativa)\s*n?[º°o.]*\s*[\d.]+(?:/\d{4})?'
         r'(?:,\s*de\s*\d{1,2}(?:º)?(?:\s*de\s*[a-zç]+\s*de\s*\d{4}|/\d{2}/\d{2,4}))?')
ALT = re.compile(r'\((inserid[oa]|incluíd[oa]|alterad[oa]|redação dada|numeração retificada)[^()]*?\)', re.I)


def alteracoes(u):
    out = []
    for l in u['lines']:
        for m in ALT.finditer(l):
            k = m.group(1).lower(); n = re.search(NORMA, m.group(0))
            tipo = ('inclusão' if k.startswith(('inser', 'inclu')) else 'redação' if k.startswith(('alter', 'reda')) else 'retificação')
            if tipo == 'retificação':
                item = 'retificação de numeração — ' + re.sub(r'^.*?(DOU.*)$', r'\1', m.group(0)[1:-1])
            else:
                item = f'{tipo} — {n.group(0) if n else m.group(0)[1:-1]}'
            if item not in out: out.append(item)
        if NOTA_SECAO.match(l):
            n = re.search(NORMA, l)
            tipo = 'vigência' if l.startswith('Entra em vigor') else 'inclusão' if l.startswith('Inclu') else 'redação'
            if n and f'{tipo} — {n.group(0)}' not in out: out.append(f'{tipo} — {n.group(0)}')
    return out


def remissoes(u, cfg):
    disp, normas = [], []
    t = ' '.join(u['lines'])
    limpo = ALT.sub(' ', t)
    for m in re.finditer(r'\b(?:subitens?|itens?|item)\s+(\d+(?:\.\d+)+(?:\s*(?:e|,)\s*\d+(?:\.\d+)+)*)', limpo):
        x = f'{m.group(0)} ({cfg["sigla"]})'
        if x not in disp: disp.append(x)
    for m in re.finditer(r'\bAnexo\s+[IVX]+\b', limpo):
        x = f'{m.group(0)} ({cfg["sigla"]})'
        if x not in disp: disp.append(x)
    for m in re.finditer(r'\bNR-\s?0?(\d+)\b|Norma Regulamentadora?e?s? nº 0?(\d+)', limpo):
        n = m.group(1) or m.group(2); x = f'NR-{int(n):02d}'
        if x != cfg['sigla'] and x not in normas: normas.append(x)
    for m in re.finditer(NORMA, t):
        x = re.sub(r'\s+', ' ', m.group(0)).strip()
        if x not in normas: normas.append(x)
    for m in re.finditer(r'\bLei \d[\d.]*/\d{4}|Consolidação das Leis do Trabalho', t):
        if m.group(0) not in normas: normas.append(m.group(0))
    return disp, normas


def esc(l):
    if re.match(r'^\d+\.\s', l): l = l.replace('.', '\\.', 1)
    elif re.match(r'^\d+\)\s', l): l = l.replace(')', '\\)', 1)
    if re.match(r'^[-*+]\s', l) or l.startswith(('#', '>', '|')): l = '\\' + l
    return l.replace('<', '&lt;')


def chave(u):
    return f'{u["part"]} {u["num"]}'


def bloco(u, a, pend, cfg):
    L = [f'### {u["rotulo"]}\n', f'**Localização:** {" › ".join(u["path"])}\n' if u['path'] else '']
    L += [esc(l) + '\n' for l in u['lines']]
    ch = alteracoes(u)
    if ch: L.append('> **Alterações legislativas registradas no texto oficial:** ' + '; '.join(ch) + '.\n')
    if not a and pend:
        a = {'I': 'Dispositivo incluído no texto oficial; interpretação pendente de elaboração.', 'P': 'Texto oficial já atualizado acima || Análise jurídica pendente', 'K': 'dispositivo novo; pendente de análise'}
    a = a or {}
    L.append('#### Interpretação\n')
    if pend:
        L.append(f"> ⚠️ **Texto oficial {pend['tipo']} no PDF do MTE (detectado em {pend['data']}).** A análise abaixo pode se referir à redação anterior e está pendente de revisão.\n")
    L.append(a.get('I', '') + '\n')
    L.append('#### Pontos Importantes\n'); L.append('\n'.join('- ' + x.strip() for x in a.get('P', '').split('||') if x.strip()) + '\n')
    L.append('#### Palavras-chave\n'); L.append('\n'.join('- ' + x.strip() for x in a.get('K', '').split(';') if x.strip()) + '\n')
    d, n = remissoes(u, cfg)
    L.append('#### Remissões de Lei\n')
    if not d and not n:
        L.append('Sem remissões expressas a outros dispositivos ou normas no texto do item.\n')
    else:
        if d: L.append('**Dispositivos citados no texto:**\n\n' + '\n'.join('- ' + x for x in d) + '\n')
        if n: L.append('**Normas citadas ou indicadas:**\n\n' + '\n'.join('- ' + x for x in n) + '\n')
    L.append('---\n')
    return '\n'.join(x for x in L if x)


def tabela_estrutura(units):
    linhas = ['| Divisão | Dispositivos | Quantidade |', '| --- | --- | --- |']
    grupos = []
    for u in units:
        g = u['path'][0] if u['path'] else '—'
        if grupos and grupos[-1][0] == g: grupos[-1][1].append(u)
        else: grupos.append([g, [u]])
    for g, us in grupos:
        nums = [x['num'] for x in us if x['num'] != 'glossario']
        faixa = ('glossário' if not nums else (f'{nums[0]} a {nums[-1]}' if len(nums) > 1 else nums[0]) + (' e glossário' if len(nums) < len(us) else ''))
        linhas.append(f'| {g} | {faixa} | {len(us)} |')
    linhas.append(f'| **Total** | | **{len(units)}** |')
    return '\n'.join(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fonte', required=True)
    ap.add_argument('--baixar', action='store_true')
    ap.add_argument('--pdf')
    ap.add_argument('--data', default=datetime.date.today().isoformat())
    a = ap.parse_args()
    F = os.path.join(RAIZ, 'fontes', a.fonte)
    cfg = json.load(open(os.path.join(F, 'config.json'), encoding='utf-8'))
    oficial = os.path.join(F, 'texto-oficial.txt')
    erro = lambda m: (print(json.dumps({'fonte': a.fonte, 'status': 'erro', 'detalhe': m}, ensure_ascii=False)), sys.exit(1))
    if a.baixar or a.pdf:
        pdf = a.pdf
        if a.baixar:
            pdf = os.path.join(F, '.tmp.pdf'); baixar(cfg['url'], pdf)
        bruto = pdf_para_texto(pdf)
        if a.baixar: os.remove(pdf)
    else:
        bruto = open(oficial, encoding='utf-8').read()

    _, L = linhas_logicas(bruto, cfg)
    if not conferir_integridade(bruto, cfg, L):
        erro('o texto reorganizado difere do PDF (fora rodapés, sumários e redações descartadas)')
    units, _ = montar(L, cfg)
    if len(units) < cfg.get('minimo', 0):
        erro(f'apenas {len(units)} dispositivos extraídos')
    vistos = set()
    for u in units:
        if chave(u) in vistos: erro('dispositivo duplicado: ' + chave(u))
        vistos.add(chave(u))

    dbr = datetime.date.fromisoformat(a.data).strftime('%d/%m/%Y')
    unid_path = os.path.join(F, 'unidades.json'); pend_path = os.path.join(F, 'pendentes.json')
    antigos = {chave(u): u['lines'] for u in json.load(open(unid_path, encoding='utf-8'))['units']} if os.path.exists(unid_path) else None
    pend = json.load(open(pend_path, encoding='utf-8')) if os.path.exists(pend_path) else {}
    alt, novos, retirados = [], [], []
    if antigos is not None:
        atuais = {chave(u): u['lines'] for u in units}
        alt = [k for k in atuais if k in antigos and antigos[k] != atuais[k]]
        novos = [k for k in atuais if k not in antigos]
        retirados = [k for k in antigos if k not in atuais]
        for k in alt: pend[k] = {'tipo': 'alterado', 'data': dbr}
        for k in novos: pend[k] = {'tipo': 'incluído', 'data': dbr}
        for k in retirados: pend.pop(k, None)
    mudou = bool(alt or novos or retirados)
    if mudou:
        log = os.path.join(F, 'CHANGELOG.md')
        antigo = open(log, encoding='utf-8').read() if os.path.exists(log) else f'# Histórico de alterações do texto oficial — {cfg["nome"]}\n'
        j = lambda xs: ', '.join(xs) or '—'
        ent = (f'\n## {dbr}\n\n- Dispositivos com texto alterado no PDF oficial: {j(alt)}\n- Dispositivos incluídos: {j(novos)}\n'
               f'- Dispositivos retirados: {j(retirados)}\n- Interpretações dos dispositivos alterados ou incluídos marcadas como pendentes de revisão.\n')
        h, _, c = antigo.partition('\n'); open(log, 'w', encoding='utf-8').write(h + '\n' + ent + c)
        json.dump(pend, open(pend_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    ann = ler_anotacoes(F)
    sem_ann = [chave(u) for u in units if chave(u) not in ann and chave(u) not in pend]
    ab_path = os.path.join(F, 'abertura.md')
    ab = open(ab_path, encoding='utf-8').read()
    if mudou:
        from_iso = datetime.date.fromisoformat(a.data)
        meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        ab = re.sub(r'(\| Texto obtido em \| )[^|]+(\|)', rf'\g<1>{from_iso.day} de {meses[from_iso.month - 1]} de {from_iso.year} \2', ab)
        open(ab_path, 'w', encoding='utf-8').write(ab)
    ab = ab.replace('<!-- ESTRUTURA_NR -->', tabela_estrutura(units))
    fe = open(os.path.join(F, 'fechamento.md'), encoding='utf-8').read()
    corpo = '\n'.join(bloco(u, ann.get(chave(u)), pend.get(chave(u)), cfg) for u in units)
    md = ab.rstrip('\n') + '\n\n## Texto Estruturado\n\n' + corpo + '\n' + fe.strip('\n') + '\n'

    tmp = os.path.join(F, '.tmp'); os.makedirs(tmp, exist_ok=True)
    up, mp = os.path.join(tmp, 'u.json'), os.path.join(tmp, 's.md')
    json.dump({'units': units}, open(up, 'w', encoding='utf-8'), ensure_ascii=False); open(mp, 'w', encoding='utf-8').write(md)
    v = subprocess.run([sys.executable, '-I', os.path.join(RAIZ, 'ferramentas', 'validate.py'), up, mp], capture_output=True, text=True)
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    m = re.search(r'idênticos ao texto oficial: (\d+) / (\d+)', v.stdout)
    if not m or m.group(1) != m.group(2) or 'seções presentes e em ordem: True' not in v.stdout:
        erro('validação: ' + v.stdout[-400:])
    if sem_ann:
        erro(f'{len(sem_ann)} dispositivos sem análise: {sem_ann[:15]}')

    saida = os.path.join(RAIZ, cfg['saida']); os.makedirs(os.path.dirname(saida), exist_ok=True)
    open(saida, 'w', encoding='utf-8').write(md)
    open(oficial, 'w', encoding='utf-8').write(bruto)
    if mudou or antigos is None:
        json.dump({'units': [{'part': u['part'], 'num': u['num'], 'lines': u['lines']} for u in units]},
                  open(unid_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    rd = os.path.join(RAIZ, 'README.md'); s = open(rd, encoding='utf-8').read().split('\n')
    for i, ln in enumerate(s):
        if ln.startswith('|') and f'({cfg["saida"]})' in ln:
            cols = ln.split('|'); cols[-2] = f' {dbr} '; s[i] = '|'.join(cols)
    open(rd, 'w', encoding='utf-8').write('\n'.join(s))
    print(json.dumps({'fonte': a.fonte, 'status': 'alterado' if mudou else 'sem_alteracao', 'dispositivos': len(units),
                      'alterados': alt, 'incluidos': novos, 'retirados': retirados, 'pendentes_de_revisao': len(pend)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
