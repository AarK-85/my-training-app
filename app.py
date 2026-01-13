import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# --- [Gemini API Setup: Advanced Coach Model] ---
gemini_ready = False
try:
    import google.generativeai as genai
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else (available_models[0] if available_models else None)
        if target_model:
            ai_model = genai.GenerativeModel(target_model)
            gemini_ready = True
except:
    gemini_ready = False

# 2. Genesis Magma Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Lexend', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #938172 !important; }
    .briefing-card { border: 1px solid #27272a; padding: 22px; border-radius: 12px; background: #0c0c0e; margin-top: 10px; min-height: 150px; }
    .prescription-badge { background-color: #FF4D00; color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-bottom: 10px; display: inline-block; }
    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #938172; padding-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync & Integer Enforcement
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(0).astype(int)
    for col in ['웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간', '디커플링(%)']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 4. Sidebar Archive
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em;'>ZONE 2 LAB</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0, format_func=lambda x: f"Session {int(x)}")
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    st.button("🔄 REFRESH DATASET", on_click=st.cache_data.clear)

# 5. Dashboard Tabs
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] (동일 구조 유지) ---
with tab_entry:
    # ... (기존과 동일하되, 정수 입력 유지)
    st.markdown('<p class="section-title">Session Configuration</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Duration (min)", 15, 180, 60, step=5)
    p1, p2, p3 = st.columns(3); f_wp, f_mp, f_cp = p1.number_input("Warm-up (W)", 100), p2.number_input("Target (W)", 140), p3.number_input("Cool-down (W)", 90)
    st.divider()
    # (심박 데이터 입력 섹션 생략 - 기존 코드와 동일)
    # ... [생략된 심박 입력 코드] ...

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data is not None:
        st.markdown(f"### Intelligence Briefing: Session {int(s_data['회차'])}")
        c_dec, c_p, c_dur = s_data['디커플링(%)'], int(s_data['본훈련파워']), int(s_data['본훈련시간'])
        
        # [핵심] 새로운 AI 코치 모델에 따른 처방 로직
        # 17회차 분석 기준 지시 사항 반영 (디커플링 및 파워 기반)
        if c_dec < 5.0:
            target_p = c_p + 5 if c_p < 160 else 160
            next_instruct = f"Increase Target to {target_p}W"
        elif c_dec < 8.0:
            next_instruct = f"Maintain {c_p}W for 60-90m"
        else:
            next_instruct = "Recovery Focus: Same Power, Less Duration"

        st.markdown('<p class="section-title">AI Performance & Next Prescription</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""<div class="briefing-card"><span class="prescription-badge">CURRENT STATUS</span><br>
            <b>Stability Achieved:</b> Session {int(s_data['회차'])} at {c_p}W shows {c_dec}% drift.<br>
            Your aerobic base is currently <b>{'Solid' if c_dec < 5 else 'Adapting'}</b>.</div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="briefing-card" style="border-color: #FF4D00;"><span class="prescription-badge">NEXT PRESCRIPTION</span><br>
            <b>Target Objective:</b> {next_instruct}<br>
            <b>Focus:</b> Maintain pure aerobic state with decoupling < 5%.</div>""", unsafe_allow_html=True)

        # (그래프 및 Gemini Coach 섹션 생략 - 기존 v8.4의 정수 고정 버전 유지)
        # ... [생략된 그래프 코드] ...

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">Long-term Aerobic Stability Trend</p>', unsafe_allow_html=True)
        # 160W 목표 게이지 (우리가 논의했던 새로운 지표)
        current_max = df['본훈련파워'].max()
        progress = min(100, int((current_max / 160) * 100))
        st.write(f"**Progress to Final Goal (160W): {progress}%**")
        st.progress(progress / 100)
        
        # (기존 Progression 그래프 코드 - dtick=1 적용 버전 유지)
        # ... [생략된 그래프 코드] ...
