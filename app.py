import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="GENESIS | Zone 2 Precision Lab", layout="wide")

# Gemini API Setup (Base Reference: Auto-Matching System)
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
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else 'models/gemini-pro'
            ai_model = genai.GenerativeModel(target_model)
            gemini_ready = True
        except: gemini_ready = False

# 2. Genesis Brand Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Lexend:wght@300;500&display=swap');

    /* Global Style */
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Lexend', sans-serif; }
    
    /* Genesis Copper Metric */
    div[data-testid="stMetricValue"] { 
        color: #938172 !important; 
        font-size: 2.2rem !important; 
        font-weight: 300 !important;
        letter-spacing: -0.03em;
    }
    div[data-testid="stMetricLabel"] { 
        color: #A1A1AA !important; 
        text-transform: uppercase; 
        letter-spacing: 0.1em;
        font-size: 0.7rem !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: transparent; border: none;
        color: #52525b; font-size: 0.8rem; letter-spacing: 0.2em; text-transform: uppercase;
    }
    .stTabs [aria-selected="true"] { 
        color: #ffffff !important; 
        border-bottom: 2px solid #938172 !important; 
    }

    /* Section Title */
    .section-title { 
        color: #938172; font-size: 0.75rem; font-weight: 500; 
        text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; 
        border-bottom: 1px solid #27272a; padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    if '회차' in df.columns:
        df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(0).astype(int)
    for col in ['웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간', '디커플링(%)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 4. Sidebar - History Management
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em; font-size:1.2rem;'>GENESIS LAB</h2>", unsafe_allow_html=True)
    st.markdown("---")
    if not df.empty:
        sessions = sorted(df["회차"].unique().astype(int).tolist(), reverse=True)
        selected_session = st.selectbox("ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None

# 5. Main Interface
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: SESSION REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Session Configuration</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Main Interval (min)", 15, 180, 60, step=5)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("Warm-up (W)", value=100)
    f_mp = p2.number_input("Target Power (W)", value=140)
    f_cp = p3.number_input("Cool-down (W)", value=90)

    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry (HR)</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            label = f"T + {i*5}m"
            hr_val = st.number_input(label, value=130, key=f"hr_gen_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))

    if st.button("COMMIT SESSION DATA", use_container_width=True):
        main_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(main_hrs) // 2
        f_ef = f_mp / np.mean(main_hrs[:mid]) if mid > 0 else 0
        s_ef = f_mp / np.mean(main_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
        updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
        conn.update(data=updated_df); st.success("Database Updated Successfully."); st.rerun()

# --- [TAB 2: PERFORMANCE ANALYSIS] ---
with tab_analysis:
    if s_data is not None:
        st.markdown(f"### Intelligence Briefing: Session {int(s_data['회차'])}")
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        current_dec, current_p, current_dur = s_data['디커플링(%)'], int(s_data['본훈련파워']), int(s_data['본훈련시간'])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Target Intensity", f"{current_p}W")
        m2.metric("Decoupling Index", f"{current_dec}%")
        m3.metric("Avg Pulse", f"{int(np.mean(hr_array[2:-1]))}bpm")
        m4.metric("Efficiency Factor", f"{round(current_p / np.mean(hr_array[2:-1]), 2)}")

        # Genesis Signature Chart (Copper & White)
        time_x = [i*5 for i in range(len(hr_array))]
        power_y = [int(s_data['웜업파워']) if t < 10 else (current_p if t < 10 + current_dur else int(s_data['쿨다운파워'])) for t in time_x]
        
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        # Power Line (Copper)
        fig1.add_trace(go.Scatter(x=time_x, y=power_y, name="Power Output", line=dict(color='#938172', width=3, shape='hv'), fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), secondary_y=False)
        # HR Line (White/Silver)
        fig1.add_trace(go.Scatter(x=time_x, y=hr_array, name="Heart Rate", line=dict(color='#F4F4F5', width=2, dash='dot')), secondary_y=True)
        
        fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(l=0, r=0, t=20, b=0), font=dict(family="Inter"))
        st.plotly_chart(fig1, use_container_width=True)

        st.divider()
        st.markdown('<p class="section-title">AI Coaching Insights</p>', unsafe_allow_html=True)
        if gemini_ready:
            chat_box = st.container(height=250)
            if pr := st.chat_input("Inquire about your performance..."):
                with st.spinner("Consulting Gemini Intelligence..."):
                    res = ai_model.generate_content(f"Analyze: Session {int(s_data['회차'])}, Power {current_p}W, Decoupling {current_dec}%. User asks: {pr}")
                    st.info(res.text)

# --- [TAB 3: LONG-TERM PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">Volume & Stability Trends</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(go.Figure(go.Bar(x=df['날짜'], y=df['본훈련시간'], marker_color='#938172')).update_layout(template="plotly_dark", title="Weekly Accumulation", height=300), use_container_width=True)
        with col2:
            st.plotly_chart(go.Figure(go.Scatter(x=df['날짜'], y=df['디커플링(%)'], line=dict(color='#ffffff'))).update_layout(template="plotly_dark", title="Stability Index (Decoupling)", height=300), use_container_width=True)
