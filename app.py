import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정 및 데이터 연결
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 데이터 전처리 (정수화)
if not df.empty:
    for col in ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 2. 사이드바 (데이터 입력 및 수정)
with st.sidebar:
    st.header("⚙️ 훈련 데이터 관리")
    mode = st.radio("작업 선택", ["기존 기록 조회/수정", "🆕 새로운 회차 기록"])
    
    if mode == "기존 기록 조회/수정" and not df.empty:
        sessions = sorted(df["회차"].unique().tolist())
        selected_session = st.selectbox("회차 선택", sessions, index=len(sessions)-1)
        s_data = df[df["회차"] == selected_session].iloc[0]
        btn_label = "데이터 수정 및 저장"
    else:
        next_session = int(df["회차"].max() + 1) if not df.empty else 1
        s_data = None
        selected_session = next_session
        btn_label = "🚀 새로운 훈련 데이터 저장"

    with st.form(key="training_input_form"):
        st.subheader(f"📝 {int(selected_session)}회차 기록")
        f_date = st.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now())
        f_session = st.number_input("회차 번호", value=int(selected_session), step=1)
        
        c1, c2, c3 = st.columns(3)
        f_wp = c1.number_input("웜업W", value=int(s_data['웜업파워']) if s_data is not None else 97, step=1)
        f_mp = c2.number_input("본훈련W", value=int(s_data['본훈련파워']) if s_data is not None else 140, step=1)
        f_cp = c3.number_input("쿨다운W", value=int(s_data['쿨다운파워']) if s_data is not None else 90, step=1)
        
        f_duration = st.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 90, step=5)
        
        num_main = f_duration // 5
        total_steps = 2 + num_main + 1
        existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
        
        st.write(f"💓 심박수 입력 ({total_steps}개 지점)")
        hr_inputs = []
        h_cols = st.columns(3)
        for i in range(total_steps):
            try: def_hr = int(float(existing_hrs[i].strip()))
            except: def_hr = 130
            with h_cols[i % 3]:
                hr_val = st.number_input(f"{i*5}분", value=def_hr, key=f"hr_input_{i}", step=1)
                hr_inputs.append(str(int(hr_val)))
        
        if st.form_submit_button(btn_label):
            # ... 저장 로직 (이전과 동일)
            main_hrs = [int(x) for x in hr_inputs[2:-1]]
            mid = len(main_hrs) // 2
            f_ef_val = f_mp / np.mean(main_hrs[:mid])
            s_ef_val = f_mp / np.mean(main_hrs[mid:])
            f_dec = round(((f_ef_val - s_ef_val) / f_ef_val) * 100, 2)
            new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
            updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
            conn.update(data=updated_df)
            st.rerun()

# 4. 메인 분석 대시보드
if not df.empty and s_data is not None:
    st.title(f"📊 Session {int(s_data['회차'])} 분석 리포트")
    tab1, tab2 = st.tabs(["🎯 오늘의 훈련 분석", "📈 장기 성장 추이"])

    with tab1:
        # AI 코치 헤드라인 및 메트릭 (생략 방지 위해 유지)
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        time_array = [i*5 for i in range(len(hr_array))]
        current_dec = s_data['디커플링(%)']
        current_p = int(s_data['본훈련파워'])
        max_hr = int(max(hr_array))
        
        st.info(f"🤖 **AI 코치:** {'완벽한 제어 상태입니다! +5W 확장을 추천합니다.' if current_dec <= 5.0 else '적응이 좀 더 필요합니다.'}")
        
        # 그래프 1: 시퀀스 분석 (파워 어레이 로직 수정)
        wp, mp, cp = int(s_data['웜업파워']), int(s_data['본훈련파워']), int(s_data['쿨다운파워'])
        
        # --- [수정된 로직] 파워 어레이를 타임 어레이와 동일하게 생성 ---
        power_array = []
        num_main_end_idx = 2 + (int(s_data['본훈련시간']) // 5) # 17회차 기준 2+18 = 20 (100분 지점)
        for i in range(len(time_array)):
            if i < 2: power_array.append(wp)
            elif i < num_main_end_idx: power_array.append(mp)
            else: power_array.append(cp) # 100분 시점부터 마지막 105분까지 cp 유지

        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=time_array, y=power_array, name="Power", line=dict(color='cyan', width=3, shape='hv'), fill='tozeroy'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_array, y=hr_array, name="HR", line=dict(color='red', width=4, shape='spline')), secondary_y=True)
        
        m_end_time = int(s_data['본훈련시간']) + 10
        fig1.add_vrect(x0=0, x1=10, fillcolor="gray", opacity=0.1, annotation_text="WU")
        fig1.add_vrect(x0=10, x1=m_end_time, fillcolor="blue", opacity=0.05, annotation_text="Main")
        fig1.add_vrect(x0=m_end_time, x1=time_array[-1], fillcolor="gray", opacity=0.1, annotation_text="CD")
        fig1.update_layout(template="plotly_dark", height=450, hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        # 목표 달성률 및 장기 지표 (이전과 동일)
        # ... (EF, HRR 그래프 로직)
        st.subheader(f"🏁 최종 목표(160W) 달성률: {min(current_p/160*100, 100.0):.1f}%")
        st.progress(min(current_p / 160, 1.0))
