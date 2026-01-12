import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Analytics", layout="wide")

# 2. 구글 시트 연결 및 데이터 로드
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 로드 및 초기화 로직
try:
    df = conn.read(ttl=0)
    if df is None or "회차" not in df.columns:
        df = pd.DataFrame(columns=["날짜", "회차", "Phase", "훈련시간", "평균파워", "평균심박", "EF", "디커플링", "피로도", "메모"])
except Exception:
    df = pd.DataFrame(columns=["날짜", "회차", "Phase", "훈련시간", "평균파워", "평균심박", "EF", "디커플링", "피로도", "메모"])

st.title("📊 Zone 2 Performance Analytics")

# 3. 사이드바 입력창
with st.sidebar:
    st.header("➕ 새로운 기록 추가")
    
    with st.form(key="training_input_form", clear_on_submit=True):
        date = st.date_input("훈련 날짜")
        
        # 마지막 회차 안전하게 가져오기
        try:
            if not df.empty:
                sessions = pd.to_numeric(df["회차"], errors='coerce').dropna()
                last_session = int(sessions.max()) if not sessions.empty else 0
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

# 4. 데이터 시각화 (데이터가 있을 때만 표시)
if not df.empty and len(df) > 0:
    c1, c2, c3 = st.columns(3)
    
    # 데이터 숫자형 변환 (에러 방지)
    df['평균파워'] = pd.to_numeric(df['평균파워'], errors='coerce')
    df['디커플링'] = pd.to_numeric(df['디커플링'], errors='coerce')
    df['회차'] = pd.to_numeric(df['회차'], errors='coerce')
    
    latest_power = df['평균파워'].iloc[-1] if not df['평균파워'].isnull().all() else 0
    min_dec = df['디커플링'].min() if not df['디커플링'].isnull().all() else 0
    
    c1.metric("최근 파워", f"{latest_power} W")
    c2.metric("최저 디커플링", f"{min_dec}%")
    c3.metric("진행 회차", f"{len(df)}회")

    # 메인 그래프
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['회차'], y=df['평균파워'], name="평균 파워", line=dict(color='#00CC96', width=3)))
    fig.add_hline(y=160, line_dash="dash", line_color="red", annotation_text="목표 160W")
    fig.update_layout(title="파워 성장 추이", template="plotly_dark", xaxis_title="회차", yaxis_title="Power (W)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("사이드바에서 첫 데이터를 입력하면 분석 대시보드가 활성화됩니다.")
