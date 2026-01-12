import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Full Sequence Lab", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 3. 사이드바: 구간별 파워 및 심박수 입력
with st.sidebar:
    st.header("🚴 전체 라이딩 시퀀스 입력")
    with st.form(key="full_sequence_form", clear_on_submit=False):
        date = st.date_input("날짜")
        session = st.number_input("회차", value=int(df["회차"].max() + 1) if not df.empty else 1)
        
        st.divider()
        st.subheader("1️⃣ 웜업 (Warm-up)")
        w_p = st.number_input("웜업 파워(W)", value=97)
        w_hr = st.text_input("웜업 심박 2개 (쉼표 구분)", "95, 125")
        
        st.subheader("2️⃣ 본 훈련 (Main Set)")
        main_p = st.number_input("본 훈련 파워(W)", value=135)
        duration = st.slider("본 훈련 시간(분)", 15, 180, 90, step=5)
        main_hr = st.text_area("본 훈련 심박 시계열 (5분 단위)", "130, 142, 141, 151, 153, 157, 154, 154, 160, 158, 160, 160, 160, 159, 160, 163, 161, 164, 159")
        
        st.subheader("3️⃣ 쿨다운 (Cool-down)")
        c_p = st.number_input("쿨다운 파워(W)", value=107)
        c_hr = st.text_input("쿨다운 심박 1개", "154")

        if st.form_submit_button("전체 시퀀스 저장 및 분석"):
            # 데이터 통합
            full_hr = f"{w_hr}, {main_hr}, {c_hr}"
            full_p = f"{w_p}, {main_p}, {c_p}" # 파워 시퀀스도 저장
            
            # 디커플링 계산 (본 훈련 구간만)
            try:
                m_hrs = [float(x.strip()) for x in main_hr.split(",")]
                mid = len(m_hrs) // 2
                f_ef = main_p / np.mean(m_hrs[:mid])
                s_ef = main_p / np.mean(m_hrs[mid:])
                dec = round(((f_ef - s_ef) / f_ef) * 100, 2)
            except:
                dec = 0
            
            new_row = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"), "회차": session, 
                "웜업파워": w_p, "본훈련파워": main_p, "쿨다운파워": c_p,
                "본훈련시간": duration, "디커플링(%)": dec, 
                "전체심박데이터": full_hr
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("데이터가 성공적으로 저장되었습니다!")
            st.rerun()

# 4. 메인 대시보드: 리얼 파워-심박 그래프
if not df.empty:
    latest = df.iloc[-1]
    st.title(f"📊 Session {latest['회차']} 정밀 시퀀스 분석")
    
    # 파워 및 심박 배열 생성 로직
    hr_array = [float(x.strip()) for x in str(latest['전체심박데이터']).split(",")]
    
    # 저장된 각 구간 파워값 불러오기
    wp, mp, cp = latest['웜업파워'], latest['본훈련파워'], latest['쿨다운파워']
    
    # 웜업(2칸), 본훈련(나머지), 쿨다운(1칸) 비율에 맞춰 파워 배열 구성
    power_array = [wp, wp] + [mp] * (len(hr_array) - 3) + [cp]
    time_array = [i*5 for i in range(len(hr_array))]

    fig = go.Figure()

    # 1. 파워 영역 (실제 기입한 파워 반영)
    fig.add_trace(go.Scatter(x=time_array, y=power_array, name="Actual Power (W)", 
                             fill='tozeroy', line=dict(color='rgba(0, 223, 216, 0.5)', width=2), yaxis="y1"))
    
    # 2. 심박수 라인
    fig.add_trace(go.Scatter(x=time_array, y=hr_array, name="Heart Rate (BPM)", 
                             line=dict(color='#ff4b4b', width=4, shape='spline'), yaxis="y2"))

    # 구간 라벨링
    fig.add_vrect(x0=0, x1=10, fillcolor="white", opacity=0.1, annotation_text="Warm-up")
    fig.add_vrect(x0=10, x1=time_array[-2], fillcolor="blue", opacity=0.05, annotation_text="Main Set")
    fig.add_vrect(x0=time_array[-2], x1=time_array[-1], fillcolor="white", opacity=0.1, annotation_text="Cool-down")

    fig.update_layout(
        template="plotly_dark", height=600,
        yaxis=dict(title="Power (Watts)", range=[0, max(power_array)*1.3]),
        yaxis2=dict(title="Heart Rate (BPM)", overlaying="y", side="right", range=[min(hr_array)-10, max(hr_array)+10]),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"💡 **분석 결과:** 본 훈련 파워 **{mp}W** 기준, 디커플링 수치는 **{latest['디커플링(%)']}%**입니다.")

    with st.expander("📂 누적 데이터 로그"):
        st.dataframe(df)
