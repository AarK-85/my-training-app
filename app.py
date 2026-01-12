import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 열 이름 정의
power_col, dec_col, session_col, hr_data_col = "평균 파워(W)", "디커플링(%)", "회차", "심박데이터"

# 3. 사이드바: Tunable 데이터 입력창
with st.sidebar:
    st.header("📝 정밀 훈련 기록")
    with st.form(key="tunable_form", clear_on_submit=False):
        date = st.date_input("날짜")
        last_s = int(df[session_col].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_s + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        
        st.divider()
        # --- 슬라이더로 시간 조절 ---
        st.subheader("⏱️ 훈련 시간 설정")
        duration = st.slider("본 훈련 시간 선택 (분)", 15, 180, 60, step=5)
        avg_p = st.number_input("목표 파워(W) 설정", value=135)
        user_dec = st.number_input("수동 기입 디커플링(%)", value=0.0, step=0.1)
        
        # --- 동적 심박수 입력 칸 ---
        st.subheader(f"💓 {duration}분간 심박수 입력 (5분 간격)")
        num_inputs = (duration // 5) + 1
        hr_list_input = []
        
        # 입력 편의를 위해 columns 활용
        for i in range(num_inputs):
            val = st.number_input(f"{i*5}분 시점", value=130, key=f"hr_input_{i}")
            hr_list_input.append(val)
        
        notes = st.text_area("특이사항 (RPE, 컨디션 등)")

        if st.form_submit_button("기록 저장 및 분석 실행"):
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
            st.success(f"데이터 연동 완료! 분석 수치: {auto_dec}%")
            st.rerun()

# 4. 메인 분석 대시보드
if not df.empty:
    st.title("🚴 Cardiac Drift 정밀 분석")
    
    latest = df.iloc[-1]
    
    # 상단 요약 지표
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("최근 파워", f"{latest[power_col]} W")
    c2.metric("앱 계산 디커플링", f"{latest[dec_col]} %")
    
    if "수동기입값" in latest:
        diff = abs(latest[dec_col] - latest["수동기입값"])
        c3.metric("데이터 검증", "✅ 일치" if diff < 0.2 else "⚠️ 오차", delta=f"{diff:.2f}%")
    c4.metric("훈련 시간", f"{latest['훈련 시간(분)']} 분")

    # 📈 Power/HR Drift 분석 시각화
    if hr_data_col in latest and pd.notna(latest[hr_data_col]):
        hrs = [float(x) for x in str(latest[hr_data_col]).split(",")]
        times = [i*5 for i in range(len(hrs))]
        powers = [latest[power_col]] * len(hrs) # 일정한 파워 라인
        
        # 이중 축 그래프 생성 (Power vs HR)
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 파워 라인 (영역 그래프)
        fig.add_trace(
            go.Scatter(x=times, y=powers, name="Power (W)", fill='tozeroy', 
                       line=dict(color='rgba(0, 223, 216, 0.5)', width=0)),
            secondary_y=False,
        )

        # 심박수 라인 (Drift 확인용)
        fig.add_trace(
            go.Scatter(x=times, y=hrs, mode='lines+markers', name="Heart Rate (BPM)",
                       line=dict(color='#ff4b4b', width=3)),
            secondary_y=True,
        )

        # 분석 분기점 (노란 점선)
        fig.add_vline(x=max(times)/2, line_dash="dash", line_color="yellow", 
                     annotation_text="EF 분석 분기점", annotation_position="top left")

        fig.update_layout(
            title=f"Session {latest[session_col]} : Power vs Heart Rate Drifting 분석",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_xaxes(title_text="Time (minutes)")
        fig.update_yaxes(title_text="<b>Power</b> (Watts)", secondary_y=False, range=[0, max(powers)*1.5])
        fig.update_yaxes(title_text="<b>Heart Rate</b> (BPM)", secondary_y=True, range=[min(hrs)-10, max(hrs)+10])

        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    with st.expander("📊 전체 훈련 시계열 데이터 보기"):
        st.dataframe(df.sort_values(by=session_col, ascending=False))
