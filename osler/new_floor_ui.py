"""Aviso numérico e ajustes simulados, sem alterar a rotina ao consultar."""
import streamlit as st


def render_new_floor_notice(service,view):
    info=view['plan'].get('capacity',{}).get('new_floor',{})
    if not info.get('missing'):return
    with st.expander(f"Faltam {info['missing']} questões para o mínimo em temas novos",key='new_floor_details',on_change='rerun') as details:
        if not details.open:return
        st.write(f"Mínimo de hoje: **{info['required']}** · Já feitas: **{info['done']}** · No plano: **{info['planned']}** · Faltam incluir: **{info['missing']}**.")
        st.caption('Contagem dos blocos em temas novos do app. As questões em temas já estudados seguem na parte de revisões.')
        with st.spinner('Calculando ajustes dentro da mesma carga…'):
            diagnostic=service.overview(view['date'],diagnose_new_floor=True)
        if diagnostic['planning_token']!=view['planning_token']:
            st.info('O plano mudou durante o cálculo. Atualize Hoje para conferir os novos valores.')
            return
        result=diagnostic['plan']['capacity']['new_floor']
        profile=diagnostic['profile']
        options=result.get('options',[])
        if options:
            st.markdown('**Para incluir o mínimo sem aumentar a meta de questões**')
            for i,option in enumerate(options,1):
                changes=[]
                if option['max_topics']!=profile['max_topics']:
                    changes.append(f"Máximo de temas por dia: **{profile['max_topics']} → {option['max_topics']}**")
                if abs(option['control_new_share']-profile['new_share'])>1e-9:
                    changes.append(f"Questões em temas novos: **{profile['new_share']:.0%} → {option['control_new_share']:.0%}**")
                st.write((f'Opção {i} · ' if len(options)>1 else '')+'; '.join(changes)+'.')
                st.caption(f"Simulação: {option['planned_new']} questões em temas novos no plano. Compromissos já reservados preservados.")
            st.write('Use esses valores em **Ajustar meu dia**. Os ajustes ainda não foram salvos.')
        elif result.get('reason')=='no_candidates':
            st.info('Não há tema novo elegível para hoje nos dados atuais. Confira o acervo e as datas dos temas antes de aumentar os limites.')
        else:
            st.warning('Aumentar apenas o máximo de temas e a proporção de novos não resolveu o encaixe dentro da carga atual.')
            st.write(f"Os blocos já reservados ocupam **{result.get('protected_questions',0)} questões** em **{result.get('protected_topics',0)} temas**. Após essas reservas, há **{result.get('remaining_questions',0)} questões** para a distribuição automática.")
            st.caption('Reagende parte dos compromissos para liberar espaço. A simulação mantém as datas reservadas e não aumenta sua meta automaticamente.')
        override=diagnostic['plan'].get('routine_override',{})
        if override.get('recovery_reserved') or override.get('area_reserved'):
            st.caption(f"O orçamento dos blocos já desconta {override.get('recovery_reserved',0)} revisões externas e {override.get('area_reserved',0)} questões de treino por área.")
