import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. Page Configuration
st.set_page_config(page_title="FTP 3.0 Project v9.995", layout="wide")

# 2. Styling (Perfect Black Theme & Compact GUI)
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
    .briefing-card { border: 1px solid #27272a; padding: 22px; border-radius: 12px; background: #0c0c0e; margin-top: 10px; height: 180px; border-left: 5px solid #FF4D00; }
    .prescription-badge { background-color: #FF4D00; color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-bottom: 12px; display: inline-block; }
    div[data-testid="stNumberInput"] label { font-size: 0.8rem !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. Data Sync
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(0).astype(int)
    df = df.sort_values('회차')

# 4. Sidebar Archive
with st.sidebar:
    st.markdown("<h2 style='color:#FF4D00; letter-spacing:0.1em;'>3.0 PROJECT</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()

def update_black(fig):
    fig.update_layout(template="plotly_dark", plot_bgcolor='black', paper_bgcolor='black', xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'), legend=dict(bgcolor='rgba(0,0,0,0)'))
    return fig

tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] (5.8% Logic Fixed & SST Data Format Fixed) ---
with tab_entry:
    w_mode = st.radio("TYPE", ["ZONE 2", "SST"], horizontal=True)
    c1, c2 = st.columns(2)
    f_date, f_session = c1.date_input("Date"), c2.number_input("No.", value=int(df["회차"].max()+1) if not df.empty else 1)
    
    if w_mode == "ZONE 2":
        r = st.columns(3)
        f_wp, f_mp, f_cp = r[0].number_input("WU (W)", 97), r[1].number_input("Target (W)", 145), r[2].number_input("CD (W)", 90)
        f_main_dur = st.slider("Main Set (min)", 15, 180, 75, step=15)
        f_total_dur = 10 + f_main_dur + 5
        f_detail = f"Z2,{f_wp},{f_mp},{f_cp},75,0" # Format match
    else:
        r1 = st.columns(3)
        f_sst_p, f_sst_t, f_sst_sets = r1[0].number_input("Work(W)", 185), r1[1].number_input("Time(m)", 15), r1[2].number_input("Sets", 2)
        r2 = st.columns(2)
        f_sst_rec_p, f_sst_rec_t = r2[0].number_input("Rec(W)", 90), r2[1].number_input("Time(m)", 5)
        f_total_dur = 10 + (f_sst_sets * (f_sst_t + f_sst_rec_t)) + 10
        f_mp = f_sst_p
        f_detail = f"SST,97,{f_sst_p},{f_sst_rec_p},{f_sst_sets},{f_sst_t},{f_sst_rec_t}"

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
    
    if st.button("SUBMIT"):
        h = [int(x) for x in hr_inputs]
        # [5.8% MATHEMATICS] 본세션 16개 정확히 이등분
        main_hr = h[2:18]
        mid = len(main_hr) // 2
        avg1, avg2 = sum(main_hr[:mid])/mid, sum(main_hr[mid:])/mid
        dec = round((( (f_mp/avg1) - (f_mp/avg2) ) / (f_mp/avg1)) * 100, 2)
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "훈련타입": w_mode, "본훈련파워": f_mp, "본훈련시간": f_total_dur-15, "디커플링(%)": dec, "전체심박데이터": ", ".join(hr_inputs), "파워데이터상세": f_detail}
        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True); conn.update(data=df); st.cache_data.clear(); st.rerun()

# --- [TAB 2: PERFORMANCE (Error Fixed)] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        time_x = [i*5 for i in range(len(hr_array))]
        c_p, c_dec, c_type = int(s_data['본훈련파워']), s_data['디커플링(%)'], s_data['훈련타입']
        
        n_pres, coach_msg = (f"{c_p+5}W SST", "완수 확인. 상향.") if c_type == "SST" else ((f"{c_p+5}W Z2", "8% 미만 성공!") if c_dec < 8.0 else (f"{c_p}W Z2", "내실 다지기."))

        st.markdown('<p class="section-title">Performance Briefing</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: st.markdown(f'<div class="briefing-card"><span class="prescription-badge">RESULT</span><p style="font-size:1.5rem; font-weight:600;">{c_p}W ({c_dec}%)</p></div>', unsafe_allow_html=True)
        with cb: st.markdown(f'<div class="briefing-card" style="border-color:#FF4D00;"><span class="prescription-badge">NEXT</span><p style="font-size:1.5rem; font-weight:600; color:#FF4D00;">{n_pres}</p><p>{coach_msg}</p></div>', unsafe_allow_html=True)

        fig_corr = update_black(make_subplots(specs=[[{"secondary_y": True}]]))
        p_raw = str(s_data['파워데이터상세']).split(',')
        if p_raw[0] == "SST" and len(p_raw) >= 7: # Safety Check
            wu_p, work_p, rec_p, sets, work_t, rec_t = [float(x) for x in p_raw[1:7]]
            p_y = [wu_p if t < 10 else (work_p if (t-10)%(work_t+rec_t) < work_t else rec_p) if t < 10 + sets*(work_t+rec_t) else 80 for t in time_x]
        else: p_y = [c_p if 10 <= t <= time_x[-1]-5 else 97 for t in time_x]
        
        fig_corr.add_trace(go.Scatter(x=time_x, y=p_y, name="Power", fill='tozeroy', line=dict(color='#FF4D00', width=3)), secondary_y=False)
        fig_corr.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#ffffff', dash='dot')), secondary_y=True)
        st.plotly_chart(fig_corr, use_container_width=True)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">W/kg Track (Target 3.0)</p>', unsafe_allow_html=True)
        fig_w = update_black(go.Figure(go.Scatter(x=df['회차'], y=df['본훈련파워']/85, mode='lines+markers', line=dict(color='#FF4D00', width=3), fill='tozeroy')))
        fig_w.add_hline(y=3.0, line_dash="dash", line_color="white", annotation_text="Goal 3.0")
        st.plotly_chart(fig_w, use_container_width=True)

        st.markdown('<p class="section-title">EF (Efficiency) Trend</p>', unsafe_allow_html=True)
        def get_ef(r):
            h = [int(x) for x in str(r['전체심박데이터']).split(',') if x.strip()]
            main = h[2:18]
            return r['본훈련파워'] / (sum(main)/len(main)) if main else 0
        df['EF'] = df.apply(get_ef, axis=1)
        fig_ef = update_black(go.Figure())
        fig_ef.add_trace(go.Bar(x=df['회차'], y=df['EF'], name='Intensity', marker_color='rgba(0, 255, 204, 0.2)'))
        fig_ef.add_trace(go.Scatter(x=df['회차'], y=df['EF'], name='Trend', line=dict(color='#00FFCC', width=2)))
        st.plotly_chart(fig_ef, use_container_width=True)
