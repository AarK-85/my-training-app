import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# Gemini API Setup (기본 로직 유지)
try:
    import google.generativeai as genai
    gemini_installed = True
except ImportError:
    gemini_installed = False

gemini_ready = False
if gemini_installed:
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            ai_model = genai.GenerativeModel('models/gemini-1.5-flash')
            gemini_ready = True
        except: gemini_ready = False

# 2. Genesis Inspired Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Lexend:wght@300;500&display=swap');
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Lexend', sans-serif; }
    
    div[data-testid="stMetricValue"] { color: #938172 !important; font-size: 2.2rem !important; font-weight: 300 !important; }
    div[data-testid="stMetricLabel"] { color: #A1A1AA !important; text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.7rem !important; }

    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; font-size: 0.8rem; text-transform: uppercase; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; background-color: #27272a !important; border: 1px solid #938172 !important; }

    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #938172; padding-left: 15px; }
    .summary-box { background-color: #0c0c0e; border: 1px solid #1c1c1f; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
    .summary-text { color: #A1A1AA; font-size: 0.95rem; font-weight: 300; line-height: 1.6; font-style: italic; }
    .recovery-badge { display: inline-block; background-color: #938172; color: #000000; padding: 2px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-top: 10px; text-transform: uppercase; }
    .guide-text { color: #71717a; font-size: 0.85rem; line-height: 1.5; padding: 10px; border-left: 1px solid #27272a; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    if '회차' in df.columns:
        df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(0).astype(int)
    for col in ['웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간', '디커플링(%)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 4. Sidebar
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em; font-size:1.2rem;'>ZONE 2 LAB</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().astype(int).tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None

# 5. Dashboard
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] (동일 로직 생략 가능하나 전체 코드 제공 위해 유지) ---
with tab_entry:
    # (이전 v7.3과 동일한 등록 로직)
    st.markdown('<p class="section-title">Session Configuration</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Main Training Duration (min)", 15, 180, 60, step=5)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("Warm-up Power (W)", value=100)
    f_mp = p2.number_input("Target Main (W)", value=140)
    f_cp = p3.number_input("Cool-down (W)", value=90)
    # 심박 데이터 입력 부분... (생략 및 v7.3 로직 유지)

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data is not None:
        st.markdown(f"### Intelligence Briefing: Session {int(s_data['회차'])}")
        
        current_dec = s_data['디커플링(%)']
        current_p = int(s_data['본훈련파워'])
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        avg_hr = np.mean(hr_array[2:-1])
        avg_ef = round(current_p / avg_hr, 2)
        
        recovery_time = "24 Hours" if current_dec < 5 else "36 Hours" if current_dec < 8 else "48 Hours+"
        
        st.markdown(f"""
        <div class="summary-box">
            <p class="summary-text">Today's session maintained <b>{current_p}W</b> with <b>{current_dec}%</b> decoupling. Efficiency factor is <b>{avg_ef}</b>.</p>
            <span class="recovery-badge">Recommended Recovery: {recovery_time}</span>
        </div>
        """, unsafe_allow_html=True)

        # [핵심 업데이트: 그래프 분리 및 색상 일치]
        col_graph, col_guide = st.columns([3, 1])
        
        with col_graph:
            time_x = [i*5 for i in range(len(hr_array))]
            power_y = [int(s_data['웜업파워']) if t < 10 else (current_p if t < 10 + int(s_data['본훈련시간']) else int(s_data['쿨다운파워'])) for t in time_x]
            ef_trend = [round(p / h, 2) if h > 0 else 0 for p, h in zip(power_y, hr_array)]

            # 2개의 행으로 분리된 서브플롯 생성
            fig = make_subplots(rows=2, cols=1, 
                                shared_xaxes=True, 
                                vertical_spacing=0.1,
                                subplot_titles=("POWER & HEART RATE TELEMETRY", "AEROBIC EFFICIENCY (EF) DRIFT"),
                                specs=[[{"secondary_y": True}], [{"secondary_y": False}]])

            # 상단 그래프 1: Power (Genesis Copper)
            fig.add_trace(go.Scatter(x=time_x, y=power_y, name="Power", 
                                     line=dict(color='#938172', width=4, shape='hv'), 
                                     fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), row=1, col=1, secondary_y=False)
            
            # 상단 그래프 2: Heart Rate (White)
            fig.add_trace(go.Scatter(x=time_x, y=hr_array, name="Heart Rate", 
                                     line=dict(color='#F4F4F5', width=2, dash='dot')), row=1, col=1, secondary_y=True)

            # 하단 그래프: Efficiency Drift (Magma Orange) - 분리되어 변화폭이 뚜렷함
            fig.add_trace(go.Scatter(x=time_x[2:-1], y=ef_trend[2:-1], name="EF Drift", 
                                     line=dict(color='#FF4D00', width=3)), row=2, col=1)

            # 축 설정: 각 지표의 색상과 축 숫자의 색상을 일치시킴
            fig.update_layout(
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                height=700, showlegend=True,
                # 상단 왼쪽 Y축 (Power)
                yaxis=dict(title="Power (W)", titlefont=dict(color="#938172"), tickfont=dict(color="#938172"), gridcolor="#1c1c1f"),
                # 상단 오른쪽 Y축 (Heart Rate)
                yaxis2=dict(title="HR (bpm)", titlefont=dict(color="#F4F4F5"), tickfont=dict(color="#F4F4F5"), anchor="x", overlaying="y", side="right"),
                # 하단 Y축 (EF)
                yaxis3=dict(title="Efficiency (EF)", titlefont=dict(color="#FF4D00"), tickfont=dict(color="#FF4D00"), gridcolor="#1c1c1f"),
                xaxis2=dict(title="Time (min)", gridcolor="#1c1c1f")
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_guide:
            st.markdown(f"""
            <div class="guide-text" style="margin-top:40px;">
            <p><b style="color:#938172;">Copper Axis (Power)</b><br>훈련 강도를 나타냅니다.</p>
            <p><b style="color:#F4F4F5;">White Axis (Heart Rate)</b><br>심장의 반응을 나타냅니다.</p>
            <p><b style="color:#FF4D00;">Magma Axis (EF Drift)</b><br>하단 전용 그래프에서 효율 변화를 0.01 단위로 정밀하게 관찰하세요.</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        # Gemini Coach 부분 유지...
