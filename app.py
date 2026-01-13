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

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# --- [Gemini API 설정: 모델 호환성 강화] ---
gemini_ready = False
available_models = []
if gemini_installed:
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # 1단계: 사용 가능한 모델 리스트 가져오기 (디버깅용)
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 2단계: 가장 안정적인 gemini-pro 또는 리스트의 첫 번째 모델 선택
            target_model = 'models/gemini-pro' if 'models/gemini-pro' in available_models else available_models[0]
            
            ai_model = genai.GenerativeModel(target_model)
            gemini_ready = True
        except Exception as e:
            st.error(f"Gemini 초기화 오류: {e}")

# 스타일 정의
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

# 2. 데이터 연결 및 전처리 (생략 없이 전체 포함)
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    for col in ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 3. 사이드바 (History)
with st.sidebar:
    st.markdown("### 🔍 History")
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("조회할 회차", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else: s_data = None

# 4. 메인 화면 구성
tab_entry, tab_analysis, tab_trends = st.tabs(["🆕 New Session", "🎯 Analysis", "📈 Trends"])

# --- [TAB 1: 데이터 입력 (동적 UI)] ---
with tab_entry:
    st.markdown('<p class="section-title">Step 1: Training Setup</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now().date())
    f_session = c2.number_input("회차", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("본 훈련 시간(분) 설정", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 60, step=5)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("웜업 파워 (10분)", value=int(s_data['웜업파워']) if s_data is not None else 100)
    f_mp = p2.number_input("본훈련 파워", value=int(s_data['본훈련파워']) if s_data is not None else 140)
    f_cp = p3.number_input("쿨다운 파워 (5분)", value=int(s_data['쿨다운파워']) if s_data is not None else 90)

    st.divider()
    st.markdown(f'<p class="section-title">Step 2: Heart Rate Entry ({f_duration + 15}m Full Course)</p>', unsafe_allow_html=True)

    total_points = ( (10 + f_duration + 5) // 5 ) + 1
    existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
    
    hr_inputs = []
    h_cols = st.columns(4)
    for i in range(total_points):
        t = i * 5
        if t <= 10: label = f"🟢 웜업 {t}m"
        elif t <= 10 + f_duration: label = f"🔵 본훈련 {t}m"
        else: label = f"⚪ 쿨다운 {t}m"
        try: def_val = int(float(existing_hrs[i].strip()))
        except: def_val = 130
        with h_cols[i % 4]:
            hr_val = st.number_input(label, value=def_val, key=f"hr_input_point_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))

    if st.button("🚀 SAVE TRAINING RECORD", width='stretch'):
        main_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(main_hrs) // 2
        if len(main_hrs) >= 2:
            f_ef = f_mp / np.mean(main_hrs[:mid])
            s_ef = f_mp / np.mean(main_hrs[mid:])
            f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2)
        else: f_dec = 0
        new_row = {
            "날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), 
            "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), 
            "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)
        }
        updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
        updated_df['날짜'] = updated_df['날짜'].astype(str)
        conn.update(data=updated_df)
        st.success("데이터 저장 성공!")
        st.rerun()

# --- [TAB 2: 분석 및 Gemini 채팅] ---
with tab_analysis:
    if not df.empty and s_data is not None:
        # 데이터 요약 (메트릭/그래프 로직 유지)
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        current_dec, current_p, current_dur = s_data['디커플링(%)'], int(s_data['본훈련파워']), int(s_data['본훈련시간'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Target Power", f"{current_p}W")
        m2.metric("Decoupling", f"{current_dec}%")
        m3.metric("Volume", f"{current_dur}m")

        # 그래프 그리기
        time_x = [i*5 for i in range(len(hr_array))]
        power_y = [current_p] * len(time_x) # 단순화된 파워라인
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=time_x, y=power_y, name="Power", line=dict(color='#3b82f6', shape='hv')), secondary_y=False)
        fig.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#ef4444')), secondary_y=True)
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, width='stretch')

        st.divider()
        st.markdown("### 💬 Chat with Gemini Coach")
        
        if not gemini_ready:
            st.error("Gemini를 불러올 수 없습니다. API 키를 확인하세요.")
            if available_models: st.write(f"사용 가능 모델 리스트: {available_models}")
        else:
            if "messages" not in st.session_state: st.session_state.messages = []
            chat_container = st.container(height=350)
            with chat_container:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            if prompt := st.chat_input("질문을 입력하세요..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with chat_container:
                    with st.chat_message("user"): st.markdown(prompt)
                
                context = f"사이클링 코치로서 분석해줘. 파워:{current_p}W, 디커플링:{current_dec}%. 질문:{prompt}"
                with chat_container:
                    with st.chat_message("assistant"):
                        try:
                            response = ai_model.generate_content(context)
                            st.markdown(response.text)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                        except Exception as e:
                            st.error(f"응답 에러: {e}")
                            st.write(f"사용 중인 모델: {ai_model.model_name}")

# --- [TAB 3: 장기 트렌드] ---
with tab_trends:
    if not df.empty:
        st.info("트렌드 분석 데이터가 준비되었습니다.")
