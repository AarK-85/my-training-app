import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# 페이지 설정 (다크 모드 및 Fancy한 레이아웃)
st.set_page_config(page_title="Zone 2 Performance Tracker", layout="wide")

# 데이터 저장용 파일 (CSV)
DB_FILE = "training_data.csv"

# 데이터 불러오기 함수
def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        return pd.DataFrame(columns=["날짜", "회차", "Phase", "평균파워", "평균심박", "디커플링", "피로도", "메모"])

# 데이터 저장 함수
def save_data(df):
    df.to_csv(DB_FILE, index=False)

# 메인 화면 구성
st.title("🚴 Performance Analytics Dashboard")
st.markdown("---")

# 사이드바: 데이터 입력 창 (모바일 접속 시 입력 편리)
with st.sidebar:
    st.header("📝 오늘의 기록")
    date = st.date_input("훈련 날짜", datetime.now())
    session_num = st.number_input("회차", min_value=1, step=1)
    phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
    power = st.slider("평균 파워 (W)", 100, 250, 135)
    hr = st.slider("평균 심박 (bpm)", 100, 180, 130)
    decoupling = st.number_input("디커플링 (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.1)
    rpe = st.select_slider("주관적 피로도", options=list(range(1, 11)), value=5)
    notes = st.text_area("메모")
    
    if st.button("데이터 저장하기"):
        new_data = {
            "날짜": date.strftime("%Y-%m-%d"),
            "회차": session_num,
            "Phase": phase,
            "평균파워": power,
            "평균심박": hr,
            "디커플링": decoupling,
            "피로도": rpe,
            "메모": notes
        }
        df = load_data()
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        save_data(df)
        st.success("기록 완료!")

# 메인 분석 화면
df = load_data()

if not df.empty:
    # 상단 요약 지표 (Scorecards)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("최근 평균 파워", f"{df['평균파워'].iloc[-1]} W", delta=f"{df['평균파워'].iloc[-1] - 130 if len(df)>1 else 0} W")
    with col2:
        status = "✅ 목표달성" if df['디커플링'].iloc[-1] <= 5 else "⚠️ 주의"
        st.metric("최근 디커플링 상태", f"{df['디커플링'].iloc[-1]} %", delta=status, delta_color="normal")
    with col3:
        target_left = 160 - df['평균파워'].max()
        st.metric("최종 목표(160W)까지", f"{target_left} W")

    st.markdown("---")

    # 차트 1: 파워 및 디커플링 추세 (시계열 분석)
    st.subheader("📊 훈련 성과 추이")
    fig = px.line(df, x="회차", y=["평균파워", "디커플링"], 
                  title="회차별 파워 및 효율 변화",
                  markers=True, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # 차트 2: Phase별 비교
    st.subheader("📂 Phase별 평균 데이터")
    phase_summary = df.groupby("Phase")[["평균파워", "디커플링"]].mean().reset_index()
    fig2 = px.bar(phase_summary, x="Phase", y="평균파워", color="디커플링",
                  title="Phase별 파워 성취도", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

    # 데이터 테이블
    with st.expander("전체 기록 보기"):
        st.dataframe(df.sort_values(by="회차", ascending=False), use_container_width=True)
else:
    st.info("아직 입력된 데이터가 없습니다. 왼쪽 사이드바에서 첫 기록을 시작하세요!")
