import json,re,sys
units=json.load(open(sys.argv[1],encoding='utf-8'))['units']; md=open(sys.argv[2],encoding='utf-8').read()
body=md.split('\n## Texto Estruturado\n',1)[1]
blocks=re.split(r'\n### ',body)
def unesc(l): return re.sub(r'^\\','',l).replace('\\.','.',1).replace('\\)',')',1).replace('&lt;','<')
ok=0;bad=[]
for u,b in zip(units,blocks[1:] if not blocks[0].startswith('### ') else blocks):
    lines=[x for x in b.split('\n#### Interpretação')[0].split('\n')[1:] if x and not x.startswith('**Localização') and not x.startswith('> **Alterações')]
    lines=[unesc(x) if (x.startswith('\\') or re.match(r'^\d+\\[.)]',x) or '&lt;' in x) else x for x in lines]
    if lines==u['lines']: ok+=1
    else: bad.append(u['num'])
heads=['## Metadados','## Resumo Executivo','## Objeto da Lei','## Contexto Jurídico','## Principais Conceitos','## Estrutura da Lei','## Texto Estruturado','## Direitos Garantidos','## Obrigações','## Proibições','## Penalidades','## Competências e Responsabilidades','## Prazos Relevantes','## Relação com Outras Normas','## Glossário Jurídico','## Perguntas e Respostas','## Palavras-chave para Busca','## Referências','## Metadados RAG']
pos=[md.find('\n'+h+'\n') for h in heads]
print('artigos idênticos ao texto oficial:',ok,'/',len(units),'| divergentes:',bad[:20])
print('seções presentes e em ordem:', all(p>0 for p in pos) and pos==sorted(pos), [h for h,p in zip(heads,pos) if p<0])
for sec in ['#### Interpretação','#### Pontos Importantes','#### Palavras-chave','#### Remissões de Lei']:
    print(sec, md.count('\n'+sec+'\n'))
print('interpretações vazias:', len(re.findall(r'#### Interpretação\n\n\n',md)))
