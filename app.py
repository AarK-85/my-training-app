import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Gemini 라이브러리 체크
try:
    import google.generativeai as genai
    gemini_installed = True
except ImportError:
    gemini_installed = False

# 1. 페이지 설정 및 다크 테마 적용
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# --- [Gemini API 설정] ---
gemini_ready = False
if gemini_installed:
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else 'models/gemini-pro'
            ai_model = genai.GenerativeModel(target_model)
            gemini_ready = True
        except: gemini_ready = False

st.markdown("""
    <style>
    .main { background-color: #09090b; }
    div[data-testid="stMetricValue"] { color: #fafafa; font-size: 1.8rem; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; background-color: #18181b; border-radius: 8px;
        border: 1px solid #27272a; color: #a1a1aa; padding: 0px 25px;
    }
    .stTabs [aria-selected="true"] { background-color: #27272a; color: #fff; border: 1px solid #3f3f46; }
    .stInfo, .stSuccess, .stWarning, .stError { border-radius: 12px; border: 1px solid #27272a; background-color: #18181b; }
    .section-title { color: #a1a1aa; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; margin-bottom: 12px; letter-spacing: 0.05em; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 연결 및 전처리 (정수형 강제 변환)
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
    st.markdown("### 🔍 History")
    if not df.empty:
        sessions = sorted(df["회차"].unique().astype(int).tolist(), reverse=True)
        selected_session = st.selectbox("조회할 회차", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else:
        s_data = None

# 4. 메인 화면 구성
tab_entry, tab_analysis, tab_trends = st.tabs(["🆕 New Session", "🎯 Analysis", "📈 Trends"])

# --- [TAB 1: 데이터 입력 (동적 UI)] ---
with tab_entry:
    st.markdown('<p class="section-title">Step 1: Training Setup</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now().date())
    next_session = int(df["회차"].max() + 1) if not df.empty else 1
    f_session = c2.number_input("회차", value=next_session, step=1)
    f_duration = c3.slider("본 훈련 시간(분) 설정", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 60, step=5)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("웜업 파워", value=int(s_data['웜업파워']) if s_data is not None else 100)
    f_mp = p2.number_input("본훈련 파워", value=int(s_data['본훈련파워']) if s_data is not None else 140)
    f_cp = p3.number_input("쿨다운 파워", value=int(s_data['쿨다운파워']) if s_data is not None else 90)

    st.divider()
    st.markdown(f'<p class="section-title">Step 2: Heart Rate Entry</p>', unsafe_allow_html=True)
    total_points = ((10 + f_duration + 5) // 5) + 1
    existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
    
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_points):
        with h_cols[i % 4]:
            def_val = 130
            if i < len(existing_hrs):
                try: def_val = int(float(existing_hrs[i]))
                except: pass
            hr_val = st.number_input(f"{i*5}m 심박", value=def_val, key=f"hr_input_step_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))

    if st.button("🚀 SAVE TRAINING RECORD", width='stretch'):
        main_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(main_hrs) // 2
        f_ef = f_mp / np.mean(main_hrs[:mid]) if mid > 0 else 0
        s_ef = f_mp / np.mean(main_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0

        new_row = {
            "날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), 
            "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), 
            "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)
        }
        updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
        updated_df['날짜'] = updated_df['날짜'].astype(str)
        updated_df['회차'] = updated_df['회차'].astype(int)
        conn.update(data=updated_df)
        st.success(f"{int(f_session)}회차 데이터 저장 성공!")
        st.rerun()

# --- [TAB 2: 분석 (정밀 그래프 복구)] ---
with tab_analysis:
    if s_data is not None:
        st.markdown(f"### 🤖 Session {int(s_data['회차'])} AI Briefing")
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        current_dec = s_data['디커플링(%)']
        current_p = int(s_data['본훈련파워'])
        current_dur = int(s_data['본훈련시간'])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Power", f"{current_p}W")
        m2.metric("Decoupling", f"{current_dec}%")
        m3.metric("Avg HR (Main)", f"{int(np.mean(hr_array[2:-1]))}bpm")
        m4.metric("EF", f"{round(current_p / np.mean(hr_array[2:-1]), 2)}")

        # [수정] 파워 수직 낙하 시점 정밀 계산 로직
        time_x = [i*5 for i in range(len(hr_array))]
        power_y = []
        for t in time_x:
            if t < 10: power_y.append(int(s_data['웜업파워']))
            elif t <= 10 + current_dur: power_y.append(current_p)
            else: power_y.append(int(s_data['쿨다운파워']))
        
        # 메인 분석 그래프 (심박 + 파워)
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        # shape='hv'를 통해 T=70분에서 즉시 수직으로 떨어지도록 보장
        fig1.add_trace(go.Scatter(x=time_x, y=power_y, name="Power", line=dict(color='#3b82f6', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#ef4444', width=3, shape='spline')), secondary_y=True)
        fig1.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified")
        st.plotly_chart(fig1, width='stretch')

        # [복구] 15분 단위 EF 분석 그래프
        st.markdown('<p class="section-title">Efficiency Factor Analysis (Every 15m)</p>', unsafe_allow_html=True)
        main_hr_only = hr_array[2:-1]
        ef_intervals = [round(current_p / np.mean(main_hr_only[i:i+3]), 2) for i in range(0, len(main_hr_only), 3) if len(main_hr_only[i:i+3]) > 0]
        fig2 = go.Figure(go.Bar(x=[f"{i*15}~{(i+1)*15}m" for i in range(len(ef_intervals))], y=ef_intervals, marker_color='#10b981', text=ef_intervals, textposition='auto'))
        fig2.update_layout(template="plotly_dark", height=300, yaxis_range=[min(ef_intervals)-0.1, max(ef_intervals)+0.1], margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig2, width='stretch')

        st.divider()
        # [연동] Gemini 채팅
        if gemini_ready:
            st.markdown("### 💬 Chat with Gemini Coach")
            if "messages" not in st.session_state: st.session_state.messages = []
            chat_container = st.container(height=300)
            with chat_container:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
            if pr := st.chat_input("Ask Coach..."):
                st.session_state.messages.append({"role": "user", "content": pr})
                with chat_container:
                    with st.chat_message("user"): st.markdown(pr)
                res = ai_model.generate_content(f"코치 답변: {int(s_data['회차'])}회차, 파워 {current_p}W, 디커플링 {current_dec}%. 질문: {pr}")
                with chat_container:
                    with st.chat_message("assistant"):
                        st.markdown(res.text)
                        st.session_state.messages.append({"role": "assistant", "content": res.text})

# --- [TAB 3: 트렌드 분석 복구] ---
with tab_trends:
    if not df.empty:
        col1, col2 = st.columns(2)
        df['날짜'] = pd.to_datetime(df['날짜'])
        
        # 1. 위클리 볼륨 트렌드
        weekly = df.set_index('날짜')['본훈련시간'].resample('W').sum().reset_index()
        with col1:
            fig3 = go.Figure(go.Bar(x=weekly['날짜'], y=weekly['본훈련시간'], marker_color='#8b5cf6', text=(weekly['본훈련시간']/60).round(1), textposition='auto'))
            fig3.update_layout(template="plotly_dark", title="Weekly Volume (min)", height=350, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig3, width='stretch')
        
        # 2. 디커플링 트렌드 (%)
        with col2:
            fig4 = go.Figure(go.Scatter(x=df['날짜'], y=df['디커플링(%)'], mode='lines+markers', line=dict(color='#f59e0b', width=3)))
            fig4.update_layout(template="plotly_dark", title="Decoupling Trend (%)", height=350, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig4, width='stretch')
            
        # 3. 로드 투 160W 파워 발전 추이
        st.markdown('<p class="section-title">Power Progression (Road to 160W)</p>', unsafe_allow_html=True)
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=df['날짜'], y=df['본훈련파워'], name="Actual Power", mode='lines+markers', line=dict(color='#3b82f6'), fill='tozeroy'))
        fig5.add_hline(y=160, line_dash="dash", line_color="red", annotation_text="Goal 160W", annotation_position="top left")
        fig5.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig5, width='stretch')
