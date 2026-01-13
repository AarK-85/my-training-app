import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime # 오늘 날짜를 위한 모듈 추가

# Gemini 라이브러리 체크
try:
    import google.generativeai as genai
    gemini_installed = True
except ImportError:
    gemini_installed = False

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# --- [베이스 레퍼런스: 자동 모델 매칭 시스템] ---
gemini_ready = False
if gemini_installed:
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if 'models/gemini-1.5-flash' in models:
                target_model = 'models/gemini-1.5-flash'
            elif 'models/gemini-pro' in models:
                target_model = 'models/gemini-pro'
            else:
                target_model = models[0] if models else None
            
            if target_model:
                ai_model = genai.GenerativeModel(target_model)
                gemini_ready = True
        except: gemini_ready = False

# 스타일 정의
st.markdown("""
    <style>
    .main { background-color: #09090b; }
    div[data-testid="stMetricValue"] { color: #fafafa; font-size: 1.8rem; font-weight: 700; letter-spacing: -0.02em; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; background-color: #18181b; border-radius: 6px;
        border: 1px solid #27272a; color: #71717a; padding: 0px 20px; font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] { background-color: #27272a; color: #fff; border: 1px solid #3f3f46; }
    .section-title { color: #71717a; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 15px; letter-spacing: 0.1em; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 연결 및 전처리
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    if '회차' in df.columns:
        df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(0).astype(int)
    for col in ['웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간', '디커플링(%)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 3. 사이드바 (History)
with st.sidebar:
    st.markdown("### :material/search: History")
    if not df.empty:
        sessions = sorted(df["회차"].unique().astype(int).tolist(), reverse=True)
        selected_session = st.selectbox("Select Session", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None

# 4. 메인 화면 구성
tab_entry, tab_analysis, tab_trends = st.tabs([":material/add_circle: Session", ":material/analytics: Analysis", ":material/monitoring: Trends"])

# --- [TAB 1: 데이터 입력] ---
with tab_entry:
    st.markdown('<p class="section-title">Training Setup</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    
    # [수정] 날짜 기본값을 과거 데이터가 아닌 '오늘'로 설정
    f_date = c1.date_input("Date", value=datetime.now().date())
    
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Main Duration (min)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 60, step=5)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("Warmup (W)", value=int(s_data['웜업파워']) if s_data is not None else 100)
    f_mp = p2.number_input("Main (W)", value=int(s_data['본훈련파워']) if s_data is not None else 140)
    f_cp = p3.number_input("Cooldown (W)", value=int(s_data['쿨다운파워']) if s_data is not None else 90)

    st.divider()
    st.markdown(f'<p class="section-title">Heart Rate Entry (Every 5m)</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            def_hr = int(float(existing_hrs[i])) if i < len(existing_hrs) else 130
            time_val = i * 5
            label = f":material/timer: {time_val}m"
            hr_val = st.number_input(label, value=def_hr, key=f"hr_v4_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))

    if st.button("SAVE PERFORMANCE DATA", icon=":material/save:", use_container_width=True):
        main_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(main_hrs) // 2
        f_ef = f_mp / np.mean(main_hrs[:mid]) if mid > 0 else 0
        s_ef = f_mp / np.mean(main_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
        updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
        updated_df['회차'] = updated_df['회차'].astype(int)
        conn.update(data=updated_df); st.success("Record Saved."); st.rerun()

# --- [TAB 2 & 3 로직은 동일하게 유지됨] ---
# ... (Analysis 탭 및 Trends 탭 로직 생략, 기존 코드와 동일)
with tab_analysis:
    if s_data is not None:
        st.markdown(f"### :material/smart_toy: Session {int(s_data['회차'])} AI Briefing")
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        current_dec, current_p, current_dur = s_data['디커플링(%)'], int(s_data['본훈련파워']), int(s_data['본훈련시간'])
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Power Target", f"{current_p}W")
        m2.metric("Decoupling", f"{current_dec}%")
        m3.metric("Avg Heart Rate", f"{int(np.mean(hr_array[2:-1]))}bpm")
        m4.metric("Efficiency Factor", f"{round(current_p / np.mean(hr_array[2:-1]), 2)}")
        time_x = [i*5 for i in range(len(hr_array))]
        power_y = []
        for t in time_x:
            if t < 10: power_y.append(int(s_data['웜업파워']))
            elif t < 10 + current_dur: power_y.append(current_p)
            else: power_y.append(int(s_data['쿨다운파워']))
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=time_x, y=power_y, name="Power", line=dict(color='#3b82f6', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#ef4444', width=3, shape='spline')), secondary_y=True)
        fig1.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=20, b=10), hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown('<p class="section-title">Efficiency Factor Trend</p>', unsafe_allow_html=True)
        main_hr_only = hr_array[2:-1]
        ef_intervals = [round(current_p / np.mean(main_hr_only[i:i+3]), 2) for i in range(0, len(main_hr_only), 3) if len(main_hr_only[i:i+3]) > 0]
        fig2 = go.Figure(go.Bar(x=[f"{i*15}m" for i in range(len(ef_intervals))], y=ef_intervals, marker_color='#10b981', text=ef_intervals, textposition='auto'))
        fig2.update_layout(template="plotly_dark", height=250, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)
        st.divider()
        st.markdown("### :material/chat: Gemini Coach")
        if gemini_ready:
            if "messages" not in st.session_state: st.session_state.messages = []
            chat_box = st.container(height=300)
            with chat_box:
                for m in st.session_state.messages:
                    with st.chat_message(m["role"]): st.markdown(m["content"])
            if pr := st.chat_input("Ask about your performance..."):
                st.session_state.messages.append({"role": "user", "content": pr})
                with chat_box:
                    with st.chat_message("user"): st.markdown(pr)
                with st.spinner("Analyzing data..."):
                    try:
                        res = ai_model.generate_content(f"코치 분석: {int(s_data['회차'])}회차, 파워 {current_p}W, 디커플링 {current_dec}%. 질문: {pr}")
                        with chat_box:
                            with st.chat_message("assistant"):
                                st.markdown(res.text)
                                st.session_state.messages.append({"role": "assistant", "content": res.text})
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab_trends:
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'])
        col1, col2 = st.columns(2)
        with col1:
            weekly = df.set_index('날짜')['본훈련시간'].resample('W').sum().reset_index()
            st.plotly_chart(go.Figure(go.Bar(x=weekly['날짜'], y=weekly['본훈련시간'], marker_color='#8b5cf6')).update_layout(template="plotly_dark", title="Weekly Volume (min)", height=350), use_container_width=True)
        with col2:
            st.plotly_chart(go.Figure(go.Scatter(x=df['날짜'], y=df['디커플링(%)'], mode='lines+markers', line=dict(color='#f59e0b'))).update_layout(template="plotly_dark", title="Decoupling Trend (%)", height=350), use_container_width=True)
        st.markdown('<p class="section-title">Power Progression (Road to 160W)</p>', unsafe_allow_html=True)
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=df['날짜'], y=df['본훈련파워'], mode='lines+markers', fill='tozeroy', line=dict(color='#3b82f6')))
        fig5.add_hline(y=160, line_dash="dash", line_color="red", annotation_text="Goal 160W")
        fig5.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(fig5, use_container_width=True)
