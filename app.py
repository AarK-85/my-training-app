import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Zone 2 Precision Lab v9.6", layout="wide")

# 2. Genesis Magma Styling (Fixed Dark Mode & Typography)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .stApp { background-color: #000000 !important; }
    [data-testid="stSidebar"] { background-color: #0c0c0e !important; }
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff !important; font-family: 'Lexend', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #938172 !important; }
    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #938172; padding-left: 15px; }
    .briefing-card { border: 1px solid #27272a; padding: 22px; border-radius: 12px; background: #0c0c0e; margin-top: 10px; min-height: 180px; height: auto; }
    .prescription-badge { background-color: #FF4D00; color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-bottom: 12px; display: inline-block; }
    .guide-box { color: #A1A1AA; font-size: 0.85rem; line-height: 1.6; padding: 20px; border-left: 3px solid #FF4D00; background: rgba(255, 77, 0, 0.05); }
    .guide-box b { color: #FF4D00 !important; font-size: 0.95rem; } 
    .delete-container { border: 1px solid #450a0a; padding: 20px; border-radius: 8px; background: #110303; margin-top: 40px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync
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
    if st.button("🔄 REFRESH DATASET"): st.cache_data.clear(); st.rerun()

# 5. Dashboard Tabs
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Session Configuration</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Duration (min)", 15, 180, 60, step=15)
    
    p1, p2, p3 = st.columns(3)
    f_wp, f_mp, f_cp = p1.number_input("Warm-up (W)", 100), p2.number_input("Target (W)", 140), p3.number_input("Cool-down (W)", 90)
    
    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry (5m Intervals)</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    hr_raw = str(s_data['전체심박데이터']) if s_data is not None else ""
    hr_list = [x.strip() for x in hr_raw.split(',') if x.strip()]
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            dv = int(float(hr_list[i])) if i < len(hr_list) else 130
            hv = st.number_input(f"T + {i*5}m", value=dv, key=f"hr_v96_{i}", step=1)
            hr_inputs.append(str(int(hv)))
    
    if st.button("COMMIT PERFORMANCE DATA", use_container_width=True):
        m_hrs = [int(x) for x in hr_inputs[2:-1]]; mid = len(m_hrs) // 2
        f_ef = f_mp / np.mean(m_hrs[:mid]) if mid > 0 else 0; s_ef = f_mp / np.mean(m_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
        conn.update(data=pd.concat([df[df["회차"] != f_session], pd.DataFrame([new])], ignore_index=True).sort_values("회차")); st.rerun()

    # 삭제 관리자 추가
    st.markdown('<div class="delete-container">', unsafe_allow_html=True)
    st.markdown('<p style="color:#ef4444; font-size:0.75rem; font-weight:600; text-transform:uppercase; margin-bottom:15px;">Data Management Zone</p>', unsafe_allow_html=True)
    dc1, dc2 = st.columns([3, 1])
    with dc1: del_session = st.selectbox("Select Session to Delete", sorted(df["회차"].unique().tolist(), reverse=True), key="del_box")
    with dc2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("DELETE NOW", use_container_width=True):
            conn.update(data=df[df["회차"] != del_session]); st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        c_p, c_dur, c_dec = int(s_data['본훈련파워']), int(s_data['본훈련시간']), s_data['디커플링(%)']
        
        # [HRR Analysis]
        hr_recovery = hr_array[-2] - hr_array[-1]
        hr_mid = np.mean(hr_array[2:len(hr_array)//2]); hr_end = np.mean(hr_array[len(hr_array)//2:-1])
        hr_drift = hr_end - hr_mid
        
        # [v9.6 Logic: 정합성 교정 버전]
        score = 0
        if c_dec < 6.0 or (c_dec < 7.5 and hr_drift < 3): score += 40
        if c_dur >= 90: score += 30; next_dur = 90
        elif c_dur >= 75: score += 20; next_dur = 90
        else: score += 10; next_dur = c_dur + 15
        if hr_recovery > 20: score += 30
        elif hr_recovery > 10: score += 15

        if score >= 70 and c_dur >= 90:
            next_step = f"Level Up to {c_p + 5}W / 60m"
            msg = f"90m Base Mastered! 강도를 {c_p+5}W로 상향하고, 시간을 60분으로 리셋하여 안정성을 확인하세요."
        elif score >= 50:
            next_step = f"Extend to {next_dur}m / {c_p}W"
            msg = f"안정적인 효율이 관찰됩니다. 현재 파워를 유지하며 시간을 {next_dur}분으로 늘려 유산소 기초를 다지세요."
        else:
            next_step = f"Consolidate {c_p}W / {c_dur}m"
            msg = "심박 표류가 기준치를 넘었습니다. 상향보다는 현재 조건에서의 안정화 수행이 우선입니다."

        st.markdown('<p class="section-title">AI Performance & HRR Analysis</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""<div class="briefing-card"><span class="prescription-badge">CURRENT RESULT</span>
            <p style="margin:0; font-weight:600;">Session {int(s_data['회차'])}: {c_p}W / {c_dur}m</p>
            <p style="margin:5px 0 0 0; color:#A1A1AA; font-size:0.9rem;">Decoupling: <b>{c_dec}%</b><br>HR Recovery: <b>{hr_recovery} bpm</b> (5m)</p></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="briefing-card" style="border-color: #FF4D00;"><span class="prescription-badge">NEXT PRESCRIPTION</span>
            <p style="margin:0; font-weight:600;">Target: {next_step}</p>
            <p style="margin:5px 0 0 0; color:#A1A1AA; font-size:0.9rem;">Note: {msg}</p></div>""", unsafe_allow_html=True)

        # [Power & HR Correlation Graph]
        st.markdown('<p class="section-title">Power & Heart Rate Correlation</p>', unsafe_allow_html=True)
        time_x = [i*5 for i in range(len(hr_array))]
        p_y = [int(s_data['웜업파워']) if t < 10 else (c_p if t < 10 + c_dur else int(s_data['쿨다운파워'])) for t in time_x]
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=time_x, y=p_y, name="Power", line=dict(color='#938172', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_x, y=hr_array, name="Heart Rate", line=dict(color='#F4F4F5', width=2, dash='dot')), secondary_y=True)
        fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, showlegend=False)
        fig1.layout.yaxis.update(title=dict(text="Power (W)", font=dict(color="#938172")), tickfont=dict(color="#938172"))
        fig1.layout.yaxis2.update(title=dict(text="HR (bpm)", font=dict(color="#F4F4F5")), tickfont=dict(color="#F4F4F5"), side="right", overlaying="y")
        st.plotly_chart(fig1, use_container_width=True)

        # [Efficiency Drift Analysis]
        st.markdown('<p class="section-title">Efficiency Drift Analysis</p>', unsafe_allow_html=True)
        ce1, ce2 = st.columns([3, 1])
        with ce1:
            ef_y = [round(c_p / h, 2) if h > 0 else 0 for h in hr_array]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=time_x[2:-1], y=ef_y[2:-1], line=dict(color='#FF4D00', width=3), fill='tozeroy', fillcolor='rgba(255, 77, 0, 0.05)'))
            fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig2, use_container_width=True)
        with ce2:
            st.markdown('<div class="guide-box"><b>Aerobic Stability</b><br><br>안정적인 구간은 수평선을 유지하며, 하향 곡선은 심박 표류(Drift)를 의미합니다.</div>', unsafe_allow_html=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">FTP 3.0W/kg Pursuit (Target 210W)</p>', unsafe_allow_html=True)
        curr_max = df['본훈련파워'].max(); progress = min(100, int((curr_max / 210) * 100))
        st.progress(progress / 100); st.write(f"Current Max: {int(curr_max)}W / Target: 210W ({progress}%)")
        
        st.markdown('<p class="section-title">Aerobic Efficiency (EF) Trend</p>', unsafe_allow_html=True)
        df['EF_Val'] = df.apply(lambda row: row['본훈련파워'] / np.mean([int(i) for i in str(row['전체심박데이터']).split(',')[2:-1]]) if len(str(row['전체심박데이터']).split(',')) > 3 else 0, axis=1)
        fig_ef = go.Figure()
        fig_ef.add_trace(go.Scatter(x=df['회차'], y=df['EF_Val'], mode='lines+markers', line=dict(color='#FF4D00', width=2)))
        fig_ef.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_ef, use_container_width=True)
