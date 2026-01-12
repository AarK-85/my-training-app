import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 설정 (Dark Mode 친화적 설정)
st.set_page_config(page_title="Zone 2 Performance Pro", layout="wide")

# 스타일 커스텀 (CSS)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 열 이름 변수화 (사용자님 시트 기준)
power_col = "평균 파워(W)"
dec_col = "디커플링(%)"
session_col = "회차"
phase_col = "Phase"

# 데이터 전처리
if not df.empty:
    df[power_col] = pd.to_numeric(df[power_col], errors='coerce').fillna(0)
    df[dec_col] = pd.to_numeric(df[dec_col], errors='coerce').fillna(0)
    df[session_col] = pd.to_numeric(df[session_col], errors='coerce').fillna(0)

# 메인 헤더
st.title("🚀 Zone 2 Performance Dashboard")
st.markdown(f"**Target:** 2026년 3월까지 **160W** 달성 | 현재 진행 단계: **{df[phase_col].iloc[-1] if not df.empty else 'N/A'}**")

# 3. 사이드바 입력창
with st.sidebar:
    st.header("📝 오늘의 훈련 기록")
    with st.form(key="input_form", clear_on_submit=True):
        date = st.date_input("날짜")
        last_s = int(df[session_col].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_s + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        power = st.slider("평균 파워(W)", 100, 200, 135)
        hr = st.slider("평균 심박(bpm)", 100, 180, 130)
        dec = st.number_input("디커플링(%)", value=5.0, step=0.1)
        rpe = st.select_slider("피로도", options=list(range(1, 11)), value=5)
        notes = st.text_area("메모")
        
        if st.form_submit_button("기록 저장하기"):
            new_row = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"), "회차": session, "Phase": phase,
                "훈련 시간(분)": 60, "평균 파워(W)": power, "평균 심박(bpm)": hr,
                "효율(EF)": round(power/hr, 2) if hr > 0 else 0, "디커플링(%)": dec,
                "피로도": rpe, "메모": notes
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("훈련 데이터가 반영되었습니다!")
            st.rerun()

# 4. 분석 결과 & 시각화
if not df.empty:
    # 요약 지표 (Scorecards)
    c1, c2, c3, c4 = st.columns(4)
    latest_p = df[power_col].iloc[-1]
    latest_d = df[dec_col].iloc[-1]
    
    c1.metric("최근 훈련 파워", f"{latest_p} W")
    c2.metric("최근 디커플링", f"{latest_d} %", delta="-정상" if latest_d <= 5 else "+주의", delta_color="inverse")
    c3.metric("누적 훈련 횟수", f"{len(df)} 회")
    
    # 🎯 훈련 성공 지표 (Progress Bar)
    progress = min(latest_p / 160, 1.0)
    c4.write(f"**목표 달성률 ({int(progress*100)}%)**")
    c4.progress(progress)

    st.markdown("---")

    # 📈 메인 성장 그래프 (Fancy Version)
    st.subheader("📊 Performance Trend")
    fig = go.Figure()
    # 파워 선 그래프
    fig.add_trace(go.Scatter(x=df[session_col], y=df[power_col], mode='lines+markers', name="Power (W)",
                             line=dict(color='#00dfd8', width=3), marker=dict(size=8)))
    # 목표선 (160W)
    fig.add_hline(y=160, line_dash="dash", line_color="#ff4b4b", annotation_text="Target 160W")
    
    fig.update_layout(template="plotly_dark", height=450, 
                      margin=dict(l=20, r=20, t=50, b=20),
                      xaxis=dict(title="Training Sessions"), yaxis=dict(title="Watts"))
    st.plotly_chart(fig, use_container_width=True)

    # 🤖 AI 코치 분석 (성공 척도 판단)
    st.subheader("💡 훈련 분석 및 코멘트")
    
    # 분석 로직
    avg_dec = df[dec_col].tail(5).mean() # 최근 5회 평균 디커플링
    
    with st.container():
        col_msg, col_icon = st.columns([0.8, 0.2])
        if avg_dec <= 5.0:
            status_msg = "✅ **성공적인 유산소 적응:** 최근 5회차 동안 디커플링이 매우 안정적입니다. 파워를 5W 정도 높여도 좋습니다!"
        elif avg_dec <= 8.0:
            status_msg = "🟡 **적응 진행 중:** 현재 파워 수준에 몸이 적응하고 있습니다. 무리하게 파워를 올리기보다 심박 안정을 더 기다리세요."
        else:
            status_msg = "⚠️ **회복 필요:** 디커플링 수치가 높습니다. 훈련 강도를 낮추거나 충분한 휴식이 필요할 수 있습니다."
        
        st.info(status_msg)

    # 데이터 로그 확인
    with st.expander("📝 전체 훈련 로그 보기"):
        st.table(df.sort_values(by=session_col, ascending=False).head(10))

else:
    st.info("사이드바에서 데이터를 입력하면 분석이 시작됩니다.")
