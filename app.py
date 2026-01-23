import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Hyper-Aggressive Coach v10.0", layout="wide")

# 2. Styling (Pure Black & Magma UI)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .stApp { background-color: #000000 !important; }
    [data-testid="stSidebar"] { background-color: #0c0c0e !important; }
    h1, h2, h3, p { color: #ffffff !important; font-family: 'Lexend', sans-serif; }
    
    .stButton > button {
        background-color: #18181b !important;
        color: #ffffff !important;
        border: 1px solid #FF4D00 !important;
        border-radius: 8px !important;
        width: 100% !important;
    }
    .stButton > button:hover { border-color: #ffffff !important; color: #FF4D00 !important; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #FF4D00 !important; }
    
    .section-title { color: #FF4D00; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #FF4D00; padding-left: 15px; }
    .briefing-card { border: 1px solid #27272a; padding: 22px; border-radius: 12px; background: #0c0c0e; margin-top: 10px; min-height: 180px; border-left: 5px solid #FF4D00; }
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

def update_fig_black(fig):
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#27272a', zerolinecolor='#27272a'),
        yaxis=dict(gridcolor='#27272a', zerolinecolor='#27272a')
    )
    return fig

# 4. Sidebar
with st.sidebar:
    st.markdown("<h2 style='color:#FF4D00; letter-spacing:0.1em;'>AGGR. COACH v10.0</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH DATASET"): st.cache_data.clear(); st.rerun()

tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Workout Entry</p>', unsafe_allow_html=True)
    w_type = st.radio("SELECT TYPE", ["ZONE 2", "SST"], horizontal=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date, f_session = c1.date_input("Date", value=datetime.now().date()), c2.number_input("Session No.", value=int(df["회차"].max()+1) if not df.empty else 1)
    
    if w_type == "ZONE 2":
        f_duration = c3.slider("Duration (min)", 15, 180, 75, step=15)
        row = st.columns(3)
        f_wp, f_mp, f_cp = row[0].number_input("Warm-up (W)", 100), row[1].number_input("Target (W)", 145), row[2].number_input("Cool-down (W)", 90)
        f_sst_p_data = f"Z2,{f_wp},{f_mp},{f_cp},0,0,0,0,0"
    else:
        r1 = st.columns(5)
        f_sst_work, f_sst_rec, f_sst_sets, f_sst_work_t, f_sst_rec_t = r1[0].number_input("SST Power (W)", 185), r1[1].number_input("Rec Power (W)", 90), r1[2].number_input("Sets", 2), r1[3].number_input("Work (m)", 10), r1[4].number_input("Rec (m)", 5)
        r2 = st.columns(4)
        f_sst_w_s, f_sst_w_e, f_sst_c_s, f_sst_c_e = r2[0].number_input("WU Start", 95), r2[1].number_input("WU End", 110), r2[2].number_input("CD Start", 100), r2[3].number_input("CD End", 80)
        f_duration = 10 + (f_sst_sets * (f_sst_work_t + f_sst_rec_t)) + 20
        f_mp = f_sst_work
        f_sst_p_data = f"SST,{f_sst_w_s},{f_sst_w_e},{f_sst_work},{f_sst_rec},{f_sst_c_s},{f_sst_c_e},{f_sst_sets},{f_sst_work_t},{f_sst_rec_t}"

    st.divider()
    total_pts = (f_duration // 5) + 1
    hr_inputs = []
    cols = st.columns(4)
    for idx in range(total_pts):
        with cols[idx % 4]:
            hv = st.number_input(f"T + {idx*5}m", value=130, key=f"hr_v10_{idx}")
            hr_inputs.append(str(int(hv)))
    
    # New V10 Meta: Cadence & Completion Check
    st.markdown('<p class="section-title">V10 Meta Data</p>', unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    f_cadence = m1.number_input("Avg Cadence (rpm)", value=85)
    f_completed = m2.checkbox("Interval Fully Completed (SST Only)", value=True)

    if st.button("SUBMIT DATA"):
        h = [int(x) for x in hr_inputs]
        main_hr = h[2:-1]; mid = len(main_hr)//2
        f_ef = f_mp / np.mean(main_hr[:mid]) if mid>0 else 0; s_ef = f_mp / np.mean(main_hr[mid:]) if mid>0 else 0
        dec = round(((f_ef-s_ef)/f_ef)*100,2) if f_ef>0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "훈련타입": w_type, "본훈련파워": int(f_mp), "본훈련시간": int(f_duration), "디커플링(%)": dec, "전체심박데이터": ", ".join(hr_inputs), "파워데이터상세": f_sst_p_data}
        conn.update(data=pd.concat([df, pd.DataFrame([new])], ignore_index=True)); st.rerun()

# --- [TAB 2: PERFORMANCE (V10 COACHING MODEL)] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        c_type, c_p, c_dur, c_dec = s_data['훈련타입'], int(s_data['본훈련파워']), int(s_data['본훈련시간']), s_data['디커플링(%)']
        
        # [V10 Aggressive Coaching Engine]
        is_high_drift = c_dec > 10.0
        # cadence_check는 메타데이터 확장이 필요하므로 여기서는 시뮬레이션
        is_low_cadence = False 

        if c_type == "ZONE 2":
            if c_dec < 8.0:
                n_pres, coach_msg = f"{c_p+5}W", f"디커플링 {c_dec}%로 8% 미만 달성. 지침에 따라 무조건 +5W 상향합니다. 내실은 실전에서 다집니다."
            elif is_high_drift:
                n_pres, coach_msg = f"{c_p}W", f"디커플링 {c_dec}%로 10% 초과. 유산소 베이스 한계점입니다. 현재 강도를 유지하며 안정화하세요."
            else:
                n_pres, coach_msg = f"{c_p}W", f"디커플링 {c_dec}%입니다. 8% 미만 진입 전까지 현재 파워를 유지합니다."
        
        else: # SST
            if not is_low_cadence: # 완수 여부 최우선
                n_pres, coach_msg = f"{c_p+5}W", "인터벌을 끝까지 밀어냈습니다. 완수가 최우선이므로 다음 세션 파워를 즉시 상향합니다."
            else:
                n_pres, coach_msg = f"{c_p}W", "케이던스 저하로 '밀어내기'가 불안정합니다. 동일 강도에서 인터벌 완수 능력을 보강하세요."

        st.markdown('<p class="section-title">V10 Coaching Briefing</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: st.markdown(f'<div class="briefing-card"><span class="prescription-badge">{c_type} RESULT</span><p style="font-size:1.5rem; font-weight:600; margin:0;">{c_p}W / {c_dur}m</p><p style="color:#A1A1AA;">Decoupling: <b>{c_dec}%</b></p></div>', unsafe_allow_html=True)
        with cb: st.markdown(f'<div class="briefing-card" style="border-color:#FF4D00;"><span class="prescription-badge">NEXT STEP (V10)</span><p style="font-size:1.5rem; font-weight:600; color:#FF4D00; margin:0;">{n_pres}</p><p style="margin-top:5px; font-size:0.9rem; color:#A1A1AA;">{coach_msg}</p></div>', unsafe_allow_html=True)

        # Correlation Graph
        time_x = [i*5 for i in range(len(hr_array))]
        fig_corr = make_subplots(specs=[[{"secondary_y": True}]])
        fig_corr.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#F4F4F5', dash='dot')), secondary_y=True)
        update_fig_black(fig_corr).update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_corr, use_container_width=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">W/kg Track (Goal 3.0)</p>', unsafe_allow_html=True)
        df['Wkg'] = df['본훈련파워'] / 85
        fig_wkg = go.Figure(go.Scatter(x=df['회차'], y=df['Wkg'], mode='lines+markers', line=dict(color='#FF4D00', width=2), fill='tozeroy'))
        fig_wkg.add_hline(y=3.0, line_dash="dash", line_color="white")
        update_fig_black(fig_wkg).update_layout(height=300)
        st.plotly_chart(fig_wkg, use_container_width=True)
