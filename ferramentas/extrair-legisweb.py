#!/usr/bin/env python3
"""Extrai o texto de uma norma da página do LegisWeb (legisweb.com.br/legislacao/?id=N).

Uso: python3 -I ferramentas/extrair-legisweb.py pagina.html > texto.txt

- Lê só o bloco "legislacao-completa" (texto da norma e anexos).
- Cada <p> vira uma linha; cada linha de tabela (<tr>) vira uma linha com as
  células separadas por " | ".
- Texto com a classe "revogado" (que o LegisWeb exibe riscado) vira ⟦texto⟧,
  seguido da nota "(Revogado pela ...)" que o LegisWeb põe na linha anterior;
  o atualizar.py converte ⟦ ⟧ em ~~tachado~~, como nas leis do Planalto.
- Notas que anunciam o item seguinte ("(Artigo acrescentado pela Lei ...):") vão
  para o fim da linha desse item; o mesmo vale para as notas editoriais
  "Nota Legisweb: ..." (postas entre parênteses).
- Cabeçalhos com número e nome na mesma linha ("TÍTULO I - DAS DISPOSIÇÕES
  GERAIS", "Livro SEGUNDO - NORMAS GERAIS") são separados em duas linhas, e
  "Livro" passa a "LIVRO", para o leitor de estrutura reconhecê-los. Nota entre
  parênteses no fim do nome vai para a linha seguinte.
"""
import html, re, sys
from html.parser import HTMLParser

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []          # (texto, revogado?)
        self.buf = []; self.rev = 0; self.cells = None; self.cell = None; self.skip = 0
        self.ativo = False; self.prof = 0
    def flush(self):
        t = re.sub(r'\s+', ' ', ''.join(self.buf).replace('\xa0', ' ')).strip()
        if t: self.out.append((t, self.rev_par))
        self.buf = []; self.rev_par = False
    def handle_starttag(self, tag, a):
        a = dict(a)
        if not self.ativo:
            if tag == 'div' and 'legislacao-completa' in (a.get('class') or ''): self.ativo = True; self.prof = 1; self.rev_par = False
            return
        if tag == 'div': self.prof += 1
        if tag in ('script', 'style'): self.skip += 1
        if tag == 'span' and 'revogado' in (a.get('class') or ''): self.rev += 1; self.rev_par = True
        elif tag == 'span': self.rev += 0
        if tag == 'tr': self.flush(); self.cells = []
        if tag in ('td', 'th') and self.cells is not None: self.cell = []
        if tag in ('p', 'br') and self.cells is None: self.flush()
        if tag in ('p', 'br') and self.cell is not None: self.cell.append(' ')
    def handle_endtag(self, tag):
        if not self.ativo: return
        if tag in ('script', 'style'): self.skip -= 1
        if tag == 'div':
            self.prof -= 1
            if self.prof == 0: self.flush(); self.ativo = False
        if tag == 'span' and self.rev: self.rev -= 1
        if tag in ('td', 'th') and self.cell is not None:
            self.cells.append(re.sub(r'\s+', ' ', ''.join(self.cell).replace('\xa0', ' ')).strip()); self.cell = None
        if tag == 'tr' and self.cells is not None:
            cs = [c for c in self.cells if c]
            if cs: self.out.append((' | '.join(cs), False))
            self.cells = None
        if tag == 'p' and self.cells is None: self.flush()
    def handle_data(self, d):
        if not self.ativo or self.skip: return
        if self.cell is not None: self.cell.append(d)
        else: self.buf.append(d)

p = P(); p.rev_par = False
p.feed(open(sys.argv[1], encoding='utf-8', errors='replace').read())

ORD = 'PRIMEIRO|SEGUNDO|TERCEIRO|QUARTO|QUINTO'
CAB = re.compile(r'^(LIVRO|Livro|TÍTULO|CAPÍTULO|SEÇÃO|Seção|SUBSEÇÃO|Subseção)\s+([IVXLC]+(?:-[A-Z])?|ÚNIC[OA]|Únic[oa]|' + ORD + r')\b\s*[-–—]?\s*(.*)$')
def cabecalho(t):
    m = CAB.match(t)
    if not m: return [t]
    rot = ('LIVRO' if m.group(1) == 'Livro' else m.group(1)) + ' ' + m.group(2)
    resto = m.group(3).strip()
    if not resto: return [rot]
    # "TÍTULO II - DISPOSIÇÕES GERAIS CAPÍTULO I - DOS POSTULANTES": dois cabeçalhos numa linha
    m2 = re.search(r'\s(CAPÍTULO|SEÇÃO|Seção)\s+([IVXLC]+|ÚNICO)\b', resto)
    if m2: return [rot, resto[:m2.start()].strip()] + cabecalho(resto[m2.start():].strip())
    nota = re.search(r'\s*(\((?:Seção|Capítulo|Título|Redação|Incluíd|Acrescentad|Revogad)[^)]*\))\s*$', resto)
    if nota: return [rot, resto[:nota.start()].strip(), nota.group(1)]
    return [rot, resto]

linhas = []; nota_rev = None
for t, rev in p.out:
    if rev:
        m = re.match(r'^\((Revogad[oa][^)]*)\):?$', t)
        if m: nota_rev = '(' + m.group(1) + ')'; continue
        linhas.append('⟦' + t + '⟧' + (' ' + nota_rev if nota_rev else ''))
        continue
    nota_rev = None
    linhas.extend(cabecalho(t))

# Notas que anunciam o item seguinte ("(Artigo acrescentado pela Lei ...):") vão para o
# fim da linha desse item, como nas notas do Planalto. As demais ficam onde estão.
final = []; pend = []
ANUNCIO = re.compile(r'^⟦?(\([^()]*(?:\([^()]*\)[^()]*)*\)):⟧?(?: \(Revogad[^)]*\))?$')
for l in linhas:
    m = ANUNCIO.match(l)
    if m: pend.append(m.group(1)); continue
    if re.match(r'^Nota Legisweb:', l, re.I): pend.append('(' + l + ')'); continue   # nota editorial sobre o artigo seguinte
    if pend:
        nota = ' '.join(pend)
        if l.startswith('⟦') and '⟧ (' in l: i = l.index('⟧ (') + 1; l = l[:i] + ' ' + nota + l[i:]
        else: l = l + ' ' + nota
        pend = []
    final.append(l)
sys.stdout.write('\n'.join(final) + '\n')
