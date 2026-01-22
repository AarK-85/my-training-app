import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="FTP 3.0W/kg Goal Tracker", layout="wide")

# 2. Styling (Perfect Black Theme)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .stApp { background-color: #000000 !important; }
    [data-testid="stSidebar"] { background-color: #0c0c0e !important; }
    h1, h2, h3, p { color: #ffffff !important; font-family: 'Lexend', sans-serif; }
    .stButton > button { background-color: #18181b !important; color: #ffffff !important; border: 1px solid #FF4D00 !important; border-radius: 8px !important; width: 100% !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; border: 1px solid #1c1c1f; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0px 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #FF4D00 !important; }
    .section-title { color: #FF4D00; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; border-left: 3px solid #FF4D00; padding-left: 15px; }
    .briefing-card { border: 1px solid #27272a; padding: 22px; border-radius: 12px; background: #0c0c0e; margin-top: 10px; min-height: 160px; border-left: 5px solid #FF4D00; }
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
    df = df.sort_values('회차')

# Sidebar & Helper
with st.sidebar:
    st.markdown("<h2 style='color:#FF4D00; letter-spacing:0.1em;'>3.0W/kg PROJECT</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()

def update_black(fig):
    fig.update_layout(
        template="plotly_dark", plot_bgcolor='black', paper_bgcolor='black',
        xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10))
    )
    return fig

tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] (완전 복구 유지) ---
with tab_entry:
    st.markdown('<p class="section-title">Workout Entry</p>', unsafe_allow_html=True)
    w_mode = st.radio("SELECT TYPE", ["ZONE 2", "SST"], horizontal=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date, f_session = c1.date_input("Date"), c2.number_input("No.", value=int(df["회차"].max()+1) if not df.empty else 1)
    
    if w_mode == "ZONE 2":
        f_main_dur = c3.slider("Main Set (min)", 15, 180, 75, step=15)
        r = st.columns(3)
        f_wp, f_mp, f_cp = r[0].number_input("Warm-up (W)", 97), r[1].number_input("Target (W)", 145), r[2].number_input("Cool-down (W)", 90)
        f_total_dur = 10 + f_main_dur + 5
        f_detail = f"Z2,{f_wp},{f_mp},{f_cp},0,0,0,0,0"
    else:
        r1 = st.columns(5)
        f_sst_work, f_sst_rec, f_sst_sets, f_sst_work_t, f_sst_rec_t = r1[0].number_input("Power", 185), r1[1].number_input("Rec", 90), r1[2].number_input("Sets", 2), r1[3].number_input("Work(m)", 10), r1[4].number_input("Rec(m)", 5)
        r2 = st.columns(4); f_sst_w_s, f_sst_w_e, f_sst_c_s, f_sst_c_e = r2[0].number_input("WU_S", 95), r2[1].number_input("WU_E", 110), r2[2].number_input("CD_S", 100), r2[3].number_input("CD_E", 80)
        f_total_dur = 10 + (f_sst_sets * (f_sst_work_t + f_sst_rec_t)) + 15 
        f_mp = f_sst_work; f_detail = f"SST,{f_sst_w_s},{f_sst_w_e},{f_sst_work},{f_sst_rec},{f_sst_c_s},{f_sst_c_e},{f_sst_sets},{f_sst_work_t},{f_sst_rec_t}"

    total_pts = (f_total_dur // 5) + 1
    hr_inputs = []
    st.markdown(f'<p class="section-title">HR Input ({f_total_dur}m)</p>', unsafe_allow_html=True)
    for r_idx in range((total_pts + 3) // 4):
        cols = st.columns(4)
        for c_idx in range(4):
            idx = r_idx * 4 + c_idx
            if idx < total_pts:
                with cols[c_idx]:
                    hv = st.number_input(f"T+{idx*5}m", value=130, key=f"hr_{idx}")
                    hr_inputs.append(str(int(hv)))
    
    if st.button("SUBMIT DATA"):
        m_hrs = [int(x) for x in hr_inputs[2:-1]]; mid = len(m_hrs)//2
        f_ef = f_mp / np.mean(m_hrs[:mid]) if mid>0 else 0; s_ef = f_mp / np.mean(m_hrs[mid:]) if mid>0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "훈련타입": w_mode, "본훈련파워": int(f_mp), "본훈련시간": int(f_total_dur-15), "디커플링(%)": round(((f_ef-s_ef)/f_ef)*100,2) if f_ef>0 else 0, "전체심박데이터": ", ".join(hr_inputs), "파워데이터상세": f_detail}
        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True); conn.update(data=df); st.cache_data.clear(); st.rerun()

# --- [TAB 2: PERFORMANCE] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        time_x = [i*5 for i in range(len(hr_array))]
        c_type, c_p, c_dur, c_dec = s_data['훈련타입'], int(s_data['본훈련파워']), int(s_data['본훈련시간']), s_data['디커플링(%)']
        
        # [Coaching Logic v9.992]
        if c_type == "ZONE 2":
            n_pres, coach_msg = (f"{c_p+5}W / {max(c_dur, 75)}m", f"디커플링 {c_dec}%로 8% 미만 '성공'. {c_p+5}W로 상향하세요.") if c_dec < 8.0 else (f"{c_p}W / {c_dur}m", "내실 다지기 필요. 동일 강도 유지.")
        else: n_pres, coach_msg = f"{c_p+5}W SST", "SST 완수 확인. 무조건 상향 원칙 적용."

        st.markdown('<p class="section-title">AI Performance Coaching</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: st.markdown(f'<div class="briefing-card"><span class="prescription-badge">{c_type} RESULT</span><p style="font-size:1.5rem; font-weight:600; margin:0;">{c_p}W / {c_dur}m</p><p style="color:#A1A1AA;">Decoupling: <b>{c_dec}%</b></p></div>', unsafe_allow_html=True)
        with cb: st.markdown(f'<div class="briefing-card" style="border-color:#FF4D00;"><span class="prescription-badge">NEXT STEP</span><p style="font-size:1.5rem; font-weight:600; color:#FF4D00; margin:0;">{n_pres}</p><p style="margin-top:5px; font-size:0.9rem; color:#A1A1AA;">{coach_msg}</p></div>', unsafe_allow_html=True)

        fig_corr = update_black(make_subplots(specs=[[{"secondary_y": True}]]))
        p_y = [c_p if 10 <= t <= 10+c_dur else 97 for t in time_x]
        fig_corr.add_trace(go.Scatter(x=time_x, y=p_y, name="Power(W)", fill='tozeroy', line=dict(color='#FF4D00', width=3)), secondary_y=False)
        fig_corr.add_trace(go.Scatter(x=time_x, y=hr_array, name="HeartRate(bpm)", line=dict(color='#ffffff', dash='dot')), secondary_y=True)
        st.plotly_chart(fig_corr, use_container_width=True)

# --- [TAB 3: PROGRESSION (Legend Fixed)] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">W/kg Track (Target 3.0)</p>', unsafe_allow_html=True)
        df['Wkg'] = df['본훈련파워'] / 85
        fig_w = update_black(go.Figure(go.Scatter(x=df['회차'], y=df['Wkg'], mode='lines+markers', name='Actual W/kg', line=dict(color='#FF4D00', width=3))))
        fig_w.add_hline(y=3.0, line_dash="dash", line_color="white", annotation_text="Goal 3.0W/kg")
        st.plotly_chart(fig_w, use_container_width=True)

        # EF Graph - Legend & Trace Name Fixed
        st.markdown('<p class="section-title">Aerobic Efficiency (EF) Trend</p>', unsafe_allow_html=True)
        def calc_ef(r):
            hrs = [int(x) for x in str(r['전체심박데이터']).split(',') if x.strip()]
            main = hrs[2:-1]
            return r['본훈련파워'] / np.mean(main) if main else 0
        df['EF'] = df.apply(calc_ef, axis=1)
        
        fig_ef = update_black(go.Figure())
        fig_ef.add_trace(go.Bar(x=df['회차'], y=df['EF'], name='EF Intensity (Bar)', marker_color='rgba(0, 255, 204, 0.2)'))
        fig_ef.add_trace(go.Scatter(x=df['회차'], y=df['EF'], mode='lines+markers', name='EF Trend (Line)', line=dict(color='#00FFCC', width=2)))
        fig_ef.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_ef, use_container_width=True)
