import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Hyper-Aggressive Coach v9.992", layout="wide")

# 2. Styling (Perfect Black Theme)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .stApp { background-color: #000000 !important; }
    [data-testid="stSidebar"] { background-color: #0c0c0e !important; }
    h1, h2, h3, p { color: #ffffff !important; font-family: 'Lexend', sans-serif; }
    
    .stButton > button {
        background-color: #18181b !important;
        color: #ffffff !important;
        border: 1px solid #FF4D00 !important;
        border-radius: 8px !important;
        width: 100% !important;
    }
    .stButton > button:hover { border-color: #ffffff !important; color: #FF4D00 !important; }
    
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
    if '파워데이터상세' not in df.columns: df['파워데이터상세'] = ""

# 4. Sidebar
with st.sidebar:
    st.markdown("<h2 style='color:#FF4D00; letter-spacing:0.1em;'>DYNAMIC COACH v9.992</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH DATASET"): st.cache_data.clear(); st.rerun()

tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Workout Mode Selection</p>', unsafe_allow_html=True)
    w_type = st.radio("SELECT TYPE", ["ZONE 2", "SST"], horizontal=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date, f_session = c1.date_input("Date", value=datetime.now().date()), c2.number_input("Session No.", value=int(df["회차"].max()+1) if not df.empty else 1)
    
    if w_type == "ZONE 2":
        f_duration = c3.slider("Duration (min)", 15, 180, 75, step=15)
        st.markdown('<p class="section-title">Zone 2 Aggressive Settings</p>', unsafe_allow_html=True)
        row = st.columns(3)
        # 웜업 제한 해제 (min_value=50, value=97)
        f_wp = row[0].number_input("Warm-up (W)", min_value=50, value=97, step=1)
        f_mp = row[1].number_input("Target (W)", 145)
        f_cp = row[2].number_input("Cool-down (W)", 90)
        f_sst_p_data = f"Z2,{f_wp},{f_mp},{f_cp},0,0,0,0,0"
    else:
        # SST 입력 로직 생략 (v9.991과 동일)
        pass

    # Submit Data 버튼 로직 생략
    if st.button("SUBMIT DATA"):
        pass

# --- [TAB 2: PERFORMANCE] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        time_x = [i*5 for i in range(len(hr_array))]
        
        # (AI Coaching Briefing 로직 생략 - v9.991과 동일)
        
        # [모든 그래프 공통 레이아웃 설정 함수]
        def update_black_theme(fig):
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,1)',
                paper_bgcolor='rgba(0,0,0,1)',
                xaxis=dict(showgrid=True, gridcolor='#27272a'),
                yaxis=dict(showgrid=True, gridcolor='#27272a')
            )
            return fig

        st.markdown('<p class="section-title">Heart Rate Recovery (HRR)</p>', unsafe_allow_html=True)
        fig_hrr = go.Figure(data=go.Scatter(x=time_x[-5:], y=hr_array[-5:], mode='lines+markers', line=dict(color='#FF4D00', width=3)))
        fig_hrr = update_black_theme(fig_hrr)
        st.plotly_chart(fig_hrr, use_container_width=True)

        st.markdown('<p class="section-title">Correlation & Efficiency Drift</p>', unsafe_allow_html=True)
        fig_corr = make_subplots(specs=[[{"secondary_y": True}]])
        # (Power/HR Trace 추가 로직 동일)
        fig_corr = update_black_theme(fig_corr)
        st.plotly_chart(fig_corr, use_container_width=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">W/kg Progression (85kg Fixed)</p>', unsafe_allow_html=True)
        fig_wkg = go.Figure(go.Scatter(x=df['회차'], y=df['본훈련파워']/85, mode='lines+markers', line=dict(color='#FF4D00', width=2)))
        fig_wkg = update_black_theme(fig_wkg)
        st.plotly_chart(fig_wkg, use_container_width=True)
