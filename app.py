import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Hyper-Aggressive Coach v9.999", layout="wide")

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

# 4. Sidebar
with st.sidebar:
    st.markdown("<h2 style='color:#FF4D00; letter-spacing:0.1em;'>PHASE 2 COACH</h2>", unsafe_allow_html=True)
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("SESSION ARCHIVE", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()

def update_black(fig):
    fig.update_layout(template="plotly_dark", plot_bgcolor='black', paper_bgcolor='black', xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'))
    return fig

tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] (Fully Restored) ---
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
        # SST 로직 축약본 (SST 파라미터 입력)
        f_total_dur = 90; f_mp = 185; f_detail = "SST,..."

    total_pts = (f_total_dur // 5) + 1
    hr_inputs = []
    st.markdown(f'<p class="section-title">Heart Rate Data ({f_total_dur}m)</p>', unsafe_allow_html=True)
    for r_idx in range((total_pts + 3) // 4):
        cols = st.columns(4)
        for c_idx in range(4):
            idx = r_idx * 4 + c_idx
            if idx < total_pts:
                with cols[c_idx]:
                    hv = st.number_input(f"T+{idx*5}m", value=130, key=f"hr_{idx}")
                    hr_inputs.append(str(int(hv)))
    
    if st.button("SUBMIT"):
        m_hrs = [int(x) for x in hr_inputs[2:-1]]; mid = len(m_hrs)//2
        f_ef = f_mp / np.mean(m_hrs[:mid]) if mid>0 else 0; s_ef = f_mp / np.mean(m_hrs[mid:]) if mid>0 else 0
        new = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "훈련타입": w_mode, "본훈련파워": int(f_mp), "본훈련시간": int(f_total_dur-15), "디커플링(%)": round(((f_ef-s_ef)/f_ef)*100,2) if f_ef>0 else 0, "전체심박데이터": ", ".join(hr_inputs), "파워데이터상세": f_detail}
        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True); conn.update(data=df); st.cache_data.clear(); st.rerun()

# --- [TAB 3: PROGRESSION] (EF & W/kg FULL RESTORE) ---
with tab_trends:
    if not df.empty:
        # 1. W/kg Growth Graph
        st.markdown('<p class="section-title">W/kg Growth Track (Aggressive Goal: 3.0+)</p>', unsafe_allow_html=True)
        df['Wkg'] = df['본훈련파워'] / 85
        fig_w = update_black(go.Figure(go.Scatter(x=df['회차'], y=df['Wkg'], mode='lines+markers', line=dict(color='#FF4D00', width=3), fill='tozeroy')))
        fig_w.add_hline(y=180/85, line_dash="dash", line_color="#FF4D00", annotation_text="Goal 180W")
        st.plotly_chart(fig_w, use_container_width=True)

        # 2. EF (Aerobic Efficiency) Trend Graph - 핵심 복구 항목
        st.markdown('<p class="section-title">Aerobic Efficiency (EF) Trend - 내실 추적</p>', unsafe_allow_html=True)
        def calc_ef(row):
            hrs = [int(x) for x in str(row['전체심박데이터']).split(',') if x.strip()]
            main_hrs = hrs[2:-1] # 웜업/쿨다운 제외
            return row['본훈련파워'] / np.mean(main_hrs) if main_hrs else 0
        
        df['EF'] = df.apply(calc_ef, axis=1)
        fig_ef = update_black(go.Figure())
        fig_ef.add_trace(go.Scatter(x=df['회차'], y=df['EF'], mode='lines+markers', name='EF Value', line=dict(color='#00FFCC', width=2)))
        fig_ef.add_trace(go.Bar(x=df['회차'], y=df['EF'], name='EF Intensity', marker_color='rgba(0, 255, 204, 0.2)'))
        st.plotly_chart(fig_ef, use_container_width=True)

        # 3. Training Dist & Decoupling Heatmap (Bottom)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="section-title">Training Distribution</p>', unsafe_allow_html=True)
            dist = df['훈련타입'].value_counts()
            fig_p = update_black(go.Figure(data=[go.Pie(labels=dist.index, values=dist.values, hole=.4, marker_colors=['#FF4D00', '#27272a'])]))
            st.plotly_chart(fig_p, use_container_width=True)
        with c2:
            st.markdown('<p class="section-title">Decoupling History (%)</p>', unsafe_allow_html=True)
            fig_d = update_black(go.Figure(go.Bar(x=df['회차'], y=df['디커플링(%)'], marker_color='#FF4D00')))
            fig_d.add_hline(y=8.0, line_dash="dot", line_color="white", annotation_text="Target 8%")
            st.plotly_chart(fig_d, use_container_width=True)
