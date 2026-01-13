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
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        ai_model = genai.GenerativeModel('models/gemini-1.5-flash')
        gemini_ready = True
    else: gemini_ready = False
except: gemini_ready = False

# 2. Genesis Inspired Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Lexend:wght@300;500&display=swap');
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Lexend', sans-serif; }
    div[data-testid="stMetricValue"] { color: #938172 !important; font-size: 2.2rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #938172 !important; }
    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #938172; padding-left: 15px; }
    .summary-box { background-color: #0c0c0e; border: 1px solid #1c1c1f; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
    .summary-text { color: #A1A1AA; font-size: 0.95rem; font-weight: 300; line-height: 1.6; font-style: italic; }
    .recovery-badge { display: inline-block; background-color: #938172; color: #000000; padding: 2px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-top: 10px; text-transform: uppercase; }
    .guide-text { color: #71717a; font-size: 0.85rem; line-height: 1.5; padding: 10px; border-left: 1px solid #27272a; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync Logic (캐싱 없이 실시간성 유지)
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

# 4. Sidebar
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em;'>ZONE 2 LAB</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
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
    f_wp = p1.number_input("Warm-up (W)", value=100)
    f_mp = p2.number_input("Target Main (W)", value=140)
    f_cp = p3.number_input("Cool-down (W)", value=90)

    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    existing_raw = str(s_data['전체심박데이터']) if s_data is not None else ""
    existing_hrs = [x.strip() for x in existing_raw.split(',') if x.strip()]
    
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            def_hr = int(float(existing_hrs[i])) if i < len(existing_hrs) else 130
            hr_val = st.number_input(f"T + {i*5}m", value=def_hr, key=f"hr_fix_v7_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))

    if st.button("COMMIT PERFORMANCE DATA", use_container_width=True):
        main_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(main_hrs) // 2
        f_ef = f_mp / np.mean(main_hrs[:mid]) if mid > 0 else 0
        s_ef = f_mp / np.mean(main_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
        updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
        conn.update(data=updated_df); st.success("Synced."); st.rerun()

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data is not None:
        st.markdown(f"### Intelligence Briefing: Session {int(s_data['회차'])}")
        
        current_dec = s_data['디커플링(%)']
        current_p = int(s_data['본훈련파워'])
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        avg_ef = round(current_p / np.mean(hr_array[2:-1]), 2)
        
        recovery_time = "24 Hours" if current_dec < 5 else "36 Hours" if current_dec < 8 else "48 Hours+"
        
        st.markdown(f"""
        <div class="summary-box">
            <p class="summary-text">Session {int(s_data['회차'])} at {current_p}W showed a <b>{current_dec}%</b> decoupling index. Efficiency is at <b>{avg_ef} EF</b>.</p>
            <span class="recovery-badge">Recommended Recovery: {recovery_time}</span>
        </div>
        """, unsafe_allow_html=True)

        # [7.3 스타일의 단일 그래프 + 에러 수정 로직]
        col_graph, col_guide = st.columns([3, 1])
        
        with col_graph:
            time_x = [i*5 for i in range(len(hr_array))]
            power_y = [int(s_data['웜업파워']) if t < 10 else (current_p if t < 10 + int(s_data['본훈련시간']) else int(s_data['쿨다운파워'])) for t in time_x]
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=time_x, y=power_y, name="Power", line=dict(color='#938172', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), secondary_y=False)
            fig.add_trace(go.Scatter(x=time_x, y=hr_array, name="Heart Rate", line=dict(color='#F4F4F5', width=2, dash='dot')), secondary_y=True)
            
            # [7.3 스타일] Efficiency Drift를 단일 그래프에 통합
            ef_trend = [round(current_p / h, 2) if h > 0 else 0 for h in hr_array]
            fig.add_trace(go.Scatter(x=time_x[2:-1], y=ef_trend[2:-1], name="Efficiency Drift", line=dict(color='#FF4D00', width=2)), secondary_y=True)

            # [핵심] 에러를 유발하는 update_yaxes 대신 layout에 직접 축 속성 주입
            fig.update_layout(
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                height=450, margin=dict(l=0, r=0, t=20, b=0), showlegend=True,
                yaxis=dict(title="Power (W)", titlefont=dict(color="#938172"), tickfont=dict(color="#938172")),
                yaxis2=dict(title="HR / Efficiency", titlefont=dict(color="#F4F4F5"), tickfont=dict(color="#F4F4F5"), side="right", overlaying="y", anchor="x")
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_guide:
            st.markdown(f"""
            <div class="guide-text" style="margin-top:40px;">
            <p><b style="color:#FF4D00;">Magma Orange Line</b><br>유산소 효율 추이를 나타냅니다. 이 선이 파워와 평행할수록 심폐 효율이 좋다는 의미입니다.</p>
            </div>
            """, unsafe_allow_html=True)

        if gemini_ready:
            st.divider()
            if pr := st.chat_input("Coach와 대화하기..."):
                with st.spinner("Reviewing laps..."):
                    res = ai_model.generate_content(f"Analyze: Session {int(s_data['회차'])}, Power {current_p}W, Decoupling {current_dec}%. User asks: {pr}")
                    st.info(res.text)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'])
        st.plotly_chart(go.Figure(go.Scatter(x=df['날짜'], y=df['디커플링(%)'], line=dict(color='#FF4D00', width=2))).update_layout(template="plotly_dark", title="Stability Trend (%)"))
        
