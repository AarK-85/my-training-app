import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# --- [Gemini API Setup: Auto-Matching System] ---
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

# 2. Genesis Inspired Styling (Standardized to English)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Lexend:wght@300;500&display=swap');
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Lexend', sans-serif; }
    div[data-testid="stMetricValue"] { color: #938172 !important; font-size: 2.2rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #938172 !important; }
    .summary-box { background-color: #0c0c0e; border: 1px solid #1c1c1f; padding: 25px; border-radius: 12px; margin-bottom: 25px; }
    .recovery-badge { display: inline-block; background-color: #938172; color: #000000; padding: 4px 12px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-top: 15px; text-transform: uppercase; }
    .guide-text { color: #71717a; font-size: 0.85rem; line-height: 1.6; padding: 15px; border-left: 1px solid #27272a; background: rgba(24, 24, 27, 0.5); }
    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #938172; padding-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    if '회차' in df.columns: df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(0).astype(int)
    for col in ['웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간', '디커플링(%)']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 4. Sidebar
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em;'>ZONE 2 LAB</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH DATASET"):
        st.cache_data.clear(); st.rerun()

# 5. Dashboard Tabs (All English)
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: SESSION REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Session Configuration</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Main Training Duration (min)", 15, 180, 60, step=5)
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("Warm-up (W)", value=100); f_mp = p2.number_input("Target Main (W)", value=140); f_cp = p3.number_input("Cool-down (W)", value=90)
    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    hr_raw = str(s_data['전체심박데이터']) if s_data is not None else ""; hr_list = [x.strip() for x in hr_raw.split(',') if x.strip()]
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            dv = int(float(hr_list[i])) if i < len(hr_list) else 130
            hv = st.number_input(f"T + {i*5}m", value=dv, key=f"hr_v78_{i}", step=1)
            hr_inputs.append(str(int(hv)))
    if st.button("COMMIT PERFORMANCE DATA", use_container_width=True):
        m_hrs = [int(x) for x in hr_inputs[2:-1]]; mid = len(m_hrs) // 2
        f_ef = f_mp / np.mean(m_hrs[:mid]) if mid > 0 else 0; s_ef = f_mp / np.mean(m_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
        conn.update(data=pd.concat([df[df["회차"] != f_session], pd.DataFrame([new])], ignore_index=True).sort_values("회차")); st.rerun()

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data is not None:
        st.markdown(f"### Intelligence Briefing: Session {int(s_data['회차'])}")
        c_dec, c_p = s_data['디커플링(%)'], int(s_data['본훈련파워'])
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        avg_ef = round(c_p / np.mean(hr_array[2:-1]), 2)
        recovery = "24 Hours" if c_dec < 5 else "36 Hours" if c_dec < 8 else "48 Hours+"
        
        st.markdown(f"""<div class="summary-box"><p class="summary-text" style="color:#A1A1AA;">Session {int(s_data['회차'])} ({c_p}W): <b>{c_dec}%</b> decoupling | <b>{avg_ef} EF</b></p><span class="recovery-badge">Recommended Recovery: {recovery}</span></div>""", unsafe_allow_html=True)

        # 1. Main Visual: Power & HR
        st.markdown('<p class="section-title">Power & Heart Rate Correlation</p>', unsafe_allow_html=True)
        time_x = [i*5 for i in range(len(hr_array))]
        power_y = [int(s_data['웜업파워']) if t < 10 else (c_p if t < 10 + int(s_data['본훈련시간']) else int(s_data['쿨다운파워'])) for t in time_x]
        
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=time_x, y=power_y, name="Power", line=dict(color='#938172', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_x, y=hr_array, name="Heart Rate", line=dict(color='#F4F4F5', width=2, dash='dot')), secondary_y=True)
        fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        fig1.update_yaxes(title_text="Power (W)", titlefont=dict(color="#938172"), tickfont=dict(color="#938172"), secondary_y=False)
        fig1.update_yaxes(title_text="HR (bpm)", titlefont=dict(color="#F4F4F5"), tickfont=dict(color="#F4F4F5"), secondary_y=True)
        st.plotly_chart(fig1, use_container_width=True)

        # 2. Efficiency Drift Analysis (Side-by-side)
        st.markdown('<p class="section-title">Efficiency Drift Analysis</p>', unsafe_allow_html=True)
        col_ef_graph, col_ef_guide = st.columns([3, 1])
        
        with col_ef_graph:
            ef_trend = [round(c_p / h, 2) if h > 0 else 0 for h in hr_array]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=time_x[2:-1], y=ef_trend[2:-1], name="EF Factor", line=dict(color='#FF4D00', width=3), fill='tozeroy', fillcolor='rgba(255, 77, 0, 0.05)'))
            fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
            fig2.update_yaxes(title_text="EF Factor", titlefont=dict(color="#FF4D00"), tickfont=dict(color="#FF4D00"))
            st.plotly_chart(fig2, use_container_width=True)

        with col_ef_guide:
            st.markdown(f"""
            <div class="guide-text" style="border-left: 3px solid #FF4D00; background: rgba(255, 77, 0, 0.02);">
            <b style="color:#FF4D00;">Efficiency Drift Guide</b><br><br>
            The slope of this chart indicates the stability of your aerobic engine.<br><br>
            A flat or slightly increasing line means high efficiency. A downward trend signals cardiac drift and accumulating fatigue.
            </div>
            """, unsafe_allow_html=True)

        if gemini_ready:
            st.markdown('<p class="section-title">Gemini Performance Coach</p>', unsafe_allow_html=True)
            if pr := st.chat_input("Ask Coach..."):
                with st.spinner("Analyzing..."):
                    res = ai_model.generate_content(f"Session {int(s_data['회차'])}, {c_p}W, {c_dec}% decoupling. {pr}")
                    with st.chat_message("assistant", avatar="https://www.gstatic.com/lamda/images/gemini_sparkle_v002.svg"):
                        st.write(res.text)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">Aerobic Stability Trend</p>', unsafe_allow_html=True)
        fig_t = go.Figure(go.Scatter(x=df['날짜'], y=df['디커플링(%)'], mode='lines+markers', line=dict(color='#FF4D00', width=2)))
        fig_t.update_layout(template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        fig_t.update_yaxes(title_text="Decoupling (%)")
        st.plotly_chart(fig_t, use_container_width=True)
