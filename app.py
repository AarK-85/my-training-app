import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Performance Pro", layout="wide")

# 스타일 커스텀 (CSS)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    div[data-testid="stExpander"] { border: none; background-color: #1f2937; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 열 이름 변수화
power_col, dec_col, session_col, phase_col = "평균 파워(W)", "디커플링(%)", "회차", "Phase"

if not df.empty:
    for col in [power_col, dec_col, session_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 메인 헤더
st.title("🚀 Zone 2 Performance Coach")
st.markdown(f"**Goal:** 2026년 3월 **160W** 달성")

# 3. 사이드바 입력창
with st.sidebar:
    st.header("📝 오늘의 훈련 기록")
    with st.form(key="input_form", clear_on_submit=True):
        date = st.date_input("날짜")
        last_s = int(df[session_col].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_s + 1)
        phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        power = st.slider("평균 파워(W)", 100, 200, 140)
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
            st.success("데이터가 반영되었습니다!")
            st.rerun()

# 4. 분석 결과 & 넥스트 스텝 제안
if not df.empty:
    latest_p = df[power_col].iloc[-1]
    latest_d = df[dec_col].iloc[-1]
    avg_dec_recent = df[dec_col].tail(3).mean() # 최근 3회 평균

    # 요약 지표
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("최근 파워", f"{latest_p} W")
    c2.metric("최근 디커플링", f"{latest_d} %")
    c3.metric("누적 횟수", f"{len(df)} 회")
    progress = min(latest_p / 160, 1.0)
    c4.write(f"**최종 목표 달성률 ({int(progress*100)}%)**")
    c4.progress(progress)

    st.markdown("---")

    # 🤖 데이터 기반 Next Step 가이드 (핵심 추가 기능)
    st.subheader("📋 AI 훈련 처방 (Next Step)")
    
    with st.container():
        # 분석 로직
        if avg_dec_recent <= 4.0:
            target_p = latest_p + 5
            advice = f"🔥 **강도 높이기 권장:** 최근 디커플링이 매우 낮습니다. 다음 세션은 **{target_p}W**로 파워를 높여 유산소 한계를 넓히세요!"
            color = "success"
        elif avg_dec_recent <= 6.0:
            advice = f"✅ **안정화 단계:** 현재 **{latest_p}W**가 몸에 잘 맞습니다. 다음 2~3회는 같은 강도를 유지하며 완벽히 다지세요."
            color = "info"
        else:
            target_p = latest_p - 5 if latest_p > 130 else 130
            advice = f"⚠️ **강도 하향 또는 유지:** 효율이 떨어지고 있습니다. 다음 세션은 **{target_p}W**로 낮춰서 심박 안정을 우선시하세요."
            color = "warning"
        
        if color == "success": st.success(advice)
        elif color == "info": st.info(advice)
        else: st.warning(advice)

    # 📈 그래프
    st.subheader("📊 Performance Trend")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[session_col], y=df[power_col], mode='lines+markers', name="Power", line=dict(color='#00dfd8')))
    fig.add_hline(y=160, line_dash="dash", line_color="#ff4b4b", annotation_text="Final Target")
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📝 전체 훈련 로그 확인"):
        st.table(df.sort_values(by=session_col, ascending=False).head(10))
