import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Ultimate Profiler v9.85", layout="wide")

# 2. Styling (v9.1 Magma Aesthetic)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .stApp { background-color: #000000 !important; }
    [data-testid="stSidebar"] { background-color: #0c0c0e !important; }
    h1, h2, h3, p { color: #ffffff !important; font-family: 'Lexend', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #938172 !important; }
    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #938172; padding-left: 15px; }
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

# 4. Sidebar Archive
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em;'>ULTIMATE LAB v9.85</h2>", unsafe_allow_html=True)
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
    st.markdown('<p class="section-title">Workout Mode Selection</p>', unsafe_allow_html=True)
    w_type = st.radio("SELECT TYPE", ["ZONE 2", "SST"], horizontal=True)
    
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    
    if w_type == "ZONE 2":
        f_duration = c3.slider("Duration (min)", 15, 180, 60, step=15)
        st.markdown('<p class="section-title">Zone 2 Power Settings</p>', unsafe_allow_html=True)
        p1, p2, p3 = st.columns(3)
        f_wp, f_mp, f_cp = p1.number_input("Warm-up (W)", 100), p2.number_input("Main Target (W)", 140), p3.number_input("Cool-down (W)", 90)
        f_sst_p_data = f"Z2,{f_wp},{f_mp},{f_cp},0,0,0,0,0" 
    else:
        st.markdown('<p class="section-title">SST Variable Interval Designer</p>', unsafe_allow_html=True)
        # [디자인 수정: 5개씩 2행으로 완벽하게 정렬]
        row1 = st.columns(5)
        f_sst_work = row1[0].number_input("Steady-State Power (W)", 180)
        f_sst_rec = row1[1].number_input("Recovery Power (W)", 90)
        f_sst_sets = row1[2].number_input("Steady-State Sets", value=2, min_value=1)
        f_sst_work_t = row1[3].number_input("SS Time (min/set)", value=10)
        f_sst_rec_t = row1[4].number_input("Rec. Time (min/set)", value=5)
        
        row2 = st.columns(5)
        f_sst_w_s = row2[0].number_input("Warm-up Start (W)", 95)
        f_sst_w_e = row2[1].number_input("Warm-up End (W)", 110)
        f_sst_c_s = row2[2].number_input("Cool-down Start (W)", 100)
        f_sst_c_e = row2[3].number_input("Cool-down End (W)", 80)
        row2[4].empty() # 마지막 빈 칸을 명시적으로 비워서 정렬 유지
        
        f_duration = 10 + (f_sst_sets * (f_sst_work_t + f_sst_rec_t)) + 20
        c3.info(f"Dynamic Duration: {f_duration} min")
        f_mp = f_sst_work
        f_sst_p_data = f"SST,{f_sst_w_s},{f_sst_w_e},{f_sst_work},{f_sst_rec},{f_sst_c_s},{f_sst_c_e},{f_sst_sets},{f_sst_work_t},{f_sst_rec_t}"

    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry</p>', unsafe_allow_html=True)
    total_pts = (f_duration // 5) + 1
    hr_inputs = []
    for row_idx in range((total_pts + 3) // 4):
        cols = st.columns(4)
        for col_idx in range(4):
            idx = row_idx * 4 + col_idx
            if idx < total_pts:
                with cols[col_idx]:
                    hv = st.number_input(f"T + {idx*5}m", value=130, key=f"hr_v985_{idx}", step=1)
                    hr_inputs.append(str(int(hv)))
    
    if st.button("COMMIT WORKOUT DATA", use_container_width=True):
        m_hrs = [int(x) for x in hr_inputs[2:-1]]; mid = len(m_hrs) // 2
        f_ef = f_mp / np.mean(m_hrs[:mid]) if mid > 0 else 0; s_ef = f_mp / np.mean(m_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "훈련타입": w_type, "본훈련파워": int(f_mp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs), "파워데이터상세": f_sst_p_data}
        conn.update(data=pd.concat([df, pd.DataFrame([new])], ignore_index=True).sort_values("회차")); st.rerun()

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        c_p = int(s_data['본훈련파워'])
        p_raw = str(s_data['파워데이터상세']).split(',') if pd.notna(s_data['파워데이터상세']) and str(s_data['파워데이터상세']) != "" else []
        time_x = [i*5 for i in range(len(hr_array))]
        
        p_y = []
        if len(p_raw) > 0 and p_raw[0] == "SST":
            w_s, w_e, ss_p, rec_p, c_s, c_e, sets, ss_t, rec_t = [float(x) for x in p_raw[1:]]
            main_end_t = 10 + (sets * (ss_t + rec_t))
            for t in time_x:
                if t < 10: p_y.append(w_s + (w_e - w_s) * (t/10))
                elif t < main_end_t:
                    rel_t = t - 10
                    cycle = ss_t + rec_t
                    if rel_t % cycle < ss_t: p_y.append(ss_p)
                    else: p_y.append(rec_p)
                else: p_y.append(c_s - (c_s - c_e) * ((t-main_end_t)/20))
        else:
            p_wp = int(p_raw[1]) if len(p_raw) > 1 else 100
            p_mp = int(p_raw[2]) if len(p_raw) > 2 else c_p
            p_cp = int(p_raw[3]) if len(p_raw) > 3 else 90
            p_y = [p_wp if t < 10 else (p_mp if t < 10 + int(s_data['본훈련시간']) else p_cp) for t in time_x]

        st.markdown(f'<p class="section-title">{s_data["훈련타입"]} Steady-State Profile</p>', unsafe_allow_html=True)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=time_x, y=p_y[:len(time_x)], name="Target", line=dict(color='#938172', width=4), fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), secondary_y=False)
        fig.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#F4F4F5', width=2, dash='dot')), secondary_y=True)
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
