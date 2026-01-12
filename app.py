import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Analytics", layout="wide")

# 2. 구글 시트 연결 및 데이터 로드
conn = st.connection("gsheets", type=GSheetsConnection)

# 에러 방지를 위해 데이터를 읽어올 때 처리
try:
    df = conn.read(ttl=0)
    # 데이터가 아예 없거나 '회차' 컬럼이 없는 경우 빈 데이터프레임 생성
    if df is None or "회차" not in df.columns:
        df = pd.DataFrame(columns=["날짜", "회차", "Phase", "훈련시간", "평균파워", "평균심박", "EF", "디커플링", "피로도", "메모"])
except Exception as e:
    st.error(f"시트 연결 오류: {e}")
    df = pd.DataFrame(columns=["날짜", "회차", "Phase", "훈련시간", "평균파워", "평균심박", "EF", "디커플링", "피로도", "메모"])

st.title("📊 Zone 2 Performance Analytics")

# 3. 사이드바 입력창
with st.sidebar:
    st.header("➕ 새로운 기록 추가")
    
    with st.form(key="training_input_form", clear_on_submit=True):
        date = st.date_input("훈련 날짜")
        
        # ✅ 에러 수정 포인트: 데이터가 숫자인지 확인하고 안전하게 마지막 회차 가져오기
        try:
            if not df.empty and pd.to_numeric(df["회차"], errors='coerce').notnull().any():
                last_session = int(pd.to_numeric(df["회차"], errors='coerce').max())
            else:
                last_session = 0
        except:
            last_session = 0
            
        session = st.number_input("회차", value=last_session + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        power = st.slider("평균 파워 (W)", 100, 200, 135)
        decoupling = st.number_input("디커플링 (%)", value=5.0, step=0.1)
        hr = st.slider("평균 심박 (bpm)", 100, 180, 130)
        rpe = st.select_slider("피로도", options=list(range(1, 11)), value=5)
        notes = st.text_area("메모")
        
        submitted = st.form_submit_button("기록 저장하기")
        
        if submitted:
            new_entry = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"),
                "회차": session,
                "Phase": phase,
                "훈련시간": 60,
                "평균파워": power,
                "평균심박": hr,
                "EF": round(power/hr, 2) if hr > 0 else 0,
                "디커플링": decoupling,
                "피로도": rpe,
                "메모": notes
            }])
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"{session}회차 저장 완료!")
            st.rerun()

# 4. 데이터 시각화
if not df.empty and len(df) > 0:
    c1, c2, c3 = st.columns(3)
    # 수치형 데이터로 변환 후 지표 계산
    latest_power = pd.to_numeric(df['평균파워'], errors='coerce').iloc[-1]
    min_dec = pd.to_numeric(df
