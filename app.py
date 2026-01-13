import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# 2. Genesis Magma Styling (Fixed Briefing Card Layout)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Lexend', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #938172 !important; }
    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #938172; padding-left: 15px; }
    
    /* Fixed Briefing Card: Responsive and contained */
    .briefing-card { 
        border: 1px solid #27272a; 
        padding: 22px; 
        border-radius: 12px; 
        background: #0c0c0e; 
        margin-top: 10px; 
        min-height: 160px; 
        height: auto;
        display: block;
        overflow: hidden;
        word-wrap: break-word;
    }
    .prescription-badge { background-color: #FF4D00; color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-bottom: 12px; display: inline-block; }
    .guide-box { color: #A1A1AA; font-size: 0.85rem; line-height: 1.6; padding: 20px; border-left: 3px solid #FF4D00; background: rgba(255, 77, 0, 0.05); }
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
    if st.button("🔄 REFRESH DATASET"):
        st.cache_data.clear()
        st.rerun()

# 5. Dashboard Tabs
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: SESSION REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Session Configuration</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Duration (min)", 15, 180, 60, step=5)
    p1, p2, p3 = st.columns(3); f_wp, f_mp, f_cp = p1.number_input("Warm-up (W)", 100), p2.number_input("Target (W)", 140), p3.number_input("Cool-down (W)", 90)
    
    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    hr_raw = str(s_data['전체심박데이터']) if s_data is not None else ""
    hr_list = [x.strip() for x in hr_raw.split(',') if x.strip()]
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            dv = int(float(hr_list[i])) if i < len(hr_list) else 130
            hv = st.number_input(f"T + {i*5}m", value=dv, key=f"hr_v89_{i}", step=1)
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
        c_dec, c_p, c_dur = s_data['디커플링(%)'], int(s_data['본훈련파워']), int(s_data['본훈련시간'])
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        avg_ef = round(c_p / np.mean(hr_array[2:-1]), 2)
        
        if c_dec < 6.0 and c_dur >= 60:
            next_p = c_p + 5 if c_p < 160 else 160
            next_instruct = f"Enter {next_p}W Zone"
            focus_msg = f"Solid base confirmed. Moving to next 5W increment."
        else:
            next_instruct = f"Re-confirm {c_p}W"
            focus_msg = "Stabilize decoupling below 6% before increment."

        st.markdown('<p class="section-title">AI Performance & Next Prescription</p>', unsafe_allow_html=True)
        brief_col1, brief_col2 = st.columns(2)
        with brief_col1:
            st.markdown(f"""<div class="briefing-card"><span class="prescription-badge">CURRENT RESULT</span>
            <p style="margin:0; font-weight:600;">Session {int(s_data['회차'])}: {c_p}W / {c_dur}m</p>
            <p style="margin:5px 0 0 0; color:#A1A1AA; font-size:0.9rem;">Efficiency: <b>{avg_ef} EF</b><br>Decoupling: <b>{c_dec}%</b></p></div>""", unsafe_allow_html=True)
        with brief_col2:
            st.markdown(f"""<div class="briefing-card" style="border-color: #FF4D00;"><span class="prescription-badge">NEXT PRESCRIPTION</span>
            <p style="margin:0; font-weight:600;">Target: {next_instruct}</p>
            <p style="margin:5px 0 0 0; color:#A1A1AA; font-size:0.9rem;">Note: {focus_msg}</p></div>""", unsafe_allow_html=True)

        st.markdown('<p class="section-title">Power & Heart Rate Correlation</p>', unsafe_allow_html=True)
        time_x = [i*5 for i in range(len(hr_array))]
        p_y = [int(s_data['웜업파워']) if t < 10 else (c_p if t < 10 + int(s_data['본훈련시간']) else int(s_data['쿨다운파워'])) for t in time_x]
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=time_x, y=p_y, name="Power", line=dict(color='#938172', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_x, y=hr_array, name="Heart Rate", line=dict(color='#F4F4F5', width=2, dash='dot')), secondary_y=True)
        fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        fig1.layout.yaxis.update(title=dict(text="Power (W)", font=dict(color="#938172")), tickfont=dict(color="#938172"))
        fig1.layout.yaxis2.update(title=dict(text="HR (bpm)", font=dict(color="#F4F4F5")), tickfont=dict(color="#F4F4F5"), side="right", overlaying="y")
        st.plotly_chart(fig1, use_container_width=True)

        st.markdown('<p class="section-title">Efficiency Drift Analysis</p>', unsafe_allow_html=True)
        ce1, ce2 = st.columns([3, 1])
        with ce1:
            ef_y = [round(c_p / h, 2) if h > 0 else 0 for h in hr_array]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=time_x[2:-1], y=ef_y[2:-1], line=dict(color='#FF4D00', width=3), fill='tozeroy', fillcolor='rgba(255, 77, 0, 0.05)'))
            fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0, r=0, t=10, b=0))
            fig2.layout.yaxis.update(title=dict(text="EF Factor", font=dict(color="#FF4D00")), tickfont=dict(color="#FF4D00"))
            st.plotly_chart(fig2, use_container_width=True)
        with ce2:
            st.markdown('<div class="guide-box"><b>Aerobic Stability</b><br><br>Downward slope indicates cardiac drift. Flat line means solid aerobic base.</div>', unsafe_allow_html=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">Road to 160W Final Goal</p>', unsafe_allow_html=True)
        current_max = df['본훈련파워'].max()
        progress = min(100, int((current_max / 160) * 100))
        st.write(f"**Current Achievement: {progress}% of 160W Target**")
        st.progress(progress / 100)

        st.markdown('<p class="section-title">Aerobic Stability Trend</p>', unsafe_allow_html=True)
        fig_dec = go.Figure()
        fig_dec.add_trace(go.Scatter(x=df['회차'], y=df['디커플링(%)'], mode='lines+markers', line=dict(color='#FF4D00', width=2)))
        fig_dec.add_hline(y=5.0, line_dash="dash", line_color="#938172", annotation_text="Goal (5%)")
        fig_dec.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        fig_dec.update_xaxes(dtick=1, title="Session No.")
        st.plotly_chart(fig_dec, use_container_width=True)
        
        st.markdown('<p class="section-title">Power Output Progression</p>', unsafe_allow_html=True)
        fig_pwr = go.Figure()
        fig_pwr.add_trace(go.Bar(x=df['회차'], y=df['본훈련파워'], marker_color='#938172'))
        fig_pwr.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        fig_pwr.update_xaxes(dtick=1, title="Session No.")
        st.plotly_chart(fig_pwr, use_container_width=True)
