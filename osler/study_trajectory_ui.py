"""Trajetória individual e capacidade: referências futuras ficam separadas do progresso."""
import hashlib
import json
import pandas as pd
import streamlit as st

from .exports import _safe_cell
from .study_models import AdaptiveProfile
from .topic_picker_ui import pick_topic
from .topic_trajectory import topic_trajectory, trajectory_summary


def trajectory_detail(state,profile,start,limit=None):
    roadmap=topic_trajectory(state,profile,start)
    reference=state.get('theme_recommended_questions',state['recommended_questions'])
    a,b=st.columns(2)
    a.metric('Referência do próximo bloco',reference)
    b.metric('Feitas em blocos registrados',roadmap['recorded_attempts'])
    st.write(state.get('dose_reason','A quantidade será ajustada após seu próximo resultado.'))
    st.caption('Após registrar o resultado, recalculamos a quantidade e o intervalo. As revisões seguintes ficam a definir; as vagas previstas estão no Calendário.')
    if state.get('review_kind')=='lot_only': st.caption('O retorno do lote de erros tem sua própria data e quantidade. A tabela abaixo é da revisão completa do tema.')
    if roadmap['complement_per_block']:
        st.warning(f"Banco pequeno: {state['total']} questões conhecidas. Para o bloco de referência de {reference}, faltam {roadmap['complement_per_block']} questões de outra fonte sobre este mesmo tema. Ele não foi substituído por um assunto amplo.")
    if state.get('questions',reference)>reference:
        st.caption('O bloco deste dia foi ampliado pela divisão de carga ou por uma inclusão na agenda. A referência acima é a necessidade atual do tema.')
    rows=trajectory_rows(roadmap)
    if limit: rows=rows[:limit]
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch',height=min(330,36*(len(rows)+1)))
    if not rows: st.info('Não há próximo contato indicado dentro do período de preparação.')
    st.caption('Esta sequência não fixa o número de revisões necessário. A manutenção continua conforme seus resultados, até o fim da preparação. Questões contam tentativas, incluindo repetições.')
    st.caption(f"PDF: {roadmap['pdf_answered']} respondidas, separado dos blocos datados. O PDF não permite numerar encontros anteriores.")
    return roadmap


def trajectory_rows(roadmap):
    return [{'Etapa':s['stage'],'Data indicativa':s['date'] or 'Após o resultado anterior',
             'Questões':str(s['questions']) if s['questions'] is not None else 'A recalcular'} for s in roadmap['steps']]


def render_trajectories(service,view):
    if not st.toggle('Ver plano de revisões por tema',key='show_trajectories'): return
    profile=AdaptiveProfile(**view['profile'])
    states=view['planning_states']
    if not states:
        st.info('Importe um relatório de questões para reconhecer os temas específicos e preparar suas revisões.')
        return
    with st.container(border=True):
        st.subheader('Próximos blocos e revisões')
        st.caption('A recomendação vale para o próximo bloco. Resultados com convicção em dias espaçados permitem manutenção menor; erros ou longo tempo sem medição pedem nova avaliação.')
        summary=trajectory_summary(states,profile,view['date'],[])
        st.caption(f"{summary['small_bank_topics']} temas têm banco menor que o mínimo por bloco. Continuam na lista com o complemento necessário, sem blocos automáticos de uma questão.")
        fields=['Tema','Próximo bloco','Critério','Feitas em blocos registrados','Complemento por encontro']
        # Uma assinatura invalida previsões quando resultado, perfil, carga ou fonte mudar.
        signature=hashlib.sha256(json.dumps([view['date'],view['profile'],states,view.get('agenda'),service.store.days()],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if st.button('Conferir o que cabe na minha rotina',key='check_trajectory_capacity'):
            with st.spinner('Distribuindo as revisões na sua rotina…'):
                st.session_state['trajectory_capacity']={'signature':signature,'summary':service.trajectories(view['date'])}
        cached=st.session_state.get('trajectory_capacity',{})
        if cached.get('signature')==signature:
            summary=cached['summary']
            fields+=['Questões com vaga prevista','Encontros com vaga prevista','Primeira vaga prevista']
            capacity=summary['scheduled_questions']
            st.caption(f"Cenário de capacidade: {capacity:,} tentativas com vaga prevista até {summary['horizon_end']}, mantendo as doses e os intervalos atuais. Não é uma quantidade necessária comprovada; será atualizado com seus resultados.")
            if summary['unscheduled_topics']: st.warning(f"{summary['unscheduled_topics']} temas ainda estão sem vaga prevista. Priorize pela incidência, acrescente blocos ou redistribua a carga.")
            st.caption('Vaga prevista continua sendo planejamento. Acertos futuros não foram presumidos. A distribuição pode ampliar um bloco e reduzir vagas para outros temas.')
        else: st.caption('A tabela não reserva datas. Confira a rotina para ver as vagas possíveis dentro da sua meta diária.')
        frame=pd.DataFrame(summary['rows'])
        st.dataframe(frame[fields],hide_index=True,width='stretch',height=280)
        safe=frame.map(lambda v:_safe_cell(v) if isinstance(v,str) else v)
        st.download_button('Baixar próximos blocos de todos os temas',safe.to_csv(index=False,sep=';').encode('utf-8-sig'),'trajetorias_por_tema.csv','text/csv')
        st.divider()
        st.markdown('**Escolha um tema para abrir as etapas**')
        chosen=pick_topic(states,'trajectory')
        if chosen:
            roadmap=trajectory_detail(chosen,profile,view['date'])
            data=pd.DataFrame(trajectory_rows(roadmap))
            st.download_button('Baixar etapas deste tema',data.to_csv(index=False,sep=';').encode('utf-8-sig'),'etapas_do_tema.csv','text/csv')
        with st.expander('Evidências e critérios do cálculo'):
            st.write('Revisões combinam recuperação ativa, feedback e espaçamento. Dois encontros suficientes, com convicção na meta e separados por pelo menos três dias, permitem testar um bloco menor de manutenção. Erros ou ausência prolongada de uma medição suficiente voltam a pedir reforço. A incidência orienta a distribuição do esforço.')
            st.caption('Os limites e quantidades são regras ajustáveis do aplicativo, não doses validadas pelos estudos. Convicção em questões repetidas não comprova desempenho em questões novas. Não há curva pessoal calibrada nem garantia de 90%. FSRS requer histórico por item; um tema inteiro não é um cartão de memória.')
            st.markdown('[Rawson e Dunlosky, 2011](https://doi.org/10.1037/a0023956) · [Cepeda e colaboradores, 2008](https://doi.org/10.1111/j.1467-9280.2008.02209.x) · [Modelo oficial do FSRS](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm)')
