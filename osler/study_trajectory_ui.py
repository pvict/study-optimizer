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
    a,b,c=st.columns(3)
    a.metric('Feitas em blocos registrados',roadmap['recorded_attempts'])
    b.metric('Recomendadas daqui até a prova',roadmap['recommended_total'])
    c.metric('Encontros recomendados',len(roadmap['steps']))
    st.caption('Cenário mantendo desempenho e intervalo atuais. As datas abaixo são indicativas; as vagas reais ficam no Calendário. Não representam estudo concluído.')
    if roadmap['horizon_end']<profile.exam_date: st.caption('Previsão limitada aos próximos 18 meses, até '+roadmap['horizon_end']+'. O total mostrado cobre esse horizonte, não todo o período até a prova.')
    if roadmap['complement_per_block']:
        st.warning(f"Banco pequeno: {state['total']} questões conhecidas. Para o bloco de referência de {state['recommended_questions']}, faltam {roadmap['complement_per_block']} questões de outra fonte sobre este mesmo tema. Ele não foi substituído por um assunto amplo.")
    st.caption(f"Referência: {state['recommended_questions']} questões por encontro, a cada {state['review_interval_days']} dias. O calendário pode ampliar o bloco para cumprir a meta diária. Total em tentativas, incluindo reutilizações; não são questões distintas.")
    rows=[{'Etapa':s['stage'],'Data indicativa':s['date'],'Questões recomendadas':s['questions'],
           'Acumulado futuro':s['cumulative_questions']} for s in roadmap['steps']]
    if limit: rows=rows[:limit]
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch',height=min(330,36*(len(rows)+1)))
    if limit and len(roadmap['steps'])>limit: st.caption('As revisões continuam até a prova. Veja a trajetória completa em Temas e estatísticas.')
    st.caption(f"PDF: {roadmap['pdf_answered']} respondidas, separado dos blocos datados. O PDF não permite numerar encontros anteriores.")
    return roadmap


def render_trajectories(service,view):
    if not st.toggle('Ver plano de revisões por tema',key='show_trajectories'): return
    profile=AdaptiveProfile(**view['profile'])
    states=view['planning_states']
    if not states:
        st.info('Importe um relatório de questões para reconhecer os temas específicos e preparar suas revisões.')
        return
    with st.container(border=True):
        st.subheader('Do próximo contato até a prova')
        st.caption('Primeiro contato ou diagnóstico, revisões 1, 2, 3… e manutenção contínua. O total muda com seu rendimento, incidência e data da prova.')
        st.caption('Cenário conservador: repetir o intervalo atual até a prova pode gerar um total alto. Ele não é uma obrigação nem uma quantidade necessária comprovada; resultados reais podem ampliar os intervalos e reduzir a previsão.')
        summary=trajectory_summary(states,profile,view['date'],[])
        st.caption(f"{summary['small_bank_topics']} temas têm banco menor que o mínimo por bloco. Continuam na lista com o complemento necessário, sem blocos automáticos de uma questão.")
        fields=['Tema','Por encontro','Demanda até a prova','Encontros recomendados','Feitas em blocos registrados','Complemento por encontro']
        # Uma assinatura invalida previsões quando resultado, perfil, carga ou fonte mudar.
        signature=hashlib.sha256(json.dumps([view['plan'],service.store.days()],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if st.button('Conferir o que cabe na minha rotina',key='check_trajectory_capacity'):
            with st.spinner('Distribuindo as revisões na sua rotina…'):
                st.session_state['trajectory_capacity']={'signature':signature,'summary':service.trajectories(view['date'])}
        cached=st.session_state.get('trajectory_capacity',{})
        if cached.get('signature')==signature:
            summary=cached['summary']
            fields+=['Questões com vaga prevista','Encontros com vaga prevista','Primeira vaga prevista']
            capacity=summary['scheduled_questions']
            demand=summary['recommended_questions']
            if demand>capacity:
                st.warning(f"Demanda individual: {demand:,} questões. Distribuição atual: {capacity:,} questões até {summary['horizon_end']}. As recomendações individuais não cabem integralmente na rotina atual.")
            if summary['unscheduled_topics']: st.warning(f"{summary['unscheduled_topics']} temas ainda estão sem vaga prevista. Priorize pela incidência, acrescente blocos ou redistribua a carga.")
            st.caption('Vaga prevista continua sendo planejamento. Acertos futuros não foram presumidos. A distribuição pode ampliar um bloco e reduzir vagas para outros temas.')
        else: st.caption('A tabela mostra demanda individual, sem reservar datas. Confira a rotina para ver as vagas possíveis dentro da sua meta diária.')
        frame=pd.DataFrame(summary['rows'])
        st.dataframe(frame[fields],hide_index=True,width='stretch',height=280)
        safe=frame.map(lambda v:_safe_cell(v) if isinstance(v,str) else v)
        st.download_button('Baixar recomendações de todos os temas',safe.to_csv(index=False,sep=';').encode('utf-8-sig'),'trajetorias_por_tema.csv','text/csv')
        st.divider()
        st.markdown('**Escolha um tema para abrir as etapas**')
        chosen=pick_topic(states,'trajectory')
        if chosen:
            roadmap=trajectory_detail(chosen,profile,view['date'])
            data=pd.DataFrame(roadmap['steps'])
            st.download_button('Baixar etapas deste tema',data.to_csv(index=False,sep=';').encode('utf-8-sig'),'etapas_do_tema.csv','text/csv')
        with st.expander('Evidências e critérios do cálculo'):
            st.write('Revisões sucessivas combinam recuperação ativa e espaçamento. Ampliamos intervalos após blocos com convicção na meta, em dias espaçados. Erros encurtam o intervalo; a incidência aumenta prioridade, frequência e dose de referência. Domínio mantém revisões de manutenção.')
            st.caption('É uma política inicial adaptada a blocos de tema. Não há dose universal de questões clínicas, curva pessoal calibrada ou garantia de 90%. FSRS exige histórico por item para uma aplicação fiel; não tratamos um tema inteiro como um cartão de memória.')
            st.markdown('[Rawson e Dunlosky, 2011](https://doi.org/10.1037/a0023956) · [Cepeda e colaboradores, 2008](https://doi.org/10.1111/j.1467-9280.2008.02209.x) · [Modelo oficial do FSRS](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm)')
