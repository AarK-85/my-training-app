import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# Gemini API Setup
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

# 2. Genesis Inspired Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Lexend:wght@300;500&display=swap');
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Lexend', sans-serif; }
    
    div[data-testid="stMetricValue"] { color: #938172 !important; font-size: 2.2rem !important; font-weight: 300 !important; letter-spacing: -0.03em; }
    div[data-testid="stMetricLabel"] { color: #A1A1AA !important; text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.7rem !important; }

    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; font-size: 0.8rem; letter-spacing: 0.1em; text-transform: uppercase; padding: 0px 25px; transition: all 0.3s ease; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; background-color: #27272a !important; border: 1px solid #938172 !important; }

    div.stButton > button { background-color: #18181b; color: #ffffff; border: 1px solid #938172; border-radius: 4px; padding: 0.6rem 1.2rem; font-family: 'Lexend', sans-serif; letter-spacing: 0.1em; transition: all 0.3s ease; text-transform: uppercase; width: 100%; }
    div.stButton > button:hover { background-color: #938172; color: #000000; box-shadow: 0 0 15px rgba(147, 129, 114, 0.4); }

    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #938172; padding-left: 15px; }
    .summary-box { background-color: #0c0c0e; border: 1px solid #1c1c1f; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
    .summary-text { color: #A1A1AA; font-size: 0.95rem; font-weight: 300; line-height: 1.6; font-style: italic; }
    .recovery-badge { display: inline-block; background-color: #938172; color: #000000; padding: 2px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-top: 10px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync Logic
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

# 4. Sidebar Navigation
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em; font-size:1.2rem;'>ZONE 2 LAB</h2>", unsafe_allow_html=True)
    st.markdown("---")
    if not df.empty:
        sessions = sorted(df["회차"].unique().astype(int).tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None

# 5. Dashboard Layout
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: SESSION REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Session Configuration</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Main Training Duration (min)", 15, 180, 60, step=5)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("Warm-up Power (W)", value=100)
    f_mp = p2.number_input("Target Main (W)", value=140)
    f_cp = p3.number_input("Cool-down (W)", value=90)

    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            def_hr = int(float(existing_hrs[i])) if i < len(existing_hrs) else 130
            hr_val = st.number_input(f"T + {i*5}m HR", value=def_hr, key=f"hr_pro_v7_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))

    if st.button("COMMIT PERFORMANCE DATA", use_container_width=True):
        main_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(main_hrs) // 2
        f_ef = f_mp / np.mean(main_hrs[:mid]) if mid > 0 else 0
        s_ef = f_mp / np.mean(main_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
        updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
        updated_df['회차'] = updated_df['회차'].astype(int)
        conn.update(data=updated_df); st.success("Cloud Database Synced."); st.rerun()

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data is not None:
        st.markdown(f"### Intelligence Briefing: Session {int(s_data['회차'])}")
        
        current_dec = s_data['디커플링(%)']
        current_p = int(s_data['본훈련파워'])
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        avg_hr = np.mean(hr_array[2:-1])
        avg_ef = round(current_p / avg_hr, 2)
        
        # [4번 추가] Recovery Window & Summary Logic
        stability = "Optimal" if current_dec < 5 else "Moderate" if current_dec < 8 else "High Fatigue"
        recovery_time = "24 Hours" if current_dec < 5 else "36 Hours" if current_dec < 8 else "48 Hours+"
        
        st.markdown(f"""
        <div class="summary-box">
            <p class="summary-text">
            Session {int(s_data['회차'])} at {current_p}W showed <b>{stability}</b> cardiac stability with a <b>{current_dec}%</b> decoupling rate. 
            Aerobic efficiency is currently tracked at <b>{avg_ef} EF</b>.
            </p>
            <span class="recovery-badge">Recommended Recovery: {recovery_time}</span>
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Target Output", f"{current_p}W")
        m2.metric("Decoupling Index", f"{current_dec}%")
        m3.metric("Avg Pulse", f"{int(avg_hr)}bpm")
        m4.metric("Efficiency Factor", f"{avg_ef}")

        # [2번 추가] HR Drift Detail 시각화 그래프
        time_x = [i*5 for i in range(len(hr_array))]
        power_y = [int(s_data['웜업파워']) if t < 10 else (current_p if t < 10 + int(s_data['본훈련시간']) else int(s_data['쿨다운파워'])) for t in time_x]
        
        # 실시간 EF 추이 (Drift 상세 분석용)
        ef_trend = [round(p / h, 2) if h > 0 else 0 for p, h in zip(power_y, hr_array)]

        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        # Power Line
        fig1.add_trace(go.Scatter(x=time_x, y=power_y, name="Power (W)", line=dict(color='#938172', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), secondary_y=False)
        # HR Line
        fig1.add_trace(go.Scatter(x=time_x, y=hr_array, name="Heart Rate (bpm)", line=dict(color='#F4F4F5', width=2, dash='dot')), secondary_y=True)
        # [2번 핵심] Efficiency Drift (상단에 얇게 표시)
        fig1.add_trace(go.Scatter(x=time_x[2:-1], y=ef_trend[2:-1], name="EF Drift", line=dict(color='rgba(147, 129, 114, 0.3)', width=1)), secondary_y=True)
        
        fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=20, b=0), hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)

        st.divider()
        st.markdown("### :material/chat: Discussion with Gemini Coach")
        if gemini_ready:
            if "messages" not in st.session_state: st.session_state.messages = []
            chat_box = st.container(height=300)
            with chat_box:
                for m in st.session_state.messages:
                    with st.chat_message(m["role"]): st.markdown(m["content"])
            if pr := st.chat_input("Ask about your HR drift or recovery..."):
                st.session_state.messages.append({"role": "user", "content": pr})
                with chat_box:
                    with st.chat_message("user"): st.markdown(pr)
                with st.spinner("Coach is calculating your recovery needs..."):
                    try:
                        res = ai_model.generate_content(f"Analyze: Session {int(s_data['회차'])}, Power {current_p}W, Decoupling {current_dec}%. Goal: 160W. User: {pr}")
                        with chat_box:
                            with st.chat_message("assistant"):
                                st.markdown(res.text)
                                st.session_state.messages.append({"role": "assistant", "content": res.text})
                    except Exception as e: st.error(f"Coach is offline: {e}")

# --- [TAB 3: LONG-TERM PROGRESSION] ---
with tab_trends:
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'])
        st.markdown('<p class="section-title">Aerobic Stability Trend</p>', unsafe_allow_html=True)
        # 디커플링 변화 추이 (회복이 잘 되고 있는지 확인용)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=df['날짜'], y=df['디커플링(%)'], mode='lines+markers', line=dict(color='#938172', width=2), fill='tozeroy'))
        fig3.add_hline(y=5.0, line_dash="dash", line_color="#10b981", annotation_text="Optimal Threshold")
        fig3.update_layout(template="plotly_dark", height=300, title="Decoupling Over Time")
        st.plotly_chart(fig3, use_container_width=True)
        
        st.markdown('<p class="section-title">Strategic Progression (Target: 160W)</p>', unsafe_allow_html=True)
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=df['날짜'], y=df['본훈련파워'], mode='lines+markers', fill='tozeroy', line=dict(color='#ffffff')))
        fig5.add_hline(y=160, line_dash="dash", line_color="#ef4444", annotation_text="Final Goal 160W")
        fig5.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(fig5, use_container_width=True)
