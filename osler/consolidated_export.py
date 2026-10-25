"""CSV de eventos tipados; nenhuma soma entre fontes ou versões."""
import csv
import json
from io import StringIO
from .exports import _safe_cell
from .study_read_model import read_events


def consolidated_csv(service,as_of):
    fields=['tipo','id','versao','acao','ativo','data','area','tema','modalidade','questoes','acertos','convictas','origem','nome','observacao','registrado_em',
            'tipo_registro','causa','critico','minutos','revisao_de','instituicao','condicoes','ineditas','detalhes_json','cards_criados']
    output=StringIO(newline=''); writer=csv.DictWriter(output,fieldnames=fields,delimiter=';',lineterminator='\n'); writer.writeheader()
    for table,kind,key in [('study_events','sessao','session_id'),('study_errors','erro','error_key'),('mock_exams','simulado','exam_key')]:
        events=read_events(service.repository,table); latest={r[key]:r for r in events}
        for r in events:
            e=r.get('data',r); day=e['day']
            if day>as_of: continue
            path=e.get('path',r.get('path',[]))
            row={'tipo':kind,'id':r[key],'versao':r['version'],'acao':r['action'],
                 'ativo':'sim' if latest[r[key]]['id']==r['id'] and r['action']=='save' else 'nao','data':day,
                 'area':path[0] if path else '', 'tema':' → '.join(path),'modalidade':e.get('mode',''),
                 'questoes':e.get('questions',''),'acertos':e.get('correct',''),'convictas':e.get('confident_correct',''),
                 'origem':e.get('source',''),'nome':e.get('name',''),'observacao':e.get('note',''),'registrado_em':r['created_at']}
            row.update(tipo_registro=e.get('kind',''),causa=e.get('cause',''),critico=e.get('critical',''),minutos=e.get('minutes',e.get('minutes_used','')),
                       revisao_de=e.get('review_of',''),instituicao=e.get('institution',''),condicoes=e.get('conditions',''),ineditas=e.get('unseen_questions',''),
                       detalhes_json=json.dumps({'areas':e.get('areas',[]),'temas':e.get('topics',[])},ensure_ascii=False) if kind=='simulado' else '',
                       cards_criados=e.get('cards_created',0) if kind=='sessao' else '')
            writer.writerow({f:_safe_cell(row.get(f,'')) for f in fields})
    return output.getvalue().encode('utf-8-sig')
