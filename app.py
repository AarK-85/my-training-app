import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 페이지 기본 설정
st.set_page_config(page_title="Zone 2 Performance Tracker", layout="wide")

# 1. 구글 시트 연결 (데이터베이스)
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 실시간 불러오기 (캐시 없음)
df = conn.read(ttl=0)

# 메인 타이틀
st.title("🚴 Performance Analytics Dashboard")
st.info("🎯 최종 목표: 2026년 3월까지 **160W (Zone 2)** 달성")

# 2. 사이드바: 데이터 입력창 (모바일 접속 시 입력 편리)
with st.sidebar:
    st.header("📝 오늘의 훈련 기록")
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("훈련 날짜")
        # 마지막 회차 자동 인식 및 +1 계산
        last_session = int(df["회차"].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_session + 1)
        
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        power = st.slider("평균 파워 (W)", 100, 200, 135)
        hr = st.slider("평균 심박 (bpm)", 100, 180, 130)
        decoupling = st.number_input("디커플링 (%)", value=5.0, step=0.1)
        rpe = st.select_slider("주관적 피로도", options=list(range(1, 11)), value=5)
        notes = st.text_area("메모")
        
        submit = st.form_submit_button("데이터 저장하기")
        
        if submit:
            new_data = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"),
                "회차": session,
                "Phase": phase,
                "평균파워": power,
                "평균심박": hr,
                "디커플링": decoupling,
                "피로도": rpe,
                "메모": notes
            }])
            # 기존 데이터에 추가 후 구글 시트 업데이트
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"{session}회차 기록 완료!")
            st.rerun()

# 3. 메인 분석 화면 구성
if not df.empty:
    # 상단 요약 지표 (Scorecards)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("최근 파워", f"{df['평균파워'].iloc[-1]} W")
    with c2:
        st.metric("최저 디커플링", f"{df['디커플링'].min()} %")
    with c3:
        st.metric("누적 훈련", f"{len(df)} 회")
    with c4:
        gap = 160 - df['평균파워'].max()
        st.metric("목표까지", f"{gap} W")

    st.markdown("---")

    # 차트 1: 파워 성장 추세 및 160W 목표선
    fig_power = go.Figure()
    fig_power.add_trace(go.Scatter(x=df['회차'], y=df['평균파워'], name="평균 파워", line=dict(color='#00CC96', width=3)))
    fig_power.add_hline(y=160, line_dash="dash", line_color="red", annotation_text="최종 목표 160W")
    fig_power.update_layout(title="회차별 파워 성장 추이", template="plotly_dark")
    st.plotly_chart(fig_power, use_container_width=True)

    # 차트 2: 디커플링 효율 변화
    fig_dec = px.area(df, x="회차", y="디커플링", title="디커플링(%) 추세 (낮을수록 효율적)", template="plotly_dark")
    fig_dec.add_hline(y=5.0, line_dash="dot", line_color="yellow", annotation_text="안정화 기준 5%")
    st.plotly_chart(fig_dec, use_container_width=True)

    # 데이터 테이블 시각화
    with st.expander("전체 로그 보기"):
        st.dataframe(df.sort_values(by="회차", ascending=False), use_container_width=True)
else:
    st.warning("데이터가 없습니다. 왼쪽 사이드바에서 기록을 시작하세요!")
