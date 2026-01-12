import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Analytics Engine", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 주요 열 이름 정의
power_col, dec_col, session_col = "평균 파워(W)", "디커플링(%)", "회차"

# 3. 사이드바: 맞춤형 데이터 입력
with st.sidebar:
    st.header("📝 훈련 세션 기록")
    with st.form(key="smart_input_form", clear_on_submit=True):
        date = st.date_input("날짜")
        last_s = int(df[session_col].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_s + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        
        st.divider()
        duration = st.number_input("본 훈련 시간(분)", value=60, step=5)
        avg_p = st.number_input("본 훈련 평균 파워(W)", value=135)
        user_dec = st.number_input("수동 기입 디커플링(%)", value=0.0, step=0.1)
        
        st.info("💡 5분 단위 심박 데이터가 있다면 아래에 입력하세요. 없으면 비워두셔도 됩니다.")
        hr_input = st.text_area("심박수 시계열 (쉼표로 구분, 예: 130, 135, 140...)", help="0분, 5분, 10분... 순서대로 입력")
        
        notes = st.text_area("메모 (기타 훈련 특이사항)")

        if st.form_submit_button("데이터 통합 저장"):
            auto_dec = user_dec # 기본값은 수동 입력값
            calc_msg = "수동 입력 데이터 기반"
            
            if hr_input:
                try:
                    hr_values = [float(x.strip()) for x in hr_input.split(",")]
                    if len(hr_values) >= 2:
                        # 전반부 / 후반부 분리 계산
                        mid = len(hr_values) // 2
                        first_half_hr = np.mean(hr_values[:mid])
                        second_half_hr = np.mean(hr_values[mid:])
                        
                        # 디커플링 공식 적용
                        first_ef = avg_p / first_half_hr
                        second_ef = avg_p / second_half_hr
                        auto_dec = round(((first_ef - second_ef) / first_ef) * 100, 2)
                        calc_msg = f"심박 데이터 분석 기반 (자동 계산: {auto_dec}%)"
                except:
                    st.error("심박 데이터 형식이 올바르지 않습니다.")

            new_data = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"), "회차": session, "Phase": phase,
                "훈련 시간(분)": duration, "평균 파워(W)": avg_p,
                "디커플링(%)": auto_dec, "수동기입값": user_dec,
                "메모": notes, "심박데이터": hr_input
            }])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"저장 완료: {calc_msg}")
            st.rerun()

# 4. 메인 대시보드 및 검증 엔진
if not df.empty:
    st.title("🚴 Zone 2 Training Intelligence")
    
    # 최근 세션 정밀 분석
    latest_session = df.iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("최근 세션 파워", f"{latest_session[power_col]} W")
    with col2:
        st.metric("앱 계산 디커플링", f"{latest_session[dec_col]} %")
    with col3:
        if "수동기입값" in latest_session and latest_session["수동기입값"] > 0:
            diff = abs(latest_session[dec_col] - latest_session["수동기입값"])
            status = "✅ 일치" if diff < 0.1 else "⚠️ 오차 발생"
            st.metric("데이터 정합성 검증", status, delta=f"차이: {diff:.2f}%")

    # 📈 심박 표류(Cardiac Drift) 시각화
    if "심박데이터" in latest_session and pd.notna(latest_session["심박데이터"]) and latest_session["심박데이터"] != "":
        st.subheader("📊 최근 세션 심박 표류 분석")
        hr_list = [float(x.strip()) for x in latest_session["심박데이터"].split(",")]
        time_list = [i*5 for i in range(len(hr_list))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=time_list, y=hr_list, mode='lines+markers', name="HR (bpm)", line=dict(color='#ff4b4b')))
        
        # 전/
