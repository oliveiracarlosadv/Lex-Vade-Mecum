import json,sys,re
d=json.load(open(sys.argv[1],encoding='utf-8')); out=sys.argv[2]; maxlv=int(sys.argv[3]) if len(sys.argv)>3 else 5
def fmt(n):
    b=int(re.match(r'\d+',n).group()); s=n if '-' in n else (n+'º' if b<=9 else n)
    return re.sub(r'^(\d)(\d{3})', r'\1.\2', s)
nodes=[]; stack=[]
for x in d['structure']:
    if x['level']<9:
        node={'level':x['level'],'label':x['label'],'name':x['name'],'arts':[]}
        while stack and stack[-1]['level']>=x['level']: stack.pop()
        stack.append(node); nodes.append(node)
    else:
        for n in stack: n['arts'].append(x['art'])
names={0:'Parte',1:'Livro',2:'Título',3:'Capítulo',4:'Seção',5:'Subseção'}
L=['| Nível | Divisão | Denominação | Artigos |','| --- | --- | --- | --- |']
for n in nodes:
    if n['level']>maxlv: continue
    lab=n['label'].split(); w2=' '.join(lab[1:]); w2=w2 if re.fullmatch(r'[IVXLC]+(-[A-Z])?',w2) else w2.capitalize(); lab=lab[0].capitalize()+' '+w2
    ind='&nbsp;&nbsp;'*n['level']
    rng=f"{fmt(n['arts'][0])} a {fmt(n['arts'][-1])}" if len(n['arts'])>1 else (fmt(n['arts'][0]) if n['arts'] else '—')
    kind='Livro' if 'COMPLEMENTAR' in n['label'] else names[n['level']]
    L.append(f"| {kind} | {ind}{lab} | {n['name'] or '—'} | {rng} |")
from collections import Counter
c=Counter(n['level'] for n in nodes)
plural={0:'partes',1:'livros',2:'títulos',3:'capítulos',4:'seções',5:'subseções'}
comp=sum(1 for n in nodes if 'COMPLEMENTAR' in n['label'])
c[0]-=comp; c[1]+=comp
L+=['',"Totais: "+', '.join(f"{c[k]} {plural[k]}" for k in sorted(c))+(" (incluído o Livro Complementar)" if comp else "")+f"; {len(d['units'])} artigos (incluídos os acrescidos por letras, revogados e vetados)."]
open(out,'w',encoding='utf-8').write('\n'.join(L)+'\n')
