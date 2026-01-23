import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Hyper-Aggressive Coach v10.1", layout="wide")

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
    st.markdown("<h2 style='color:#FF4D00; letter-spacing:0.1em;'>3.0W/kg PROJECT</h2>", unsafe_allow_html=True)
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
        f_sst_work, f_sst_rec, f_sst_sets, f_sst_work_t, f_sst_rec_t = r1[0].number_input("SST Power (W)", 185), r1[1].number_input("Rec Power (W)", 90), r1[2].number_input("Sets", 2), r1[3].number_input("Work (m)", 15), r1[4].number_input("Rec (m)", 5)
        r2 = st.columns(4)
        f_sst_w_s, f_sst_w_e, f_sst_c_s, f_sst_c_e = r2[0].number_input("WU Start", 95), r2[1].number_input("WU End", 110), r2[2].number_input("CD Start", 100), r2[3].number_input("CD End", 80)
        f_duration = 10 + (f_sst_sets * (f_sst_work_t + f_sst_rec_t)) + 15
        f_mp = f_sst_work
        f_sst_p_data = f"SST,{f_sst_w_s},{f_sst_w_e},{f_sst_work},{f_sst_rec},{f_sst_c_s},{f_sst_c_e},{f_sst_sets},{f_sst_work_t},{f_sst_rec_t}"

    st.divider()
    total_pts = (f_duration // 5) + 1
    hr_inputs = []
    cols_hr = st.columns(4)
    for idx in range(total_pts):
        with cols_hr[idx % 4]:
            hv = st.number_input(f"T + {idx*5}m", value=130, key=f"hr_v101_{idx}")
            hr_inputs.append(str(int(hv)))
    
    if st.button("SUBMIT DATA"):
        h = [int(x) for x in hr_inputs]
        main_hr = h[2:-1]; mid = len(main_hr)//2
        f_ef = f_mp / np.mean(main_hr[:mid]) if mid>0 else 0; s_ef = f_mp / np.mean(main_hr[mid:]) if mid>0 else 0
        new_dec = round(((f_ef-s_ef)/f_ef)*100,2) if f_ef>0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "훈련타입": w_type, "본훈련파워": int(f_mp), "본훈련시간": int(f_duration), "디커플링(%)": new_dec, "전체심박데이터": ", ".join(hr_inputs), "파워데이터상세": f_sst_p_data}
        conn.update(data=pd.concat([df, pd.DataFrame([new])], ignore_index=True)); st.rerun()

# --- [TAB 2: PERFORMANCE (Restored V10.1 Engine)] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        time_x = [i*5 for i in range(len(hr_array))]
        c_type, c_p, c_dur, c_dec = s_data['훈련타입'], int(s_data['본훈련파워']), int(s_data['본훈련시간']), s_data['디커플링(%)']
        
        # [V10.1 Aggressive Logic]
        if c_type == "ZONE 2":
            if c_dec < 8.0: n_pres, coach_msg = f"{c_p+5}W", "8% 미만 성공. 즉시 +5W 상향합니다."
            elif c_dec > 10.0: n_pres, coach_msg = f"{c_p}W", "디커플링 과다. 강도 유지."
            else: n_pres, coach_msg = f"{c_p}W", "내실 다지는 중."
        else: # SST
            n_pres, coach_msg = f"{c_p+5}W", "인터벌 완수 확인. 무조건 상향합니다."

        st.markdown('<p class="section-title">Coaching Briefing</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: st.markdown(f'<div class="briefing-card"><span class="prescription-badge">{c_type} RESULT</span><p style="font-size:1.5rem; font-weight:600; margin:0;">{c_p}W / {c_dur}m</p><p style="color:#A1A1AA;">Decoupling: <b>{c_dec}%</b></p></div>', unsafe_allow_html=True)
        with cb: st.markdown(f'<div class="briefing-card" style="border-color:#FF4D00;"><span class="prescription-badge">NEXT STEP</span><p style="font-size:1.5rem; font-weight:600; color:#FF4D00; margin:0;">{n_pres}</p><p style="margin-top:5px; font-size:0.9rem;">{coach_msg}</p></div>', unsafe_allow_html=True)

        # [RESTORED: Power vs HR Correlation Graph]
        st.markdown('<p class="section-title">Correlation & Drift Analysis</p>', unsafe_allow_html=True)
        p_raw = str(s_data['파워데이터상세']).split(',') if pd.notna(s_data['파워데이터상세']) and str(s_data['파워데이터상세'])!="" else []
        p_y = []
        if len(p_raw) > 0 and p_raw[0] == "SST":
            w_s, w_e, ss_p, rec_p, c_s, c_e, sets, ss_t, rec_t = [float(x) for x in p_raw[1:]]
            m_end = 10 + (sets * (ss_t + rec_t))
            for t in time_x:
                if t < 10: p_y.append(w_s + (w_e-w_s)*(t/10))
                elif t < m_end: p_y.append(ss_p if (t-10)%(ss_t+rec_t) < ss_t else rec_p)
                else: p_y.append(c_s - (c_s-c_e)*((t-m_end)/15))
        else: p_y = [c_p if 10 <= t <= time_x[-1]-5 else 90 for t in time_x]

        fig_corr = make_subplots(specs=[[{"secondary_y": True}]])
        fig_corr.add_trace(go.Scatter(x=time_x, y=p_y[:len(time_x)], name="Power", fill='tozeroy', line=dict(color='#FF4D00', width=4)), secondary_y=False)
        fig_corr.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#F4F4F5', dash='dot')), secondary_y=True)
        update_fig_black(fig_corr).update_layout(height=450, showlegend=False, xaxis_title="Time (min)")
        fig_corr.update_yaxes(title_text="Power (W)", secondary_y=False)
        fig_corr.update_yaxes(title_text="HR (bpm)", secondary_y=True)
        st.plotly_chart(fig_corr, use_container_width=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">W/kg Track (Target 3.0)</p>', unsafe_allow_html=True)
        df['Wkg'] = df['본훈련파워'] / 85
        fig_wkg = go.Figure(go.Scatter(x=df['회차'], y=df['Wkg'], mode='lines+markers', line=dict(color='#FF4D00', width=2), fill='tozeroy'))
        fig_wkg.add_hline(y=3.0, line_dash="dash", line_color="white")
        update_fig_black(fig_wkg).update_layout(height=350, yaxis_range=[1.5, 3.5])
        st.plotly_chart(fig_wkg, use_container_width=True)
