import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Analytics Pro", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 열 이름 변수화 (사용자 시트와 일치)
power_col, dec_col, session_col, phase_col = "평균 파워(W)", "디커플링(%)", "회차", "Phase"

# 3. 사이드바: 정밀 데이터 입력창
with st.sidebar:
    st.header("📝 정밀 훈련 데이터 입력")
    with st.form(key="precision_input_form", clear_on_submit=True):
        date = st.date_input("날짜")
        last_s = int(df[session_col].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_s + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        
        st.divider()
        st.subheader("⏱️ 본 훈련 세션 데이터")
        main_duration = st.number_input("본 훈련 시간(분)", value=60, step=5)
        avg_p = st.number_input("본 훈련 평균 파워(W)", value=135)
        
        # 5분 단위 심박수 입력 (Expander로 정리)
        with st.expander("💓 5분 단위 심박수 입력"):
            hr_values = []
            num_steps = main_duration // 5
            for i in range(num_steps + 1):
                hr = st.number_input(f"{i*5}분 시점 심박수", value=130, key=f"hr_{i}")
                hr_values.append(hr)
        
        user_dec = st.number_input("수동 계산 디커플링(%)", value=0.0, step=0.1, help="본인이 계산한 값을 입력해 검증하세요.")
        rpe = st.select_slider("피로도", options=list(range(1, 11)), value=5)
        notes = st.text_area("메모")

        if st.form_submit_button("기록 저장 및 자동 분석"):
            # --- 자동 디커플링 계산 로직 ---
            # 전반부/후반부 데이터 분할
            mid_idx = len(hr_values) // 2
            first_half_hr = np.mean(hr_values[:mid_idx])
            second_half_hr = np.mean(hr_values[mid_idx:])
            
            # EF(Efficiency Factor) 계산 = Power / HR
            first_ef = avg_p / first_half_hr
            second_ef = avg_p / second_half_hr
            
            # 디커플링 계산: ((전반EF - 후반EF) / 전반EF) * 100
            # 심박이 오르면 EF가 낮아지므로 (First - Second) / First 양수값이 드리프트 수치임
            auto_dec = round(((first_ef - second_ef) / first_ef) * 100, 2)
            
            new_row = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"), "회차": session, "Phase": phase,
                "훈련 시간(분)": main_duration, "
