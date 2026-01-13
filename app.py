import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정 및 shadcn 스타일 테마 적용
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #09090b; }
    /* 카드 스타일 */
    .input-card {
        background-color: #18181b;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #27272a;
        margin-bottom: 20px;
    }
    .section-title {
        color: #a1a1aa;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 15px;
        letter-spacing: 0.05em;
    }
    /* 입력창 스타일 */
    .stNumberInput input, .stSelectbox div {
        background-color: #09090b !important;
        border: 1px solid #27272a !important;
        border-radius: 8px !important;
        color: #fafafa !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    for col in ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 3. 사이드바 (조회 전용으로 간소화)
with st.sidebar:
    st.markdown("### 🔍 History")
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("조회할 회차 선택", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    st.divider()
    st.caption("새로운 데이터를 입력하려면 우측 상단의 'Data Entry' 섹션을 이용하세요.")

# 4. 메인 화면 구성
st.title("Zone 2 Training Lab")

# [핵심] 입력 섹션 리디자인 - Expander를 활용한 깔끔한 UI
with st.expander("🆕 Data Entry & Record Update", expanded=False):
    st.markdown('<p class="section-title">Step 1: Session Information</p>', unsafe_allow_html=True)
    
    with st.form(key="modern_training_form"):
        # 섹션 1: 기본 정보 및 파워 설정
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        f_date = c1.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now())
        f_session = c2.number_input("회차", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
        f_duration = c3.slider("본 훈련(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 60, step=5)
        
        st.markdown('<p class="section-title">Step 2: Target Power (W)</p>', unsafe_allow_html=True)
        p1, p2, p3 = st.columns(3)
        f_wp = p1.number_input("Warmup", value=int(s_data['웜업파워']) if s_data is not None else 97, step=1)
        f_mp = p2.number_input("Main", value=int(s_data['본훈련파워']) if s_data is not None else 140, step=1)
        f_cp = p3.number_input("Cooldown", value=int(s_data['쿨다운파워']) if s_data is not None else 90, step=1)
        
        st.markdown('<p class="section-title">Step 3: Heart Rate Log (BPM)</p>', unsafe_allow_html=True)
        num_main = f_duration // 5
        total_steps = 2 + num_main + 1
        existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
        
        # 가로 4열 그리드 배치로 가독성 극대화
        hr_inputs = []
        h_cols = st.columns(4)
        for i in range(total_steps):
            time_label = f"{i*5}m"
            # 구간별 태그 표시 (WU, Main, CD)
            if i < 2: label = f"🟢 {time_label} (WU)"
            elif i < 2 + num_main: label = f"🔵 {time_label} (Main)"
            else: label = f"⚪ {time_label} (CD)"
            
            try: def_hr = int(float(existing_hrs[i].strip()))
            except: def_hr = 130
            
            with h_cols[i % 4]:
                hr_val = st.number_input(label, value=def_hr, key=f"hr_m_{i}", step=1)
                hr_inputs.append(str(int(hr_val)))
        
        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("🚀 RECORD SESSION", use_container_width=True)
        
        if submit:
            # 디커플링 계산 및 시트 저장 로직 (이전과 동일)
            main_hrs = [int(x) for x in hr_inputs[2:-1]]
            mid = len(main_hrs) // 2
            f_ef_val = f_mp / np.mean(main_hrs[:mid])
            s_ef_val = f_mp / np.mean(main_hrs[mid:])
            f_dec = round(((f_ef_val - s_ef_val) / f_ef_val) * 100, 2)
            new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
            updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
            conn.update(data=updated_df)
            st.rerun()

st.divider()

# 이후 분석 대시보드 (Tab 1, Tab 2) 로직...
