import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Performance Pro", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 열 이름 정의
power_col, dec_col, session_col, hr_data_col = "평균 파워(W)", "디커플링(%)", "회차", "심박데이터"

# 3. 사이드바: 정밀 데이터 입력창
with st.sidebar:
    st.header("📝 훈련 세션 기록")
    with st.form(key="precision_form", clear_on_submit=True):
        date = st.date_input("날짜")
        last_s = int(df[session_col].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_s + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        
        st.divider()
        duration = st.number_input("본 훈련 시간(분)", value=60, step=5)
        avg_p = st.number_input("본 훈련 평균 파워(W)", value=135)
        user_dec = st.number_input("수동 기입 디커플링(%)", value=0.0, step=0.1)
        
        # --- 5분 단위 심박수 입력 칸 자동 생성 ---
        st.subheader("💓 5분 단위 심박수")
        num_inputs = (duration // 5) + 1
        hr_list_input = []
        
        # 3열 레이아웃으로 입력칸 배치 (공간 절약)
        cols = st.columns(3)
        for i in range(num_inputs):
            with cols[i % 3]:
                val = st.number_input(f"{i*5}분", value=130, key=f"hr_step_{i}")
                hr_list_input.append(val)
        
        notes = st.text_area("메모")

        if st.form_submit_button("데이터 저장 및 분석"):
            # 자동 디커플링 계산 로직
            mid = len(hr_list_input) // 2
            f_hr = np.mean(hr_list_input[:mid])
            s_hr = np.mean(hr_list_input[mid:])
            
            f_ef = avg_p / f_hr
            s_ef = avg_p / s_hr
            auto_dec = round(((f_ef - s_ef) / f_ef) * 100, 2)
            
            new_row = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"), "회차": session, "Phase": phase,
                "훈련 시간(분)": duration, "평균 파워(W)": avg_p,
                "디커플링(%)": auto_dec, "수동기입값": user_dec,
                "메모": notes, "심박데이터": ",".join(map(str, hr_list_input))
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"저장 완료! 자동 계산 디커플링: {auto_dec}%")
            st.rerun()

# 4. 메인 대시보드
if not df.empty:
    st.title("🚴 Zone 2 Training Intelligence")
    
    # 상단 요약
    latest = df.iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("최근 파워", f"{latest[power_col]} W")
    c2.metric("디커플링 (앱 계산)", f"{latest[dec_col]} %")
    
    # 검증 로직
    if "수동기입값" in latest and latest["수동기입값"] > 0:
        diff = abs(latest[dec_col] - latest["수동기입값"])
        c3.metric("데이터 검증", "✅ 일치" if diff < 0.2 else "⚠️ 확인필요", delta=f"오차 {diff:.2f}%")

    # 심박수 추이 그래프
    if hr_data_col in latest and pd.notna(latest[hr_data_col]):
        try:
            hrs = [float(x) for x in str(latest[hr_data_col]).split(",")]
            times = [i*5 for i in range(len(hrs))]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=times, y=hrs, mode='lines+markers', name="Heart Rate", line=dict(color='#00dfd8')))
            fig.add_vline(x=max(times)/2, line_dash="dash", line_color="yellow", annotation_text="분석 분기점")
            fig.update_layout(template="plotly_dark", title="세션 내 심박수 변화 (Cardiac Drift 추적)", xaxis_title="시간(분)", yaxis_title="BPM")
            st.plotly_chart(fig, use_container_width=True)
        except:
            pass

    st.divider()
    with st.expander("📊 전체 히스토리 데이터"):
        st.dataframe(df.sort_values(by=session_col, ascending=False))
