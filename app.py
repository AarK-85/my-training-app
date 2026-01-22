import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Phase 2 Aggressive Coach v9.998", layout="wide")

# 2. Styling (Perfect Black Theme)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .stApp { background-color: #000000 !important; }
    [data-testid="stSidebar"] { background-color: #0c0c0e !important; }
    h1, h2, h3, p { color: #ffffff !important; font-family: 'Lexend', sans-serif; }
    .stButton > button { background-color: #18181b !important; color: #ffffff !important; border: 1px solid #FF4D00 !important; border-radius: 8px !important; width: 100% !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #FF4D00 !important; }
    .section-title { color: #FF4D00; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #FF4D00; padding-left: 15px; }
    .briefing-card { border: 1px solid #27272a; padding: 22px; border-radius: 12px; background: #0c0c0e; margin-top: 10px; min-height: 160px; border-left: 5px solid #FF4D00; }
    .prescription-badge { background-color: #FF4D00; color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-bottom: 12px; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(0).astype(int)
    if '훈련타입' not in df.columns: df['훈련타입'] = 'ZONE 2'
    df = df.sort_values('회차')

# 4. Sidebar Archive
with st.sidebar:
    st.markdown("<h2 style='color:#FF4D00; letter-spacing:0.1em;'>PHASE 2 COACH</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH DATASET"): st.cache_data.clear(); st.rerun()

tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 2: PERFORMANCE (Active Phase 2 AI Coach)] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        time_x = [i*5 for i in range(len(hr_array))]
        c_type, c_p, c_dur, c_dec = s_data['훈련타입'], int(s_data['본훈련파워']), int(s_data['본훈련시간']), s_data['디커플링(%)']

        # [Phase 2 AI Engine]
        last_3_types = df.tail(3)['훈련타입'].tolist()
        
        # 주기 판단 (Z2-Z2-SST)
        if not last_3_types: 
            n_type = "ZONE 2"
            phase_msg = "Phase 2 사이클 시작"
        elif last_3_types[-1] == "SST": 
            n_type = "ZONE 2"
            phase_msg = "Cycle Step 1: Zone 2 (공사 시작)"
        elif len(last_3_types) >= 2 and last_3_types[-1] == "ZONE 2" and (len(last_3_types) < 3 or last_3_types[-2] != "ZONE 2"):
            n_type = "ZONE 2"
            phase_msg = "Cycle Step 2: Zone 2 (영토 확장)"
        else:
            n_type = "SST"
            phase_msg = "Cycle Step 3: SST (천장 뚫기)"

        # 처방 로직
        if n_type == "ZONE 2":
            z2_past = df[df['훈련타입'] == "ZONE 2"].iloc[-1]
            p_dec, p_p, p_dur = z2_past['디커플링(%)'], int(z2_past['본훈련파워']), int(z2_past['본훈련시간'])
            if p_dec < 8.0:
                n_pres = f"{p_p+5}W / {max(p_dur, 75)}m"
                coach_msg = f"디커플링 {p_dec}%로 8% 미만 '성공'. 지침에 따라 즉시 {p_p+5}W로 상향 제안합니다."
            else:
                n_pres = f"{p_p}W / {p_dur}m"
                coach_msg = f"디커플링 {p_dec}%로 안정화 필요. 8% 미만 달성까지 {p_p}W를 유지하며 내실을 다지세요."
        else:
            sst_past = df[df['훈련타입'] == "SST"].iloc[-1]
            p_p = int(sst_past['본훈련파워'])
            n_pres = f"{p_p+5}W SST"
            coach_msg = "SST 완수 확인. 훈련 지침에 따라 다음 세션은 무조건 상향하여 천장을 높입니다."

        st.markdown(f'<p class="section-title">{phase_msg}</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: st.markdown(f'<div class="briefing-card"><span class="prescription-badge">{c_type} RESULT</span><p style="font-size:1.5rem; font-weight:600; margin:0;">{c_p}W / {c_dur}m</p><p style="color:#A1A1AA;">Decoupling: <b>{c_dec}%</b></p></div>', unsafe_allow_html=True)
        with cb: st.markdown(f'<div class="briefing-card" style="border-color:#FF4D00;"><span class="prescription-badge">NEXT STEP</span><p style="font-size:1.5rem; font-weight:600; color:#FF4D00; margin:0;">{n_pres}</p><p style="margin-top:5px; font-size:0.9rem; color:#A1A1AA;">{coach_msg}</p></div>', unsafe_allow_html=True)

        # [Graphs - All Black Theme]
        def update_black(fig):
            fig.update_layout(template="plotly_dark", plot_bgcolor='black', paper_bgcolor='black', xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'))
            return fig

        fig_corr = make_subplots(specs=[[{"secondary_y": True}]])
        p_y = [c_p if 10 <= t <= 10+c_dur else 97 for t in time_x]
        fig_corr.add_trace(go.Scatter(x=time_x, y=p_y, name="Power", fill='tozeroy', line=dict(color='#FF4D00', width=3)), secondary_y=False)
        fig_corr.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#ffffff', dash='dot')), secondary_y=True)
        st.plotly_chart(update_black(fig_corr), use_container_width=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">W/kg Growth Track (Target 180W)</p>', unsafe_allow_html=True)
        fig_w = update_black(go.Figure(go.Scatter(x=df['회차'], y=df['본훈련파워']/85, mode='lines+markers', line=dict(color='#FF4D00', width=2), fill='tozeroy')))
        fig_w.add_hline(y=180/85, line_dash="dash", line_color="white", annotation_text="Goal 180W")
        st.plotly_chart(fig_w, use_container_width=True)
