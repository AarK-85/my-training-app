import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Final Precision Lab", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 3. 사이드바 (조회 및 입력)
with st.sidebar:
    st.header("🔍 데이터 관리")
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist())
        selected_session = st.selectbox("조회할 회차 선택", sessions, index=len(sessions)-1)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else:
        selected_session = 1
        s_data = None

    st.divider()
    with st.form(key="recovery_form"):
        st.subheader(f"📝 {selected_session}회차 기록 수정")
        
        # 파워 설정
        w_p = st.number_input("웜업W", value=int(s_data['웜업파워']) if s_data is not None else 97)
        main_p = st.number_input("본훈련W", value=int(s_data['본훈련파워']) if s_data is not None else 135)
        c_p = st.number_input("쿨다운W", value=int(s_data['쿨다운파워']) if s_data is not None else 90) # 17회차 쿨다운 90W 반영
        
        # 가변 본 훈련 시간 (17회차는 90분)
        duration = st.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 90, step=5)
        
        # --- 심박수 입력칸 (데이터 유실 방지 로직) ---
        num_main_steps = duration // 5
        total_steps = 2 + num_main_steps + 1 # 웜업2 + 본훈련N + 쿨다운1
        
        existing_hrs = [x.strip() for x in str(s_data['전체심박데이터']).split(",")] if s_data is not None else []
        
        st.subheader(f"💓 심박 데이터 (총 {total_steps}개)")
        hr_inputs = []
        cols = st.columns(3)
        for i in range(total_steps):
            t = i * 5
            # 기존 데이터가 있으면 로드, 없으면 130 기본값
            default_val = float(existing_hrs[i]) if i < len(existing_hrs) else 130.0
            with cols[i % 3]:
                hr_val = st.number_input(f"{t}분 시점", value=default_val, key=f"hr_input_{i}")
                hr_inputs.append(str(hr_val))
        
        if st.form_submit_button("기록 업데이트"):
            full_hr_str = ", ".join(hr_inputs)
            # 디커플링 및 저장 로직 (생략)
            st.rerun()

# 4. 메인 분석 대시보드
if not df.empty and s_data is not None:
    st.title(f"📊 Session {selected_session} 시퀀스 정밀 분석")
    
    hr_array = [float(x.strip()) for x in str(s_data['전체심박데이터']).split(",")]
    time_array = [i*5 for i in range(len(hr_array))]
    wp, mp, cp = s_data['웜업파워'], s_data['본훈련파워'], s_data['쿨다운파워']
    
    # --- 가변적 파워 스텝 로직 (105분 심박수 반영) ---
    # 17회차 기준: 0~5분(WU), 10~95분(Main), 100~105분(CD)
    # 100분 지점에서 수직 낙하하려면 100분 데이터부터 cp로 설정되어야 함
    power_array = []
    num_main_end_idx = 2 + (s_data['본훈련시간'] // 5) # 본훈련이 끝나는 인덱스 (100분 지점)
    
    for i in range(len(time_array)):
        if i < 2: # 0, 5분
            power_array.append(wp)
        elif i < num_main_end_idx: # 10분 ~ 본훈련 종료 직전까지
            power_array.append(mp)
        else: # 본훈련 종료 시점(수직 낙하 시작)부터 마지막(105분)까지
            power_array.append(cp)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. 파워 스텝 그래프
    fig.add_trace(go.Scatter(
        x=time_array, y=power_array, name="Target Power (W)",
        line=dict(color='rgba(0, 223, 216, 1.0)', width=3, shape='hv'),
        fill='tozeroy', fillcolor='rgba(0, 223, 216, 0.1)'
    ), secondary_y=False)
    
    # 2. 심박수 그래프 (105분 데이터 포함)
    fig.add_trace(go.Scatter(
        x=time_array, y=hr_array, name="Heart Rate (BPM)",
        line=dict(color='#ff4b4b', width=4, shape='spline')
    ), secondary_y=True)

    # 배경 구간 가이드
    m_end_time = s_data['본훈련시간'] + 10 # 웜업 10분 포함
    fig.add_vrect(x0=0, x1=10, fillcolor="gray", opacity=0.1, annotation_text="WU")
    fig.add_vrect(x0=10, x1=m_end_time, fillcolor="blue", opacity=0.05, annotation_text="Main")
    fig.add_vrect(x0=m_end_time, x1=time_array[-1], fillcolor="gray", opacity=0.1, annotation_text="CD")

    fig.update_layout(template="plotly_dark", height=600, hovermode="x unified")
    fig.update_yaxes(range=[0, 200], secondary_y=False)
    fig.update_yaxes(range=[min(hr_array)-10, max(hr_array)+10], secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"💡 105분 시점 최종 심박수: **{hr_array[-1]} BPM** / 디커플링: **{s_data['디커플링(%)']}%**")
