import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Gemini 라이브러리 임포트 시도
try:
    import google.generativeai as genai
    gemini_installed = True
except ImportError:
    gemini_installed = False

# 1. 페이지 설정 및 테마
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# --- [Gemini API 설정 및 보안 로직] ---
gemini_ready = False
if gemini_installed:
    if "GEMINI_API_KEY" in st.secrets:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            ai_model = genai.GenerativeModel('gemini-1.5-flash')
            gemini_ready = True
        except Exception:
            gemini_ready = False

# 스타일 정의 (Shadcn UI 느낌의 다크 테마)
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

# 2. 데이터 연결 및 전처리
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
    else:
        s_data = None

# 4. 메인 화면 구성 (탭)
tab_entry, tab_analysis, tab_trends = st.tabs(["🆕 New Session", "🎯 Analysis", "📈 Trends"])

# --- [TAB 1: 데이터 입력 (동적 UI)] ---
with tab_entry:
    st.markdown('<p class="section-title">Step 1: Training Setup</p>', unsafe_allow_html=True)
    
    # 상단 설정 바 (슬라이더 포함)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now().date())
    f_session = c2.number_input("회차", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    
    # 이 슬라이더를 움직이면 아래 입력칸이 즉시 변합니다.
    f_duration = c3.slider("본 훈련 시간(분) 설정", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 60, step=5)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("웜업 파워 (10분 고정)", value=int(s_data['웜업파워']) if s_data is not None else 100)
    f_mp = p2.number_input("본훈련 파워", value=int(s_data['본훈련파워']) if s_data is not None else 140)
    f_cp = p3.number_input("쿨다운 파워 (5분 고정)", value=int(s_data['쿨다운파워']) if s_data is not None else 90)

    st.divider()
    st.markdown(f'<p class="section-title">Step 2: Heart Rate Entry ({f_duration + 15}m Full Course)</p>', unsafe_allow_html=True)

    # 데이터 포인트 계산 (0분 포함 5분 단위)
    # 웜업(0,5,10) + 본훈련(15...종료) + 쿨다운(+5)
    total_points = ( (10 + f_duration + 5) // 5 ) + 1
    existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
    
    hr_inputs = []
    # 입력칸 그리드 배치 (4열)
    h_cols = st.columns(4)
    for i in range(total_points):
        t = i * 5
        if t <= 10: label = f"🟢 웜업 {t}m"
        elif t <= 10 + f_duration: label = f"🔵 본훈련 {t}m"
        else: label = f"⚪ 쿨다운 {t}m"
        
        try: def_val = int(float(existing_hrs[i].strip()))
        except: def_val = 130
            
        with h_cols[i % 4]:
            # key 값을 동적으로 생성하여 충돌 방지
            hr_val = st.number_input(label, value=def_val, key=f"hr_input_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 데이터 저장 버튼
    if st.button("🚀 SAVE TRAINING RECORD", use_container_width=True):
        # 디커플링 계산 (10분~종료시점 사이 데이터만 추출)
        main_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(main_hrs) // 2
        if len(main_hrs) >= 2:
            f_ef = f_mp / np.mean(main_hrs[:mid])
            s_ef = f_mp / np.mean(main_hrs[mid:])
            f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2)
        else:
            f_dec = 0

        new_row = {
            "날짜": f_date.strftime("%Y-%m-%d"), 
            "회차": int(f_session), 
            "웜업파워": int(f_wp), 
            "본훈련파워": int(f_mp), 
            "쿨다운파워": int(f_cp), 
            "본훈련시간": int(f_duration), 
            "디커플링(%)": f_dec, 
            "전체심박데이터": ", ".join(hr_inputs)
        }
        
        updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
        updated_df['날짜'] = updated_df['날짜'].astype(str)
        conn.update(data=updated_df)
        st.success("✅ 데이터가 성공적으로 저장되었습니다!")
        st.rerun()

# --- [TAB 2: 분석 및 Gemini 채팅] ---
with tab_analysis:
    if not df.empty and s_data is not None:
        st.markdown("### 🤖 AI Coach's Daily Briefing")
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        current_dec, current_p, current_dur = s_data['디커플링(%)'], int(s_data['본훈련파워']), int(s_data['본훈련시간'])
        max_hr = int(max(hr_array))

        # 메트릭 대시보드
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Target Power", f"{current_p}W")
        m2.metric("Decoupling", f"{current_dec}%", delta="- Stable" if current_dec <= 5.0 else "+ Check", delta_color="normal" if current_dec <= 8.0 else "inverse")
        m3.metric("Max HR", f"{max_hr}bpm")
        m4.metric("Volume", f"{current_dur}m")

        st.divider()

        # 수직 단계형 파워 그래프 로직
        time_x = [i*5 for i in range(len(hr_array))]
        power_y = []
        num_main_end = 2 + (current_dur // 5)
        for i in range(len(time_x)):
            if i < 2: power_y.append(int(s_data['웜업파워']))
            elif i < num_main_end: power_y.append(current_p)
            else: power_y.append(int(s_data['쿨다운파워']))
            
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        # Power (Step Line)
        fig1.add_trace(go.Scatter(x=time_x, y=power_y, name="Power", line=dict(color='#3b82f6', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'), secondary_y=False)
        # HR (Smooth Line)
        fig1.add_trace(go.Scatter(x=time_x, y=hr_array, name="HR", line=dict(color='#ef4444', width=3, shape='spline')), secondary_y=True)
        fig1.update_layout(template="plotly_dark", height=450, hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig1, use_container_width=True)

        st.divider()
        
        # 💬 Gemini AI 채팅 섹션
        st.markdown("### 💬 Chat with Gemini Coach")
        if not gemini_installed:
            st.error("`google-generativeai` 라이브러리가 설치되지 않았습니다. `requirements.txt`에 추가해 주세요.")
        elif not gemini_ready:
            st.warning("Streamlit Secrets에 `GEMINI_API_KEY`를 설정해 주세요.")
        else:
            if "messages" not in st.session_state:
                st.session_state.messages = []

            chat_container = st.container(height=300)
            with chat_container:
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

            if prompt := st.chat_input("오늘 훈련에 대해 물어보세요..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(prompt)

                # 데이터 맥락을 Gemini에게 제공
                context = f"""
                너는 사이클링 전문가 코치야. 다음 데이터를 바탕으로 분석해줘.
                회차: {s_data['회차']}, 파워: {current_p}W, 시간: {current_dur}분, 디커플링: {current_dec}%.
                사용자 질문: {prompt}
                """
                
                with chat_container:
                    with st.chat_message("assistant"):
                        response = ai_model.generate_content(context)
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- [TAB 3: 장기 트렌드] ---
with tab_trends:
    if not df.empty:
        # 효율 지수(EF) 및 회복 심박(HRR) 계산
        def safe_ef(r):
            try:
                hrs = [float(x.strip()) for x in str(r['전체심박데이터']).split(",")]
                main = hrs[2:-1]
                return int(r['본훈련파워']) / np.mean(main) if len(main) > 0 else 0
            except: return 0
        def safe_hrr(r):
            try:
                hrs = [float(x.strip()) for x in str(r['전체심박데이터']).split(",")]
                return int(hrs[-2] - hrs[-1]) if len(hrs) >= 2 else 0
            except: return 0

        df['EF'] = df.apply(safe_ef, axis=1)
        df['HRR'] = df.apply(safe_hrr, axis=1)
        
        # 주간 볼륨 계산
        df_vol = df.copy()
        df_vol['날짜'] = pd.to_datetime(df_vol['날짜'])
        weekly_v = df_vol.set_index('날짜')['본훈련시간'].resample('W').sum().reset_index()
        weekly_v['날짜'] = weekly_v['날짜'].dt.strftime('%m/%d')

        st.subheader(f"🏁 최종 목표(160W) 달성률: {min(int(s_data['본훈련파워'])/160*100, 100.0):.1f}%")
        st.progress(min(int(s_data['본훈련파워'])/160, 1.0))
        
        c_ef, c_hrr = st.columns(2)
        with c_ef:
            st.markdown("### Efficiency Index (EF)")
            st.plotly_chart(go.Figure(go.Scatter(x=df['회차'], y=df['EF'], mode='lines+markers', line=dict(color='#10b981', width=3))).update_layout(template="plotly_dark", height=300), use_container_width=True)
        with c_hrr:
            st.markdown("### HR Recovery (BPM)")
            st.plotly_chart(go.Figure(go.Bar(x=df['회차'], y=df['HRR'], marker_color='#f59e0b')).update_layout(template="plotly_dark", height=300), use_container_width=True)

        st.divider()
        st.markdown("### 📅 Weekly Training Volume")
        fig_vol = go.Figure(go.Bar(x=weekly_v['날짜'], y=weekly_v['본훈련시간'], text=(weekly_v['본훈련시간']/60).round(1), textposition='auto', marker_color='#8b5cf6'))
        fig_vol.update_layout(template="plotly_dark", height=350, yaxis_title="Minutes", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_vol, use_container_width=True)
