"""Converte o XML do pdftohtml (Código de Ética e Disciplina da OAB) em texto
no formato usado pelo Lex Vade Mecum: um dispositivo por linha, notas de rodapé
entre parênteses no fim da linha que tem a chamada."""
import re, sys, html
import xml.etree.ElementTree as ET

src, dst = sys.argv[1], sys.argv[2]
raw = open(src, encoding='utf-8').read()
root = ET.fromstring(raw)

CORPO = {'3', '11', '4', '5', '10', '6'}   # fontes do texto (5 = chamada em negrito da capa)
CHAMADA = {'9', '5'}
NOTA_NUM, NOTA_TXT = '7', '8'

def texto(el):
    return html.unescape(''.join(el.itertext()))

linhas = []          # (pagina, top, left, [(left, txt, chamada?)])
notas = {}           # numero -> texto
for page in root.iter('page'):
    pn = int(page.get('number'))
    els = [e for e in page.iter('text')]
    # notas de rodapé: número (fonte 7) seguido de textos fonte 8
    atual = None
    for e in sorted(els, key=lambda e: (int(e.get('top')), int(e.get('left')))):
        f = e.get('font'); t = texto(e)
        if f == NOTA_NUM and t.strip().isdigit():
            atual = t.strip(); notas[atual] = ''
        elif f == NOTA_TXT and atual is not None:
            notas[atual] = re.sub(r'\s+', ' ', notas[atual] + ' ' + t).strip()
    corpo = []
    for e in els:
        f = e.get('font'); t = texto(e); top = int(e.get('top')); left = int(e.get('left'))
        if f in ('1', '2', '0'):                     # cabeçalho da página e capa
            continue
        if f == '3' and top > 980 and t.strip().isdigit():   # número da página
            continue
        if f in (NOTA_NUM, NOTA_TXT):
            continue
        if f not in CORPO and f not in CHAMADA:
            continue
        ch = f in CHAMADA and t.strip().isdigit()
        corpo.append((top, left, t, ch))
    corpo.sort(key=lambda x: (x[0], x[1]))
    grupos = []
    for top, left, t, ch in corpo:
        for g in grupos:
            if abs(g[0] - top) <= 5:
                g[2].append((left, t, ch)); break
        else:
            grupos.append([top, left, [(left, t, ch)]])
    for top, left, frag in sorted(grupos, key=lambda g: g[0]):
        frag.sort()
        linhas.append((pn, top, min(f[0] for f in frag), frag))

INICIO = re.compile(r'^(Art\.\s*\d|§\s*\d|Parágrafo único|[IVXLC]+\s*[–-]\s|[a-z]\)\s|TÍTULO\b|CAPÍTULO\b|SEÇÃO\b|SUBSEÇÃO\b|Brasília,|ANEXO|RESOLVE)')
paras = []           # [texto, [chamadas], cabecalho?]
for pn, top, left, frag in linhas:
    t = ''; chamadas = []
    for _, s, ch in frag:
        if ch: chamadas.append(s.strip()); t += '\u0000' + s.strip() + '\u0001'
        else: t += s
    t = re.sub(r'[  \t]+', ' ', t).strip()
    if not t.replace('\u0000', '').replace('\u0001', '').strip():
        continue
    plano = re.sub('\u0000\\d+\u0001', '', t)
    centralizado = left > 110
    maiusc = plano == plano.upper() and re.search(r'[A-ZÀ-Ú]', plano)
    cab = centralizado and (maiusc or re.match(r'(TÍTULO|CAPÍTULO|SEÇÃO)', plano))
    novo = (not paras) or cab or paras[-1][2] or INICIO.match(plano)
    if novo:
        paras.append([t, cab])
    else:
        ant = paras[-1][0]
        paras[-1][0] = ant + t if ant.endswith('-') else ant + ' ' + t
    paras[-1] = [paras[-1][0], paras[-1][1]] + [cab]

saida = []
for t, cab, _ in paras:
    nums = re.findall('\u0000(\\d+)\u0001', t)
    t = re.sub('\u0000\\d+\u0001', '', t).strip()
    t = re.sub(r' {2,}', ' ', t)
    notas_txt = [notas.get(n, f'[nota {n} não encontrada]').strip() for n in nums]
    if cab:
        saida.append(t)
        saida += [f'({n})' for n in notas_txt]
    else:
        saida.append(t + ''.join(f' ({n})' for n in notas_txt))
open(dst, 'w', encoding='utf-8').write('\n'.join(saida) + '\n')
print(len(saida), 'linhas;', len(notas), 'notas')
