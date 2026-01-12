import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection  # 구글 시트 연결용

st.set_page_config(page_title="Zone 2 Analytics", layout="wide")

st.title("🚴 Zone 2 Performance Dashboard")

# 1. 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# 2. 사이드바 입력창
with st.sidebar:
    st.header("📝 훈련 기록 입력")
    # 마지막 회차 자동 계산
    last_session = int(df["회차"].max()) if not df.empty else 0
    
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("날짜")
        session = st.number_input("회차", value=last_session + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        power = st.slider("평균 파워(W)", 100, 200, 135)
        decoupling = st.number_input("디커플링(%)", value=5.0, step=0.1)
        submit = st.form_submit_button("기록 저장")

        if submit:
            new_row = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"),
                "회차": session, "Phase": phase,
                "평균파워": power, "디커플링": decoupling
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            st.success("데이터가 구글 시트에 저장되었습니다!")

# 3. 데이터 시각화
if not df.empty:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("최고 파워", f"{df['평균파워'].max()} W")
    with col2:
        st.metric("최저 디커플링", f"{df['디커플링'].min()} %")

    # 파워 추세선에 목표선(160W) 추가
    fig = px.line(df, x="회차", y="평균파워", title="파워 성장 추이", markers=True, template="plotly_dark")
    fig.add_hline(y=160, line_dash="dash", line_color="red", annotation_text="최종 목표 160W")
    st.plotly_chart(fig, use_container_width=True)
