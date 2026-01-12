import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Adaptive Step-Power Lab", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 3. 사이드바: 조회 및 가변 입력창
with st.sidebar:
    st.header("🔍 데이터 관리")
    
    # 회차 선택 및 데이터 로드
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist())
        selected_session = st.selectbox("조회할 회차 선택", sessions, index=len(sessions)-1)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else:
        selected_session = 1
        s_data = None

    st.divider()

    # 입력 폼
    with st.form(key="adaptive_form", clear_on_submit=False):
        st.subheader(f"📝 {selected_session}회차 기록/수정")
        
        date = st.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now())
        session_num = st.number_input("회차 번호", value=int(selected_session))
        
        # 파워 설정
        col1, col2, col3 = st.columns(3)
        w_p = col1.number_input("웜업W", value=int(s_data['웜업파워']) if s_data is not None else 97)
        main_p = col2.number_input("본훈련W", value=int(s_data['본훈련파워']) if s_data is not None else 135)
        c_p = col3.number_input("쿨다운W", value=int(s_data['쿨다운파워']) if s_data is not None else 107)
        
        # 가변 시간 설정 (슬라이더로 조절 시 입력칸 개수 즉시 반영)
        duration = st.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 60, step=5)
        
        # --- [복구된 5분 단위 심박수 입력칸] ---
        st.subheader("💓 심박수 입력 (5분 간격)")
        # 웜업(10분=2칸) + 본훈련(duration/5) + 쿨다운(5분=1칸)
        num_main_steps = duration // 5
        total_steps = 2 + num_main_steps + 1
        
        # 기존 시트 데이터가 있으면 미리 채워넣기 위한 파싱
        existing_hrs = []
        if s_data is not None:
            existing_hrs = [x.strip() for x in str(s_data['전체심박데이터']).split(",")]
        
        hr_inputs = []
        # 3열로 깔끔하게 배치
        cols = st.columns(3)
        for i in range(total_steps):
            label = ""
            if i < 2: label = f"WU {i*5}분"
            elif i < 2 + num_main_steps: label = f"본 {i*5}분"
            else: label = f"CD {i*5}분"
            
            # 기존 값이 있으면 넣고, 없으면 130 기본값
            default_val = float(existing_hrs[i]) if i < len(existing_hrs) else 130.0
            with cols[i % 3]:
                hr_val = st.number_input(label, value=default_val, key=f"hr_step_{i}")
                hr_inputs.append(str(hr_val))
        
        if st.form_submit_button("데이터 저장/업데이트"):
            # 디커플링 계산 (본 훈련 구간만 슬라이싱)
            main_hr_only = [float(x) for x in hr_inputs[2:-1]]
            mid = len(main_hr_only) // 2
            f_ef = main_p / np.mean(main_hr_only[:mid])
            s_ef = main_p / np.mean(main_hr_only[mid:])
            dec = round(((f_ef - s_ef) / f_ef) * 100, 2)
            
            full_hr_str = ", ".join(hr_inputs)
            
            new_row = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"), "회차": session_num, 
                "웜업파워": w_p, "본훈련파워": main_p, "쿨다운파워": c_p,
                "본훈련시간": duration, "디커플링(%)": dec, "전체심박데이터": full_hr_str
            }])
            
            # 기존 회차 있으면 업데이트, 없으면 추가
            if not df.empty and session_num in df["회차"].values:
                df = df[df["회차"] != session_num]
            updated_df = pd.concat([df, new_row], ignore_index=True).sort_values("회차")
            conn.update(data=updated_df)
            st.success(f"{session_num}회차 저장 완료!")
            st.rerun()

# 4. 메인 대시보드
if not df.empty and s_data is not None:
    st.title(f"📊 Session {selected_session} 분석")
    
    hr_array = [float(x.strip()) for x in str(s_data['전체심박데이터']).split(",")]
    wp, mp, cp = s_data['웜업파워'], s_data['본훈련파워'], s_data['쿨다운파워']
    time_array = [i*5 for i in range(len(hr_array))]
    
    # --- 가변적 스텝 파워 로직 ---
    # 데이터 포인트의 마지막 직전까지 본훈련 파워를 유지하고, 
    # 마지막 데이터(쿨다운 시작점)에서 정확히 수직 낙하함
    power_array = []
    num_points = len(hr_array)
    for i in range(num_points):
        if i < 2: power_array.append(wp)
        elif i < num_points - 1: power_array.append(mp)
        else: power_array.append(cp)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 파워 스텝 그래프
    fig.add_trace(go.Scatter(x=time_array, y=power_array, name="Power (W)", 
                             line=dict(color='rgba(0, 223, 216, 1.0)', width=3, shape='hv'),
                             fill='tozeroy', fillcolor='rgba(0, 223, 216, 0.1)'), secondary_y=False)
    
    # 심박 곡선
    fig.add_trace(go.Scatter(x=time_array, y=hr_array, name="Heart Rate (BPM)", 
                             line=dict(color='#ff4b4b', width=4, shape='spline')), secondary_y=True)

    # 배경 구간 표시 (가변 시간 반영)
    m_end = time_array[-1] - 5
    fig.add_vrect(x0=0, x1=10, fillcolor="gray", opacity=0.1, annotation_text="WU")
    fig.add_vrect(x0=10, x1=m_end, fillcolor="blue", opacity=0.05, annotation_text="Main")
    fig.add_vrect(x0=m_end, x1=time_array[-1], fillcolor="gray", opacity=0.1, annotation_text="CD")

    fig.update_layout(template="plotly_dark", height=500, hovermode="x unified")
    fig.update_yaxes(range=[0, 200], secondary_y=False)
    fig.update_yaxes(range=[min(hr_array)-10, max(hr_array)+10], secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Drift (Decoupling)", f"{s_data['디커플링(%)']}%")
