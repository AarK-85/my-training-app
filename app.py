import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Ultimate Profiler v9.87", layout="wide")

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
    st.markdown("<h2 style='letter-spacing:0.1em;'>ANALYST LAB v9.87</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()

tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION (v9.85 GUI 유지)] ---
with tab_entry:
    st.markdown('<p class="section-title">Workout Mode Selection</p>', unsafe_allow_html=True)
    w_type = st.radio("SELECT TYPE", ["ZONE 2", "SST"], horizontal=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date, f_session = c1.date_input("Date"), c2.number_input("Session No.", value=int(df["회차"].max()+1) if not df.empty else 1)
    
    if w_type == "ZONE 2":
        f_duration = c3.slider("Duration (min)", 15, 180, 60, step=15)
        row = st.columns(3)
        f_wp, f_mp, f_cp = row[0].number_input("Warm-up (W)", 100), row[1].number_input("Target (W)", 140), row[2].number_input("Cool-down (W)", 90)
        f_sst_p_data = f"Z2,{f_wp},{f_mp},{f_cp},0,0,0,0,0"
    else:
        row1 = st.columns(5)
        f_sst_work, f_sst_rec, f_sst_sets, f_sst_work_t, f_sst_rec_t = row1[0].number_input("SS Power", 180), row1[1].number_input("Rec. Power", 90), row1[2].number_input("SS Sets", 2), row1[3].number_input("SS Time", 10), row1[4].number_input("Rec. Time", 5)
        row2 = st.columns(5)
        f_sst_w_s, f_sst_w_e, f_sst_c_s, f_sst_c_e = row2[0].number_input("Warm-up Power Start (W)", 95), row2[1].number_input("Warm-up Power End (W)", 110), row2[2].number_input("Cool-down Power Start (W)", 100), row2[3].number_input("Cool-down Power End (W)", 80)
        f_duration = 10 + (f_sst_sets * (f_sst_work_t + f_sst_rec_t)) + 20
        c3.info(f"Dynamic Duration: {f_duration} min"); f_mp = f_sst_work
        f_sst_p_data = f"SST,{f_sst_w_s},{f_sst_w_e},{f_sst_work},{f_sst_rec},{f_sst_c_s},{f_sst_c_e},{f_sst_sets},{f_sst_work_t},{f_sst_rec_t}"

    st.divider()
    total_pts = (f_duration // 5) + 1
    hr_inputs = []
    for row_idx in range((total_pts + 3) // 4):
        cols = st.columns(4)
        for col_idx in range(4):
            idx = row_idx * 4 + col_idx
            if idx < total_pts:
                with cols[col_idx]: hv = st.number_input(f"T + {idx*5}m", value=130, key=f"hr_v987_{idx}"); hr_inputs.append(str(int(hv)))
    
    if st.button("COMMIT DATA", use_container_width=True):
        m_hrs = [int(x) for x in hr_inputs[2:-1]]; mid = len(m_hrs)//2
        f_ef = f_mp / np.mean(m_hrs[:mid]) if mid>0 else 0; s_ef = f_mp / np.mean(m_hrs[mid:]) if mid>0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "훈련타입": w_type, "본훈련파워": int(f_mp), "본훈련시간": int(f_duration), "디커플링(%)": round(((f_ef-s_ef)/f_ef)*100,2) if f_ef>0 else 0, "전체심박데이터": ", ".join(hr_inputs), "파워데이터상세": f_sst_p_data}
        conn.update(data=pd.concat([df, pd.DataFrame([new])], ignore_index=True)); st.rerun()

# --- [TAB 2: PERFORMANCE (Labeling 보강)] ---
with tab_analysis:
    if s_data is not None:
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        time_x = [i*5 for i in range(len(hr_array))]
        
        p_raw = str(s_data['파워데이터상세']).split(',') if pd.notna(s_data['파워데이터상세']) and str(s_data['파워데이터상세'])!="" else []
        p_y = []
        if len(p_raw) > 0 and p_raw[0] == "SST":
            w_s, w_e, ss_p, rec_p, c_s, c_e, sets, ss_t, rec_t = [float(x) for x in p_raw[1:]]
            main_end = 10 + (sets * (ss_t + rec_t))
            for t in time_x:
                if t < 10: p_y.append(w_s + (w_e-w_s)*(t/10))
                elif t < main_end: p_y.append(ss_p if (t-10)%(ss_t+rec_t) < ss_t else rec_p)
                else: p_y.append(c_s - (c_s-c_e)*((t-main_end)/20))
        else: p_y = [int(s_data['본훈련파워']) if 10 <= t <= 10+int(s_data['본훈련시간']) else 90 for t in time_x]

        st.markdown('<p class="section-title">Session Heart Rate Recovery (HRR)</p>', unsafe_allow_html=True)
        fig_hrr = go.Figure()
        fig_hrr.add_trace(go.Scatter(x=time_x[-5:], y=hr_array[-5:], mode='lines+markers', line=dict(color='#FF4D00', width=3)))
        fig_hrr.update_layout(template="plotly_dark", height=250, margin=dict(l=0,r=0,t=10,b=30), 
                              xaxis_title="Time (min)", yaxis_title="Recovery HR (bpm)")
        st.plotly_chart(fig_hrr, use_container_width=True)

        st.markdown('<p class="section-title">Correlation & Efficiency Drift</p>', unsafe_allow_html=True)
        fig_corr = make_subplots(specs=[[{"secondary_y": True}]])
        fig_corr.add_trace(go.Scatter(x=time_x, y=p_y, name="Power", fill='tozeroy', line=dict(color='#938172', width=4)), secondary_y=False)
        fig_corr.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#F4F4F5', dash='dot')), secondary_y=True)
        fig_corr.update_layout(template="plotly_dark", height=400, showlegend=False,
                              xaxis_title="Elapsed Time (min)")
        fig_corr.update_yaxes(title_text="Power (W)", secondary_y=False, title_font=dict(color="#938172"))
        fig_corr.update_yaxes(title_text="Heart Rate (bpm)", secondary_y=True, title_font=dict(color="#F4F4F5"))
        st.plotly_chart(fig_corr, use_container_width=True)

# --- [TAB 3: PROGRESSION (Labeling 보강)] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">Power-to-Weight Ratio Growth (Target 3.0W/kg)</p>', unsafe_allow_html=True)
        df['Wkg'] = df['본훈련파워'] / 85
        fig_wkg = go.Figure()
        fig_wkg.add_trace(go.Scatter(x=df['회차'], y=df['Wkg'], mode='lines+markers', line=dict(color='#FF4D00', width=2), fill='tozeroy'))
        fig_wkg.add_hline(y=3.0, line_dash="dash", line_color="white")
        fig_wkg.update_layout(template="plotly_dark", height=300, yaxis_range=[1.5, 3.5],
                              xaxis_title="Session Number", yaxis_title="Power (W/kg)")
        st.plotly_chart(fig_wkg, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<p class="section-title">Aerobic Efficiency (EF) Trend</p>', unsafe_allow_html=True)
            df['EF'] = df.apply(lambda r: r['본훈련파워'] / np.mean([int(x) for x in str(r['전체심박데이터']).split(',')[2:-1]]), axis=1)
            fig_ef = go.Figure()
            fig_ef.add_trace(go.Scatter(x=df['회차'], y=df['EF'], mode='markers', marker=dict(size=10, color='#938172')))
            fig_ef.update_layout(template="plotly_dark", height=300,
                                  xaxis_title="Session Number", yaxis_title="Efficiency Factor (W/bpm)")
            st.plotly_chart(fig_ef, use_container_width=True)
        with col_b:
            st.markdown('<p class="section-title">Training Distribution</p>', unsafe_allow_html=True)
            dist = df['훈련타입'].value_counts()
            fig_pie = go.Figure(data=[go.Pie(labels=dist.index, values=dist.values, hole=.3, marker_colors=['#FF4D00','#938172'])])
            fig_pie.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
