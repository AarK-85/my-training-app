import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Analytics", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl=0)
        return data if data is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df = get_data()

st.title("📊 Zone 2 Performance Analytics")

# 3. 사이드바 입력창
with st.sidebar:
    st.header("➕ 새로운 기록 추가")
    
    with st.form(key="training_input_form", clear_on_submit=True):
        date = st.date_input("날짜")
        
        # 회차 자동 계산 (사용자님의 '회차' 열 이름 기준)
        last_session = 0
        if not df.empty and "회차" in df.columns:
            sessions = pd.to_numeric(df["회차"], errors='coerce').dropna()
            last_session = int(sessions.max()) if not sessions.empty else 0
            
        session = st.number_input("회차", value=last_session + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        duration = st.number_input("훈련 시간(분)", value=60)
        power = st.slider("평균 파워(W)", 100, 200, 135)
        hr = st.slider("평균 심박(bpm)", 100, 180, 130)
        decoupling = st.number_input("디커플링(%)", value=5.0, step=0.1)
        rpe = st.select_slider("피로도", options=list(range(1, 11)), value=5)
        notes = st.text_area("메모")
        
        submitted = st.form_submit_button("기록 저장하기")
        
        if submitted:
            # 사용자님의 시트 헤더와 동일하게 데이터 구성
            new_entry = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"),
                "회차": session,
                "Phase": phase,
                "훈련 시간(분)": duration,
                "평균 파워(W)": power,
                "평균 심박(bpm)": hr,
                "효율(EF)": round(power/hr, 2) if hr > 0 else 0,
                "디커플링(%)": decoupling,
                "피로도": rpe,
                "메모": notes
            }])
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"{session}회차 저장 완료!")
            st.rerun()

# 4. 데이터 시각화 (사용자님 시트의 열 이름 기준)
# 체크할 열 이름들: '평균 파워(W)', '디커플링(%)', '회차'
power_col = "평균 파워(W)"
dec_col = "디커플링(%)"
session_col = "회차"

if not df.empty and power_col in df.columns:
    c1, c2, c3 = st.columns(3)
    
    # 수치 형변환
    df[power_col] = pd.to_numeric(df[power_col], errors='coerce').fillna(0)
    df[dec_col] = pd.to_numeric(df[dec_col], errors='coerce').fillna(0)
    df[session_col] = pd.to_numeric(df[session_col], errors='coerce').fillna(0)
    
    latest_power = df[power_col].iloc[-1]
    min_dec = df[dec_col].min()
    
    c1.metric("최근 파워", f"{latest_power} W")
    c2.metric("최저 디커플링", f"{min_dec}%")
    c3.metric("진행 회차", f"{len(df)}회")

    # 메인 그래프
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[session_col], y=df[power_col], name="평균 파워", line=dict(color='#00CC96', width=3)))
    fig.add_hline(y=160, line_dash="dash", line_color="red", annotation_text="목표 160W")
    fig.update_layout(title="파워 성장 추이 (Goal: 160W)", template="plotly_dark", xaxis_title="회차", yaxis_title="Power (W)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("시트에 데이터가 입력되면 분석 대시보드가 활성화됩니다.")
