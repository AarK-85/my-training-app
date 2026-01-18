import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Dual-Engine Lab v9.7", layout="wide")

# 2. Styling (v9.1 Magma Aesthetic)
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
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(0).astype(int)
    # 훈련타입 컬럼이 없을 경우 대비
    if '훈련타입' not in df.columns: df['훈련타입'] = 'ZONE 2'

# 4. Sidebar Archive
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em;'>DUAL-ENGINE LAB</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH DATASET"): st.cache_data.clear(); st.rerun()

# 5. Dashboard Tabs
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Workout Type Selection</p>', unsafe_allow_html=True)
    w_type = st.radio("SELECT TYPE", ["ZONE 2", "SST"], horizontal=True)
    
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Main Set Duration (min)", 15, 180, 60, step=15)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("Warm-up (W)", 100)
    # SST일 경우 기본 타겟 파워를 높게 설정 (145~155W 예상)
    f_mp = p2.number_input("Target Power (W)", 140 if w_type == "ZONE 2" else 155)
    f_cp = p3.number_input("Cool-down (W)", 90)
    
    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry (5m Intervals)</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            hv = st.number_input(f"T + {i*5}m", value=130, key=f"hr_v97_{i}", step=1)
            hr_inputs.append(str(int(hv)))
    
    if st.button("COMMIT WORKOUT DATA", use_container_width=True):
        m_hrs = [int(x) for x in hr_inputs[2:-1]]; mid = len(m_hrs) // 2
        f_ef = f_mp / np.mean(m_hrs[:mid]) if mid > 0 else 0; s_ef = f_mp / np.mean(m_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "훈련타입": w_type, "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
        conn.update(data=pd.concat([df, pd.DataFrame([new])], ignore_index=True).sort_values("회차")); st.rerun()

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        c_type = s_data['훈련타입']
        c_p, c_dur, c_dec = int(s_data['본훈련파워']), int(s_data['본훈련시간']), s_data['디커플링(%)']
        hr_recovery = hr_array[-2] - hr_array[-1]

        st.markdown(f'<p class="section-title">{c_type} Performance Analysis</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        if c_type == "ZONE 2":
            # [v9.62 Zone 2 Logic]
            hr_drift = np.mean(hr_array[len(hr_array)//2:-1]) - np.mean(hr_array[2:len(hr_array)//2])
            score = 0
            if c_dec < 6.0 or (c_dec < 7.5 and hr_drift < 3): score += 40
            if c_dur >= 90: score += 30; next_dur = 90
            elif c_dur >= 75: score += 20; next_dur = 90
            else: score += 10; next_dur = c_dur + 15
            if hr_recovery > 15: score += 30
            
            if score >= 70 and c_dur >= 90:
                next_step = f"{c_p + 5}W 상향 & 60m 리셋"
                msg = "90분 기초 완성! 강도를 높이고 시간을 60분으로 줄여 적응을 시작하세요."
            elif score >= 50:
                next_step = f"{next_dur}m로 시간 증강"
                msg = "효율이 좋습니다. 현재 파워를 유지하며 시간을 늘리세요."
            else:
                next_step = "현재 단계 유지 및 다지기"
                msg = "심박 불안정이 감지됩니다. 같은 조건에서 한 번 더 훈련하세요."
        else:
            # [SST Logic]
            avg_hr = np.mean(hr_array[2:-1])
            sst_ef = round(c_p / avg_hr, 2)
            next_step = f"SST 강도 유지 또는 +2W 상향"
            msg = f"SST 평균 효율: {sst_ef}. 근지구력 강화 세션입니다. 피로도가 높다면 1회 더 유지하세요."

        with col1:
            st.markdown(f"""<div class="briefing-card"><span class="prescription-badge">{c_type} RESULT</span>
            <p style="margin:0; font-weight:600;">{c_p}W / {c_dur}m (Session {int(s_data['회차'])})</p>
            <p style="margin:5px 0 0 0; color:#A1A1AA; font-size:0.9rem;">Decoupling: <b>{c_dec}%</b><br>HR Recovery: <b>{hr_recovery} bpm</b></p></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="briefing-card" style="border-color: #FF4D00;"><span class="prescription-badge">COACHING</span>
            <p style="margin:0; font-weight:600;">Next: {next_step}</p>
            <p style="margin:5px 0 0 0; color:#A1A1AA; font-size:0.9rem;">{msg}</p></div>""", unsafe_allow_html=True)

        # Graph
        time_x = [i*5 for i in range(len(hr_array))]
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#F4F4F5', width=2)), secondary_y=True)
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350)
        st.plotly_chart(fig, use_container_width=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">Road to FTP 3.0W/kg (Target Z2 180W)</p>', unsafe_allow_html=True)
        z2_max = df[df['훈련타입']=='ZONE 2']['본훈련파워'].max() if not df[df['훈련타입']=='ZONE 2'].empty else 0
        progress = min(100, int((z2_max / 180) * 100))
        st.progress(progress / 100)
        st.write(f"Current Max Zone 2: {int(z2_max)}W / Target: 180W ({progress}%)")
        
        st.markdown('<p class="section-title">Workout Distribution (Phase 2 Status)</p>', unsafe_allow_html=True)
        dist = df['훈련타입'].value_counts()
        fig_pie = go.Figure(data=[go.Pie(labels=dist.index, values=dist.values, hole=.3, marker_colors=['#938172', '#FF4D00'])])
        fig_pie.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)
