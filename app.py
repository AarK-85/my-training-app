import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# --- [Data Loading: Optimized] ---
@st.cache_data(ttl=60)
def load_data(_conn):
    try:
        df = _conn.read(ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
        df = df.dropna(subset=['날짜'])
        num_cols = ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간', '디커플링(%)']
        for col in num_cols:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df['회차'] = df['회차'].astype(int)
        return df.sort_values("회차", ascending=False)
    except: return pd.DataFrame()

# 2. Gemini API
gemini_ready = False
try:
    import google.generativeai as genai
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        ai_model = genai.GenerativeModel('models/gemini-1.5-flash')
        gemini_ready = True
except: pass

# 3. Genesis Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Lexend:wght@500&display=swap');
    .main { background-color: #000000; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Inter', sans-serif; }
    div[data-testid="stMetricValue"] { color: #938172 !important; font-size: 2.2rem !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0c0c0e; padding: 10px; border-radius: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border-radius: 4px; color: #71717a; padding: 0 20px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #938172 !important; }
    .summary-box { background-color: #0c0c0e; border: 1px solid #1c1c1f; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
    .section-title { color: #938172; font-size: 0.8rem; text-transform: uppercase; border-left: 3px solid #938172; padding-left: 10px; margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

# 4. Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = load_data(conn)

# 5. Sidebar
with st.sidebar:
    st.markdown("### ZONE 2 LAB")
    if not df.empty:
        s_list = df["회차"].tolist()
        selected_s = st.selectbox("ARCHIVE", s_list, index=0)
        s_data = df[df["회차"] == selected_s].iloc[0].to_dict()
    else: s_data = None
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# 6. Tabs
t1, t2, t3 = st.tabs(["[ ENTRY ]", "[ PERFORMANCE ]", "[ PROGRESS ]"])

# --- [TAB 1: ENTRY] ---
with t1:
    st.markdown('<p class="section-title">Session Setup</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max()+1) if not df.empty else 1)
    f_duration = c3.slider("Main Training Duration (min)", 15, 180, 60)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("Warm-up (W)", 100)
    f_mp = p2.number_input("Target Main (W)", 140)
    f_cp = p3.number_input("Cool-down (W)", 90)

    st.divider()
    total_pts = ((10 + f_duration + 5) // 5) + 1
    hr_raw = str(s_data.get('전체심박데이터', '')) if s_data else ''
    hr_list = [x.strip() for x in hr_raw.split(',') if x.strip()]
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            dv = int(float(hr_list[i])) if i < len(hr_list) else 130
            hr_inp = st.number_input(f"T+{i*5}m", value=dv, key=f"v87_{i}")
            hr_inputs.append(str(int(hr_inp)))

    if st.button("COMMIT DATA", use_container_width=True):
        m_hr = [int(x) for x in hr_inputs[2:-1]]
        mid = len(m_hr) // 2
        f_ef = f_mp / np.mean(m_hr[:mid]) if mid > 0 else 0
        s_ef = f_mp / np.mean(m_hr[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
        conn.update(data=pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차"))
        st.cache_data.clear(); st.rerun()

# --- [TAB 2: PERFORMANCE] ---
with t2:
    if s_data:
        st.markdown(f"### Intelligence Briefing: Session {int(s_data['회차'])}")
        c_dec, c_p = float(s_data['디커플링(%)']), int(s_data['본훈련파워'])
        hr_array = [int(float(x)) for x in str(s_data['전체심박데이터']).split(',') if x.strip()]
        avg_ef = round(c_p / np.mean(hr_array[2:-1]), 2)
        
        st.markdown(f'<div class="summary-box">Efficiency: {avg_ef} EF | Stability: {c_dec}%</div>', unsafe_allow_html=True)

        # [ULTIMATE FIX: NO update_yaxes, NO secondary_y]
        time_x = [i*5 for i in range(len(hr_array))]
        p_y = [int(s_data['웜업파워']) if t < 10 else (c_p if t < 10 + int(s_data['본훈련시간']) else int(s_data['쿨다운파워'])) for t in time_x]
        ef_y = [round(p/h, 2) if h > 0 else 0 for p, h in zip(p_y, hr_array)]

        # 단순히 3개의 독립된 그래프를 생성하여 충돌 가능성 원천 차단
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                            subplot_titles=("POWER (W)", "HEART RATE (BPM)", "EFFICIENCY (EF)"))

        fig.add_trace(go.Scatter(x=time_x, y=p_y, name="Power", line=dict(color='#938172', width=3, shape='hv')), row=1, col=1)
        fig.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#F4F4F5', width=2, dash='dot')), row=2, col=1)
        fig.add_trace(go.Scatter(x=time_x[2:-1], y=ef_y[2:-1], name="EF", line=dict(color='#FF4D00', width=3)), row=3, col=1)

        # 에러 방지: layout 속성을 한꺼번에 대입
        fig.update_layout(template="plotly_dark", height=800, showlegend=False, 
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          margin=dict(l=50, r=20, t=50, b=50))
        
        # 개별 축의 이름만 조심스럽게 할당
        fig.layout.yaxis.title = "Power"
        fig.layout.yaxis2.title = "HR"
        fig.layout.yaxis3.title = "EF"
        fig.layout.xaxis3.title = "Time (min)"
        
        st.plotly_chart(fig, use_container_width=True)

        if gemini_ready:
            st.divider()
            if pr := st.chat_input("Ask Coach..."):
                with st.spinner("Analyzing..."):
                    res = ai_model.generate_content(f"Analyze Session {int(s_data['회차'])}, {c_p}W, {c_dec}% Decoupling. User: {pr}")
                    st.info(res.text)

# --- [TAB 3: PROGRESS] ---
with t3:
    if not df.empty:
        st.markdown('<p class="section-title">Stability Trend</p>', unsafe_allow_html=True)
        f3 = go.Figure(go.Scatter(x=df['날짜'], y=df['디커플링(%)'], line=dict(color='#FF4D00')))
        f3.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(f3, use_container_width=True)
