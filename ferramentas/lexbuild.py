"""Monta o Markdown de uma norma: texto oficial (extraído por script) + anotações.

Uso: python3 -I lexbuild.py config.json
config: {
  "text": arquivo .txt extraído do Planalto,
  "parts": [{"id": "L", "start": "Art. 1o", "end": "Rio de Janeiro, 4", "label_prefix": "", "self_name": "desta Lei"}],
  "ann": [arquivos de anotação], "front": md antes do Texto Estruturado,
  "back": md depois do Texto Estruturado, "out": arquivo .md final,
  "units_out": json com as unidades (para validação)
}
"""
import json, re, sys, glob, os

cfg = json.load(open(sys.argv[1], encoding='utf-8'))
L = [l.strip() for l in open(cfg['text'], encoding='utf-8').read().split('\n')]

# Cabeçalhos com letras espaçadas ("P A R T E   G E R A L", no Código Civil) viram "PARTE GERAL".
# Só afeta linhas formadas por letras soltas; o texto dos artigos não muda.
def _espacado(l):
    if not re.fullmatch(r'(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ]\s+){3,}[A-ZÁÉÍÓÚÂÊÔÃÕÇ]', l): return l
    s = re.sub(r'\s+', '', l)
    return re.sub(r'^(PARTE|LIVRO)(?=[A-Z])', r'\1 ', s)
# Cabeçalhos sem acento ("TITULO III", "CAPITULO I", no Código Civil) recebem o acento.
def _acento(l):
    return re.sub(r'^(SUB)?TITULO(?=\s)', lambda m: (m.group(1) or '') + 'TÍTULO', re.sub(r'^CAPITULO(?=\s)', 'CAPÍTULO', l))
L = [_acento(_espacado(l)) for l in L]

HEAD = re.compile(r'^(SUBTÍTULO|TÍTULO|CAPÍTULO|SEÇÃO|Seção|SUBSEÇÃO|Subseção|LIVRO|PARTE)\s+([IVXLC]+(-[A-Z])?|ÚNIC[OA]|GERAL|ESPECIAL|COMPLEMENTAR|PRIMEIRO|SEGUNDO|TERCEIRO|QUARTO|QUINTO)\b\s*(.*)$')
# \s aceita também o espaço não separável (U+00A0) que o Planalto às vezes usa após "Art."
# Aceita "Arts. 52 a 58 (Revogados...)" (intervalo revogado, CTN) como uma unidade.
# Aceita ainda "Art. 759.(Revogado..." sem espaço (Código Civil).
# Também aceita "Art. . 154" (ponto duplicado) e "Art. 401A" (letra sem hífen), grafias presentes na CLT.
ART = re.compile(r'^Arts?\.?\s*(?:\.\s*)?(\d+(?:\.\d{3})*)(º|o|°|\.)?(-[A-Z]|[A-Z](?=[.\s-]))?\.?(?:\s|(?=\())')
LEVEL = {'PARTE': 0, 'LIVRO': 1, 'TÍTULO': 2, 'SUBTÍTULO': 3, 'CAPÍTULO': 4, 'SEÇÃO': 5, 'Seção': 5, 'SUBSEÇÃO': 6, 'Subseção': 6}

def find(prefix, start=0):
    for i in range(start, len(L)):
        if L[i].startswith(prefix):
            return i
    raise SystemExit(f'marcador não encontrado: {prefix}')

units, structure = [], []
pos = 0
for p in cfg['parts']:
    a = find(p['start'], pos)
    b = find(p['end'], a + 1)
    pos = b
    path = [None] * 7
    cur = None
    i = a
    while i < b:
        l = L[i]
        if not l:
            i += 1; continue
        m = HEAD.match(l)
        if m and not ART.match(l):
            lv = 0 if m.group(2) == 'COMPLEMENTAR' else LEVEL[m.group(1)]
            name = m.group(4).strip()
            j = i + 1; notes = []; parts = [name] if name else []
            while j < b and not ART.match(L[j]) and not HEAD.match(L[j]):
                if L[j].startswith('('): notes.append(L[j])
                # Linhas tachadas ou dispositivos soltos (§, incisos, alíneas de artigo revogado)
                # não fazem parte do nome do Título/Capítulo/Seção.
                elif '~~' in L[j] or re.match(r'^(§|Parágrafo|[IVXLC]+(-[A-Z])?\s*[-–]|[a-z]\))', L[j]): pass
                elif L[j]: parts.append(L[j])
                j += 1
            name = ' '.join(parts).replace(' Regulamento', '').replace('Estados,Distrito', 'Estados, Distrito')
            label = m.group(1).upper() + ' ' + m.group(2)
            path[lv] = f'{label} — {name}' if name else label
            for k in range(lv + 1, 7): path[k] = None
            structure.append({'part': p['id'], 'level': lv, 'label': label, 'name': name, 'notes': notes})
            cur = None; i = j; continue
        m = ART.match(l)
        if m:
            letra = m.group(3) or ''
            num = m.group(1).replace('.', '') + (('-' + letra) if letra and not letra.startswith('-') else letra)
            cur = {'part': p['id'], 'num': num, 'path': [x for x in path if x], 'lines': [l]}
            units.append(cur)
            structure.append({'part': p['id'], 'level': 9, 'art': num})
            i += 1; continue
        if cur: cur['lines'].append(l)
        elif p.get('preamble') and not units:
            units.append({'part': p['id'], 'num': 'preambulo', 'path': [], 'lines': [l]})
        i += 1

seen = set()
for u in units:
    k = (u['part'], u['num'])
    if k in seen: raise SystemExit(f'artigo duplicado: {k}')
    seen.add(k)

ann = {}
for f in cfg['ann']:
    for path in sorted(glob.glob(f)):
        cur = None
        for line in open(path, encoding='utf-8'):
            line = line.rstrip('\n')
            if line.startswith('@'):
                part, num = line[1:].split(None, 1); cur = ann.setdefault((part, num.strip()), {})
            elif cur is not None and line[:3] in ('I: ', 'P: ', 'K: '):
                cur[line[0]] = line[3:].strip()

NORM = r'(?:Emenda Constitucional(?: de Revisão)?|Lei Complementar|Decreto-[Ll]ei|Decreto Legislativo|Decreto|Lei|Medida Provisória|Resolução|Ato Institucional)\s+n[ºo°]\.?\s*[\d.]+(?:-[A-Z])?(?:,\s*de\s*(?:\d{1,2}(?:º|o)?\s*(?:de\s*)?[a-zç]+\s*de\s*)?[\d.]+(?:/\d+)?)?'
CHG = re.compile(r'\((Redação dada|Incluíd[oa]|Revogad[oa]|Acrescentad[oa]|Renumerad[oa]|Vetad[oa])[^()]*?(' + NORM + r')[^()]*\)', re.I)
VIDE = re.compile(r'\(Vide\s+([^()]*(?:\([^()]*\)[^()]*)*)\)', re.I)
NOTES = re.compile(r'\((?:Redação dada|Incluíd[oa]|Revogad[oa]|Acrescentad[oa]|Renumerad[oa]|Vetad[oa]|Regulamento|Vigência|Vide)[^()]*(?:\([^()]*\)[^()]*)*\)|\bVigência\b|\(Regulamento\)', re.I)
REF = re.compile(r'\b(arts?\.|artigos?)\s*(\d+(?:º|°|o)?(?:-[A-Z])?(?:(?:,\s*|\s+e\s+)\d+(?:º|°|o)?(?:-[A-Z])?)*)((?:(?:,\s*|\s+)(?:§§?\s*\d+(?:º|°|o)?(?:-[A-Z])?(?:\s*(?:e|a)\s*\d+(?:º|°|o)?(?:-[A-Z])?)?|caput|inciso\s+[IVXLC]+(?:-[A-Z])?|incisos\s+[IVXLC]+(?:\s*(?:e|a)\s*[IVXLC]+)?|[IVXLC]+(?:-[A-Z])?\b|"[a-z]"|alíneas?\s+"?[a-z]"?|(?:do|da|deste|desta)\s+(?:caput|parágrafo único)))*)')
QUAL = [(re.compile(r'^[^.;]{0,25}?\b(?:da|desta) Constituição(?: Federal)?'), 'Constituição Federal'),
        (re.compile(r'^[^.;]{0,25}?\bdeste Ato das Disposições Constitucionais Transitórias|^[^.;]{0,25}?\bdo ADCT|^[^.;]{0,25}?\bdeste Ato'), 'ADCT'),
        (re.compile(r'^[^.;]{0,25}?\b(?:do|da) (' + NORM + ')'), None)]

def changes(u):
    out = []
    for l in u['lines']:
        for m in CHG.finditer(l):
            k = m.group(1).lower()
            kind = ('redação' if k.startswith('reda') else 'inclusão' if k.startswith(('inclu', 'acresc')) else
                    'revogação' if k.startswith('revog') else 'veto' if k.startswith('vet') else 'renumeração')
            item = f'{kind} — {m.group(2).strip()}'
            if item not in out: out.append(item)
    return out

def remissions(u, part_cfg):
    dispositivos, normas = [], []
    for l in u['lines']:
        for m in VIDE.finditer(l):
            v = re.sub(r'\s+', ' ', m.group(1)).strip()
            if v and v not in normas: normas.append(v)
        clean = NOTES.sub(' ', l)
        for m in REF.finditer(clean):
            ref = re.sub(r'\s+', ' ', (m.group(1) + ' ' + m.group(2) + m.group(3))).strip().rstrip(',')
            after = clean[m.end():]
            where = part_cfg.get('self_name', 'desta norma')
            for rx, name in QUAL:
                q = rx.match(after)
                if q:
                    where = name if name else q.group(1); break
            item = f'{ref} ({where})'
            if item not in dispositivos: dispositivos.append(item)
        for m in re.finditer(NORM, clean):
            n = re.sub(r'\s+', ' ', m.group(0)).strip().rstrip(',')
            if n not in normas: normas.append(n)
    return dispositivos, normas

def esc(l):
    if re.match(r'^\d+\.\s', l): l = l.replace('.', '\\.', 1)
    elif re.match(r'^\d+\)\s', l): l = l.replace(')', '\\)', 1)
    if re.match(r'^[-*+]\s', l) or l.startswith(('#', '>', '|')): l = '\\' + l
    return l.replace('<', '&lt;')

def label(u, pc):
    if u['num'] == 'preambulo': return 'Preâmbulo'
    n = u['num']; base = int(re.match(r'\d+', n).group())
    n = n if '-' in n else (n + 'º' if base <= 9 else n)
    n = re.sub(r'^(\d)(\d{3})', r'\1.\2', n)
    return pc.get('label_prefix', '') + f'Art. {n}'

def only_marker(u, word):
    t = ' '.join(u['lines']); return len(t) < 160 and word in t

pcfg = {p['id']: p for p in cfg['parts']}
PEND = json.load(open(cfg['pendentes'], encoding='utf-8')) if cfg.get('pendentes') and os.path.exists(cfg['pendentes']) else {}
out, missing = [], []
for u in units:
    pc = pcfg[u['part']]
    a = ann.get((u['part'], u['num']))
    out.append(f'### {label(u, pc)}\n')
    loc = ' › '.join(u['path']) if u['path'] else pc.get('root_name', '')
    if pc.get('loc_prefix'): loc = pc['loc_prefix'] + (' › ' + loc if u['path'] else '')
    if loc: out.append(f'**Localização:** {loc}\n')
    for l in u['lines']: out.append(esc(l) + '\n')
    ch = changes(u)
    if ch: out.append('> **Alterações legislativas registradas no texto oficial:** ' + '; '.join(ch) + '.\n')
    if not a and only_marker(u, 'Revogad'):
        a = {'I': 'Dispositivo revogado, conforme indicado no texto oficial. A numeração é mantida para preservar a referência histórica e as remissões feitas por outras normas.',
             'P': 'Sem eficácia normativa atual || A revogação está registrada no próprio texto compilado || Consultar a norma revogadora para a disciplina vigente da matéria',
             'K': 'dispositivo revogado; revogação; histórico legislativo'}
    pend = PEND.get(u['part'] + ' ' + u['num'])
    if not a and pend:
        a = {'I': 'Dispositivo incluído no texto oficial do Planalto; interpretação pendente de elaboração.', 'P': 'Texto oficial já atualizado acima || Análise jurídica pendente', 'K': 'dispositivo novo; pendente de análise'}
    if not a:
        missing.append(u['part'] + ' ' + u['num']); a = {}
    out.append('#### Interpretação\n')
    if pend:
        out.append(f"> ⚠️ **Texto oficial {pend['tipo']} no Planalto (detectado em {pend['data']}).** A análise abaixo pode se referir à redação anterior e está pendente de revisão.\n")
    out.append(a.get('I', '') + '\n')
    out.append('#### Pontos Importantes\n'); out.append('\n'.join('- ' + x.strip() for x in a.get('P', '').split('||') if x.strip()) + '\n')
    out.append('#### Palavras-chave\n'); out.append('\n'.join('- ' + x.strip() for x in a.get('K', '').split(';') if x.strip()) + '\n')
    d, n = remissions(u, pc)
    out.append('#### Remissões de Lei\n')
    if not d and not n:
        out.append('Sem remissões expressas a outros dispositivos ou normas no texto do artigo.\n')
    else:
        if d: out.append('**Dispositivos citados no texto:**\n\n' + '\n'.join('- ' + x for x in d) + '\n')
        if n: out.append('**Normas citadas ou indicadas (inclusive em notas "Vide"):**\n\n' + '\n'.join('- ' + x for x in n) + '\n')
    out.append('---\n')

front = open(cfg['front'], encoding='utf-8').read().rstrip('\n') if cfg.get('front') else ''
back = open(cfg['back'], encoding='utf-8').read().strip('\n') if cfg.get('back') else ''
doc = front + '\n\n## Texto Estruturado\n\n' + '\n'.join(out) + '\n' + back + '\n'
open(cfg['out'], 'w', encoding='utf-8').write(doc)
if cfg.get('units_out'):
    json.dump({'units': units, 'structure': structure}, open(cfg['units_out'], 'w', encoding='utf-8'), ensure_ascii=False)
print('unidades:', len(units), '| sem anotação:', len(missing), missing[:30])
