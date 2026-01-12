import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

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
        
        # 파워 및 시간 설정
        w_p = st.number_input("웜업W", value=int(s_data['웜업파워']) if s_data is not None else 97)
        main_p = st.number_input("본훈련W", value=int(s_data['본훈련파워']) if s_data is not None else 135)
        c_p = st.number_input("쿨다운W", value=int(s_data['쿨다운파워']) if s_data is not None else 90)
        duration = st.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 90, step=5)
        
        # 심박수 입력칸 생성
        num_main_steps = duration // 5
        total_steps = 2 + num_main_steps + 1
        existing_hrs = [x.strip() for x in str(s_data['전체심박데이터']).split(",")] if s_data is not None else []
        
        hr_inputs = []
        cols = st.columns(3)
        for i in range(total_steps):
            default_val = float(existing_hrs[i]) if i < len(existing_hrs) else 130.0
            with cols[i % 3]:
                hr_val = st.number_input(f"{i*5}분 시점", value=default_val, key=f"hr_in_{i}")
                hr_inputs.append(str(hr_val))
        
        if st.form_submit_button("기록 업데이트"):
            full_hr_str = ", ".join(hr_inputs)
            # 여기에 시트 업데이트 로직 추가 가능
            st.rerun()

# 4. 메인 분석 대시보드
if not df.empty and s_data is not None:
    # --- [NEW] AI 코치 헤드라인 섹션 ---
    st.markdown("### 🤖 AI Coach's Daily Briefing")
    
    hr_array = [float(x.strip()) for x in str(s_data['전체심박데이터']).split(",")]
    max_hr = max(hr_array)
    current_dec = s_data['디커플링(%)']
    current_p = s_data['본훈련파워']
    
    if current_dec <= 5.0:
        headline = f"🔥 **완벽한 제어 상태입니다.** 디커플링 {current_dec}%로 심폐 효율이 안정적이니, {current_p + 5}W로 엔진을 확장할 시점입니다!"
    elif current_dec <= 8.0 and max_hr < 170:
        headline = f"✅ **엔진 확장 가능성이 확인되었습니다.** 디커플링({current_dec}%)이 소폭 있으나 최대심박({max_hr}bpm)이 통제되고 있으니, 다음은 {current_p + 5}W로 도전합시다!"
    else:
        headline = f"⏳ **현재 구간 적응이 더 필요합니다.** 심박 표류({current_dec}%)가 관찰되니, {current_p}W를 반복하여 제어력을 확보합시다."

    st.info(headline)
    st.divider()

    # --- [그래프 1] 정밀 시퀀스 분석 ---
    st.title(f"📊 Session {selected_session} 시퀀스 정밀 분석")
    
    time_array = [i*5 for i in range(len(hr_array))]
    wp, mp, cp = s_data['웜업파워'], s_data['본훈련파워'], s_data['쿨다운파워']
    
    power_array = []
    num_main_end_idx = 2 + (int(s_data['본훈련시간']) // 5)
    
    for i in range(len(time_array)):
        if i < 2: power_array.append(wp)
        elif i < num_main_end_idx: power_array.append(mp)
        else: power_array.append(cp)

    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=time_array, y=power_array, name="Power (W)", line=dict(color='cyan', width=3, shape='hv'), fill='tozeroy', fillcolor='rgba(0, 255, 255, 0.1)'), secondary_y=False)
    fig1.add_trace(go.Scatter(x=time_array, y=hr_array, name="HR (BPM)", line=dict(color='red', width=4, shape='spline')), secondary_y=True)

    m_end_time = int(s_data['본훈련시간']) + 10
    fig1.add_vrect(x0=0, x1=10, fillcolor="gray", opacity=0.1, annotation_text="WU")
    fig1.add_vrect(x0=10, x1=m_end_time, fillcolor="blue", opacity=0.05, annotation_text="Main")
    fig1.add_vrect(x0=m_end_time, x1=time_array[-1], fillcolor="gray", opacity=0.1, annotation_text="CD")
    
    fig1.update_layout(template="plotly_dark", height=500, hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    # --- [그래프 2] Cardiac Drift 분석 ---
    st.divider()
    st.subheader("🎯 Cardiac Drift 시각적 분석 (전반 vs 후반)")
    
    main_hrs = hr_array[2:-1]
    mid_point = len(main_hrs) // 2
    first_half = main_hrs[:mid_point]
    second_half = main_hrs[mid_point:]
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=list(range(len(first_half))), y=first_half, name='1st Half (Stability)', line=dict(color='cyan', width=2)))
    fig2.add_trace(go.Scatter(x=list(range(len(second_half))), y=second_half, name='2nd Half (Drift)', line=dict(color='red', width=2), fill='tonexty', fillcolor='rgba(255, 0, 0, 0.1)'))
    
    fig2.update_layout(template="plotly_dark", height=400)
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.plotly_chart(fig2, use_container_width=True)
    with col_b:
        drift_bpm = np.mean(second_half) - np.mean(first_half)
        st.metric("심박 상승 폭", f"+{drift_bpm:.1f} bpm", delta=f"{s_data['디커플링(%)']}%", delta_color="inverse")

    # --- [그래프 3 & 4] EF 추이 및 HRR 분석 ---
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📈 유산소 효율성(EF) 추이")
        def calc_ef(row):
            hrs = [float(x.strip()) for x in str(row['전체심박데이터']).split(",")]
            return row['본훈련파워'] / np.mean(hrs[2:-1])
        
        trend_df = df.copy()
        trend_df['EF'] = trend_df.apply(calc_ef, axis=1)
        fig3 = go.Scatter(x=trend_df['회차'], y=trend_df['EF'], mode='lines+markers', line=dict(color='springgreen', width=3))
        st.plotly_chart(go.Figure(data=fig3, layout=dict(template="plotly_dark", height=350)), use_container_width=True)

    with c2:
        st.subheader("💓 심박 회복력 (HRR)")
        def calc_hrr(row):
            hrs = [float(x.strip()) for x in str(row['전체심박데이터']).split(",")]
            return hrs[-2] - hrs[-1]
        
        hrr_df = df.copy()
        hrr_df['HRR'] = hrr_df.apply(calc_hrr, axis=1)
        fig4 = go.Bar(x=hrr_df['회차'], y=hrr_df['HRR'], marker_color='orange')
        st.plotly_chart(go.Figure(data=fig4, layout=dict(template="plotly_dark", height=350)), use_container_width=True)
