"""Inventário hierárquico local e fila de primeira passagem, sem executar HTML."""
from html.parser import HTMLParser
from datetime import date
import re

from .models import normalize_path, stable_topic_id


class _TreeReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth=0; self.rows=[]; self.row=None; self.capture=None; self.ignore=0

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in {'script','style'}: self.ignore+=1
        if self.ignore: return
        classes=attrs.get('class','').split()
        if tag=='div':
            self.depth+=1
            if any(c.startswith('TreeNode-') for c in classes):
                if self.row: raise ValueError('Há nós incompletos na árvore. Copie o container inteiro.')
                indent=re.search(r'margin-left\s*:\s*(\d+)px',attrs.get('style',''))
                if not indent: raise ValueError('Não foi possível identificar a hierarquia dos temas.')
                self.row={'depth':self.depth,'label':'','number':'','indent':int(indent[1]),'branch':False}
        if self.row:
            if any('chevron-' in c for c in classes): self.row['branch']=True
            if any(c.startswith('Label-') for c in classes): self.capture='label'
            if any(c.startswith('StatInfo-') for c in classes): self.capture='number'

    def handle_data(self,data):
        if self.row and self.capture and not self.ignore: self.row[self.capture]+=data

    def handle_endtag(self,tag):
        if tag in {'script','style'}: self.ignore=max(0,self.ignore-1); return
        if self.ignore: return
        if tag in {'span','p'}: self.capture=None
        if tag=='div':
            if self.row and self.depth==self.row['depth']: self.rows.append(self.row); self.row=None
            self.depth-=1
            if self.depth<0: raise ValueError('HTML cortado ou com fechamento inválido.')


def parse_error_cards(text):
    if not isinstance(text,str) or len(text.encode('utf-8'))>20*1024*1024: raise ValueError('Use um HTML de até20 MB.')
    parser=_TreeReader(); parser.feed(text); parser.close()
    if parser.depth or parser.row or not parser.rows: raise ValueError('Não encontrei uma árvore completa. Copie o container inteiro.')
    if len(parser.rows)>10000: raise ValueError('A árvore excede10000 nós.')
    stack=[]; nodes=[]; seen=set()
    for i,row in enumerate(parser.rows):
        label=' '.join(row['label'].split()); number=row['number'].strip()
        if not label or len(label)>300 or not re.fullmatch(r'\d+|\d{1,3}(?:\.\d{3})+',number): raise ValueError('Tema ou quantidade de cards inválidos no HTML.')
        while stack and stack[-1]['indent']>=row['indent']: stack.pop()
        if not stack and row['indent']!=0: raise ValueError('Falta um tema pai no início ou no meio da árvore.')
        if stack and (not stack[-1]['branch'] or row['indent']!=stack[-1]['indent']+20): raise ValueError('Hierarquia incompleta: expanda os pais antes de copiar.')
        path=[n['label'] for n in stack]+[label]; key=tuple(path)
        if key in seen: raise ValueError('Tema repetido na mesma hierarquia. Nenhuma linha foi importada.')
        seen.add(key)
        has_children=i+1<len(parser.rows) and parser.rows[i+1]['indent']>row['indent']
        node={'topic_id':stable_topic_id(path),'path':path,'label':label,'count':int(number.replace('.','')),
              'indent':row['indent'],'branch':row['branch'],'has_children':has_children,'specific':not row['branch'] and not has_children}
        nodes.append(node); stack.append(node)
    unresolved=[]
    for node in nodes:
        if not node['branch']: continue
        children=[n for n in nodes if len(n['path'])==len(node['path'])+1 and n['path'][:-1]==node['path']]
        residue=node['count']-sum(n['count'] for n in children)
        if residue<0: raise ValueError('A soma dos filhos ultrapassa o pai. Refaça a exportação completa.')
        if residue: unresolved.append({'path':node['path'],'count':residue,'reason':'Grupo recolhido' if not children else 'Cards sem subtema identificado'})
    merged={}
    for n in nodes:
        if not n['specific']:continue
        if n['topic_id'] not in merged:merged[n['topic_id']]={**n,'source_paths':[n['path']]}
        else:
            merged[n['topic_id']]['count']+=n['count'];merged[n['topic_id']]['source_paths'].append(n['path'])
    topics=list(merged.values())
    total=sum(n['count'] for n in nodes if len(n['path'])==1)
    schedulable=sum(n['count'] for n in topics)
    if total!=schedulable+sum(n['count'] for n in unresolved): raise ValueError('Os subtotais da árvore não conferem.')
    return {'nodes':nodes,'topics':topics,'unresolved':unresolved,'total':total,'schedulable':schedulable,'unallocated':total-schedulable}


def plan_error_cards(topics,progress,states,day,budget,question_ids=(),snapshot_day=None,reference_budget=None,completed_today=None):
    """Política de triagem explícita; não estima retenção ou probabilidade de aprovação."""
    if type(budget) is not int or not 0<=budget<=2000: raise ValueError('A carga deve estar entre0 e2000 cards.')
    reference_budget=budget if reference_budget is None else reference_budget
    if type(reference_budget) is not int or not 0<=reference_budget<=2000: raise ValueError('Referência diária inválida.')
    completed_today=max(0,reference_budget-budget) if completed_today is None else completed_today
    if type(completed_today) is not int or completed_today<0:raise ValueError('Quantidade realizada inválida.')
    asof=date.fromisoformat(day); state_by_path={tuple(normalize_path(s['path'])):s for s in states if s.get('path')}
    state_by_id={s['topic_id']:s for s in states}; ranked=[]
    for t in topics:
        p=progress.get(t['topic_id'],{}); remaining=max(0,t['count']-p.get('covered',0))
        if not remaining: continue
        state=state_by_path.get(tuple(normalize_path(t['path'])),state_by_id.get(t['topic_id'],{}))
        performance=state.get('performance',{}); n=performance.get('exact_n',0); correct=performance.get('exact_correct',0)
        accuracy=(correct+1)/(n+2) if n else None
        known=bool(state.get('incidence_known')); incidence=max(0,min(1,state.get('incidence_strength',0))) if known else .5
        last=p.get('last_day') or snapshot_day or day; age=max(0,(asof-date.fromisoformat(last)).days)
        score=(.5+.5*incidence)*(1+(1-accuracy if accuracy is not None else .5))*(1+min(age,28)/28)
        sync=t['topic_id'] in question_ids
        if sync: score*=1.15
        reasons=[]
        if known and incidence>=.75:reasons.append('Incidência alta nas suas instituições')
        if n and correct/n<.6:reasons.append('Erros frequentes nas questões')
        if sync:reasons.append('Combina com as questões de hoje')
        if age>=7:reasons.append(f'{age} dias sem registro de cards neste lote')
        ranked.append({**t,'remaining':remaining,'accuracy':accuracy,'sample':n,'incidence_known':known,'score':score,
                       'priority':'Alta' if known and incidence>=.75 or n>=10 and correct/n<.6 else 'Regular',
                       'in_progress_today':p.get('last_day')==day and p.get('covered',0)>0,
                       'oversized':remaining>reference_budget+reference_budget//10,
                       'reason':' · '.join(reasons) or 'Avançar na primeira passagem pelo lote','planned':0})
    ranked.sort(key=lambda t:(not t['in_progress_today'],-t['score'],-t['remaining'],tuple(normalize_path(t['path']))))
    total=0; ceiling=max(0,budget+reference_budget//10-max(0,completed_today-reference_budget))
    for t in ranked:
        if (total<budget or t['in_progress_today']) and total+t['remaining']<=ceiling:
            t['planned']=t['remaining'];total+=t['planned']
        t['blocks']=[t['planned']] if t['planned'] else []
    return ranked
