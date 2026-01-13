import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Config
st.set_page_config(page_title="Zone 2 Lab v8.8", layout="wide")

# --- [Data Loading] ---
@st.cache_data(ttl=30)
def fetch_training_data(_conn):
    try:
        raw_df = _conn.read(ttl=0)
        if raw_df is None or raw_df.empty: return pd.DataFrame()
        # 데이터 정리
        raw_df['날짜'] = pd.to_datetime(raw_df['날짜'], errors='coerce').dt.date
        raw_df = raw_df.dropna(subset=['날짜'])
        for c in ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간', '디커플링(%)']:
            if c in raw_df.columns: raw_df[c] = pd.to_numeric(raw_df[c], errors='coerce').fillna(0)
        return raw_df.sort_values("회차", ascending=False)
    except: return pd.DataFrame()

# 2. Gemini
gemini_active = False
try:
    import google.generativeai as genai
    key = st.secrets.get("GEMINI_API_KEY")
    if key:
        genai.configure(api_key=key)
        gemini_bot = genai.GenerativeModel('models/gemini-1.5-flash')
        gemini_active = True
except: pass

# 3. Style (Genesis Design)
st.markdown("""
    <style>
    .main { background-color: #000000; }
    div[data-testid="stMetricValue"] { color: #938172 !important; font-size: 2.2rem !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0c0c0e; border-radius: 8px; }
    .stTabs [aria-selected="true"] { border: 1px solid #938172 !important; }
    .sum-box { background-color: #0c0c0e; border: 1px solid #1c1c1f; padding: 20px; border-radius: 8px; }
    .label { color: #938172; font-size: 0.8rem; text-transform: uppercase; border-left: 3px solid #938172; padding-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 4. Connection
gs_conn = st.connection("gsheets", type=GSheetsConnection)
df_main = fetch_training_data(gs_conn)

# 5. Sidebar
with st.sidebar:
    st.title("ZONE 2 LAB")
    if not df_main.empty:
        sel_s = st.selectbox("ARCHIVE", df_main["회차"].tolist())
        d = df_main[df_main["회차"] == sel_s].iloc[0].to_dict()
    else: d = None
    if st.button("Refresh Cloud"):
        st.cache_data.clear()
        st.rerun()

# 6. Content
t1, t2, t3 = st.tabs(["[ ENTRY ]", "[ PERFORMANCE ]", "[ PROGRESS ]"])

with t1:
    st.markdown('<p class="label">Setup Session</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,2])
    v_date = c1.date_input("Date", value=datetime.now().date())
    v_s_no = c2.number_input("Session", value=int(df_main["회차"].max()+1) if not df_main.empty else 1)
    v_dur = c3.slider("Main (min)", 15, 180, 60)
    
    p1, p2, p3 = st.columns(3)
    v_wp = p1.number_input("Warmup (W)", 100)
    v_mp = p2.number_input("Main (W)", 140)
    v_cp = p3.number_input("Cool (W)", 90)

    st.divider()
    pts = ((10 + v_dur + 5) // 5) + 1
    hr_str = str(d.get('전체심박데이터', '')) if d else ''
    hr_list = [x.strip() for x in hr_str.split(',') if x.strip()]
    hr_in = []
    h_cols = st.columns(4)
    for i in range(pts):
        with h_cols[i % 4]:
            val = int(float(hr_list[i])) if i < len(hr_list) else 130
            hr_v = st.number_input(f"T+{i*5}m", value=val, key=f"hr_88_{i}")
            hr_in.append(str(int(hr_v)))

    if st.button("SAVE TO CLOUD", use_container_width=True):
        m_h = [int(x) for x in hr_in[2:-1]]
        m_idx = len(m_h) // 2
        e1 = v_mp / np.mean(m_h[:m_idx]) if m_idx > 0 else 0
        e2 = v_mp / np.mean(m_h[m_idx:]) if m_idx > 0 else 0
        dec = round(((e1 - e2) / e1) * 100, 2) if e1 > 0 else 0
        new = {"날짜": v_date.strftime("%Y-%m-%d"), "회차": int(v_s_no), "웜업파워": int(v_wp), "본훈련파워": int(v_mp), "쿨다운파워": int(v_cp), "본훈련시간": int(v_dur), "디커플링(%)": dec, "전체심박데이터": ", ".join(hr_in)}
        gs_conn.update(data=pd.concat([df_main[df_main["회차"] != v_s_no], pd.DataFrame([new])], ignore_index=True))
        st.cache_data.clear(); st.rerun()

with t2:
    if d:
        st.markdown(f"### Performance Briefing: Session {int(d['회차'])}")
        dec_v, p_v = float(d['디커플링(%)']), int(d['본훈련파워'])
        hr_a = [int(float(x)) for x in str(d['전체심박데이터']).split(',') if x.strip()]
        ef_v = round(p_v / np.mean(hr_a[2:-1]), 2)
        
        st.markdown(f'<div class="sum-box">Stability: {dec_v}% | Efficiency: {ef_v}</div>', unsafe_allow_html=True)

        # [V8.8 FIX] 모든 update_yaxes 함수 삭제. 축 설정을 layout에서 직접 텍스트로 처리.
        t_x = [i*5 for i in range(len(hr_a))]
        p_data = [int(d['웜업파워']) if t < 10 else (p_v if t < 10 + int(d['본훈련시간']) else int(d['쿨다운파워'])) for t in t_x]
        e_data = [round(p/h, 2) if h > 0 else 0 for p, h in zip(p_data, hr_a)]

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                            subplot_titles=("POWER", "HEART RATE", "EFFICIENCY"))

        fig.add_trace(go.Scatter(x=t_x, y=p_data, name="P", line=dict(color='#938172', width=3)), row=1, col=1)
        fig.add_trace(go.Scatter(x=t_x, y=hr_a, name="H", line=dict(color='#F4F4F5', dash='dot')), row=2, col=1)
        fig.add_trace(go.Scatter(x=t_x[2:-1], y=e_data[2:-1], name="E", line=dict(color='#FF4D00')), row=3, col=1)

        # fig.update_yaxes 를 절대 쓰지 않음 (에러의 원천)
        fig.update_layout(template="plotly_dark", height=800, showlegend=False, 
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        # 텍스트로 축 이름 직접 주입 (가장 안전)
        fig['layout']['yaxis']['title'] = 'Power (W)'
        fig['layout']['yaxis2']['title'] = 'HR (bpm)'
        fig['layout']['yaxis3']['title'] = 'EF'
        fig['layout']['xaxis3']['title'] = 'Time (min)'
        
        st.plotly_chart(fig, use_container_width=True)

        if gemini_active:
            if q := st.chat_input("Ask Coach..."):
                with st.spinner("Analyzing..."):
                    res = gemini_bot.generate_content(f"Analyze: S{int(d['회차'])}, {p_v}W, {dec_v}%. User: {q}")
                    st.info(res.text)

with t3:
    if not df_main.empty:
        st.markdown('<p class="label">Stability Trend</p>', unsafe_allow_html=True)
        f3 = go.Figure(go.Scatter(x=df_main['날짜'], y=df_main['디커플링(%)'], line=dict(color='#FF4D00')))
        f3.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(f3, use_container_width=True)
