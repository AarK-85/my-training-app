import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Hyper-Aggressive Coach v9.993", layout="wide")

# 2. Styling (Perfect Black Theme)
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

# 4. Sidebar
with st.sidebar:
    st.markdown("<h2 style='color:#FF4D00; letter-spacing:0.1em;'>DYNAMIC COACH v9.993</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH DATASET"): st.cache_data.clear(); st.rerun()

tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Workout Mode Selection</p>', unsafe_allow_html=True)
    w_type = st.radio("SELECT TYPE", ["ZONE 2", "SST"], horizontal=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date, f_session = c1.date_input("Date", value=datetime.now().date()), c2.number_input("Session No.", value=int(df["회차"].max()+1) if not df.empty else 1)
    
    if w_type == "ZONE 2":
        f_duration = c3.slider("Duration (min)", 15, 180, 75, step=15)
        st.markdown('<p class="section-title">Zone 2 Aggressive Settings</p>', unsafe_allow_html=True)
        row = st.columns(3)
        f_wp = row[0].number_input("Warm-up (W)", min_value=50, value=97, step=1)
        f_mp = row[1].number_input("Target (W)", 145)
        f_cp = row[2].number_input("Cool-down (W)", 90)
        f_sst_p_data = f"Z2,{f_wp},{f_mp},{f_cp},0,0,0,0,0"
    else:
        st.markdown('<p class="section-title">SST Variable Interval Designer</p>', unsafe_allow_html=True)
        r1 = st.columns(5)
        f_sst_work, f_sst_rec, f_sst_sets, f_sst_work_t, f_sst_rec_t = r1[0].number_input("Steady-State Power (W)", 185), r1[1].number_input("Recovery Power (W)", 90), r1[2].number_input("Steady-State Sets", 2), r1[3].number_input("SS Time (min)", 10), r1[4].number_input("Recovery (min)", 5)
        r2 = st.columns(5)
        f_sst_w_s, f_sst_w_e, f_sst_c_s, f_sst_c_e = r2[0].number_input("WU Start (W)", 95), r2[1].number_input("WU End (W)", 110), r2[2].number_input("CD Start (W)", 100), r2[3].number_input("CD End (W)", 80)
        f_duration = 10 + (f_sst_sets * (f_sst_work_t + f_sst_rec_t)) + 20
        c3.info(f"Dynamic Duration: {f_duration} min"); f_mp = f_sst_work
        f_sst_p_data = f"SST,{f_sst_w_s},{f_sst_w_e},{f_sst_work},{f_sst_rec},{f_sst_c_s},{f_sst_c_e},{f_sst_sets},{f_sst_work_t},{f_sst_rec_t}"

    st.markdown('<p class="section-title">Heart Rate Data Entry (5-min intervals)</p>', unsafe_allow_html=True)
    total_pts = (f_duration // 5) + 1
    hr_inputs = []
    for r_idx in range((total_pts + 3) // 4):
        cols = st.columns(4)
        for c_idx in range(4):
            idx = r_idx * 4 + c_idx
            if idx < total_pts:
                with cols[c_idx]:
                    hv = st.number_input(f"T + {idx*5}m", value=130, key=f"hr_v9993_{idx}")
                    hr_inputs.append(str(int(hv)))
    
    if st.button("SUBMIT WORKOUT DATA"):
        m_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(m_hrs)//2
        f_ef = f_mp / np.mean(m_hrs[:mid]) if mid>0 else 0
        s_ef = f_mp / np.mean(m_hrs[mid:]) if mid>0 else 0
        new_row = {
            "날짜": f_date.strftime("%Y-%m-%d"),
            "회차": int(f_session),
            "훈련타입": w_type,
            "본훈련파워": int(f_mp),
            "본훈련시간": int(f_duration),
            "디커플링(%)": round(((f_ef-s_ef)/f_ef)*100,2) if f_ef>0 else 0,
            "전체심박데이터": ", ".join(hr_inputs),
            "파워데이터상세": f_sst_p_data
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        conn.update(data=df)
        st.cache_data.clear()
        st.success(f"Session {f_session} Recorded!")
        st.rerun()

# --- [TAB 2: PERFORMANCE (Aggressive Coach)] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        time_x = [i*5 for i in range(len(hr_array))]
        c_type, c_p, c_dur, c_dec = s_data['훈련타입'], int(s_data['본훈련파워']), int(s_data['본훈련시간']), s_data['디커플링(%)']

        # [Iron Logic v9.993]
        z2_df = df[df['훈련타입'] == "ZONE 2"].sort_values('회차')
        if not z2_df.empty:
            last_z2 = z2_df.iloc[-1]
            p_dec, p_p, p_dur = last_z2['디커플링(%)'], int(last_z2['본훈련파워']), int(last_z2['본훈련시간'])
            if p_dec < 6.5: # 공격적 상향 트리거
                n_pres, coach_msg = f"{p_p+5}W / {max(p_dur, 75)}m", f"디커플링 {p_dec}%! 바닥 공사 완료 판정. {p_p+5}W로 상향하여 180W 목표에 다가갑니다."
            else:
                n_pres, coach_msg = f"{p_p}W / {p_dur}m", "안정화 단계입니다. 6.5% 미만 달성까지 동일 파워에서 내실을 다지세요."
        else: n_pres, coach_msg = "145W / 75m", "첫 공격적 세션을 시작하세요."

        st.markdown('<p class="section-title">Aggressive Performance Briefing</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: st.markdown(f'<div class="briefing-card"><span class="prescription-badge">{c_type} RESULT</span><p style="font-size:1.5rem; font-weight:600; margin:0;">{c_p}W / {c_dur}m</p><p style="color:#A1A1AA;">Decoupling: <b>{c_dec}%</b></p></div>', unsafe_allow_html=True)
        with cb: st.markdown(f'<div class="briefing-card" style="border-color:#FF4D00;"><span class="prescription-badge">NEXT STEP</span><p style="font-size:1.5rem; font-weight:600; color:#FF4D00; margin:0;">{n_pres}</p><p style="margin-top:5px; font-size:0.9rem; color:#A1A1AA;">{coach_msg}</p></div>', unsafe_allow_html=True)

        # [Graphs with Black Theme]
        def update_black(fig):
            fig.update_layout(template="plotly_dark", plot_bgcolor='black', paper_bgcolor='black', xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'))
            return fig

        st.markdown('<p class="section-title">Efficiency Drift Visualization</p>', unsafe_allow_html=True)
        fig_corr = make_subplots(specs=[[{"secondary_y": True}]])
        # (파워 프로파일 계산 로직)
        p_raw = str(s_data['파워데이터상세']).split(',') if pd.notna(s_data['파워데이터상세']) and str(s_data['파워데이터상세'])!="" else []
        p_y = []
        if len(p_raw) > 0 and p_raw[0] == "SST":
            w_s, w_e, ss_p, rec_p, c_s, c_e, sets, ss_t, rec_t = [float(x) for x in p_raw[1:]]
            m_e = 10 + (sets * (ss_t + rec_t))
            for t in time_x:
                if t < 10: p_y.append(w_s + (w_e-w_s)*(t/10))
                elif t < m_e: p_y.append(ss_p if (t-10)%(ss_t+rec_t) < ss_t else rec_p)
                else: p_y.append(c_s - (c_s-c_e)*((t-m_e)/20))
        else: p_y = [c_p if 10 <= t <= 10+c_dur else 97 for t in time_x]

        fig_corr.add_trace(go.Scatter(x=time_x, y=p_y[:len(time_x)], name="Power", fill='tozeroy', line=dict(color='#FF4D00', width=3)), secondary_y=False)
        fig_corr.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#ffffff', dash='dot')), secondary_y=True)
        st.plotly_chart(update_black(fig_corr), use_container_width=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">W/kg Trend (85kg)</p>', unsafe_allow_html=True)
        fig_w = update_black(go.Figure(go.Scatter(x=df['회차'], y=df['본훈련파워']/85, mode='lines+markers', line=dict(color='#FF4D00'))))
        st.plotly_chart(fig_w, use_container_width=True)
