import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="Zone 2 Performance Tracker", layout="wide")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

st.title("📊 Zone 2 Performance Analytics")

# 2. 사이드바 - 데이터 입력 (에러 수정 지점)
with st.sidebar:
    st.header("➕ 새로운 기록 추가")
    
    # 폼(Form) 시작
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("훈련 날짜")
        last_session = int(df["회차"].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_session + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        power = st.slider("평균 파워 (W)", 100, 200, 135)
        decoupling = st.number_input("디커플링 (%)", value=5.0, step=0.1)
        hr = st.slider("평균 심박 (bpm)", 100, 180, 130)
        rpe = st.select_slider("피로도", options=list(range(1, 11)), value=5)
        notes = st.text_area("메모")
        
        # ✅ 반드시 form 블록 안에 이 버튼이 있어야 에러가 나지 않습니다.
        submit = st.form_submit_button("기록 저장하기")
        
        if submit:
            new_data = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"),
                "회차": session, 
                "Phase": phase, 
                "훈련시간": 60, # 기본값 60분 설정
                "평균파워": power, 
                "평균심박": hr, 
                "EF": round(power/hr, 2) if hr > 0 else 0,
                "디커플링": decoupling, 
                "피로도": rpe, 
                "메모": notes
            }])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            st.success("데이터가 구글 시트에 저장되었습니다!")
            st.rerun()

# 3. 메인 대시보드 출력부 (기존과 동일)
if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("최근 파워", f"{df['평균파워'].iloc[-1]} W")
    c2.metric("최저 디커플링", f"{df['디커플링'].min()}%")
    c3.metric("진행 회차", f"{len(df)}회")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['회차'], y=df['평균파워'], name="평균 파워", line=dict(color='#00CC96', width=3)))
    fig.add_hline(y=160, line_dash="dash", line_color="red", annotation_text="최종 목표 160W")
    fig.update_layout(title="회차별 파워 성장 추이", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("왼쪽 사이드바에서 첫 데이터를 입력해 주세요.")
