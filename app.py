import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Performance Pro", layout="wide")

# 스타일 커스텀
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
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

st.title("🚀 Zone 2 Performance Coach")

# --- 🎯 훈련 로드맵 (기준 정보) ---
with st.expander("🏁 Phase별 졸업 기준 및 목표 확인"):
    guide_data = {
        "구분": ["Phase 1", "Phase 2", "Phase 3"],
        "목표 파워": ["130W - 135W", "140W - 150W", "150W - 160W+"],
        "졸업 기준": ["5.0% 미만", "5.0% - 8.0%", "7.0% - 10.0%"],
        "훈련 목적": ["기초 유산소 강화", "유산소 상향/SS 병행", "고강도 지속주 완성"]
    }
    st.table(pd.DataFrame(guide_data))

# 3. 사이드바 입력창
with st.sidebar:
    st.header("📝 오늘의 훈련 기록")
    with st.form(key="input_form", clear_on_submit=True):
        date = st.date_input("날짜")
        last_s = int(df[session_col].max()) if not df.empty else 0
        session = st.number_input("회차", value=last_s + 1)
        current_phase = st.selectbox("Phase", ["Phase 1", "Phase 2", "Phase 3"])
        power = st.slider("평균 파워(W)", 100, 200, 135)
        hr = st.slider("평균 심박(bpm)", 100, 180, 130)
        dec = st.number_input("디커플링(%)", value=5.0, step=0.1)
        rpe = st.select_slider("피로도", options=list(range(1, 11)), value=5)
        notes = st.text_area("메모")
        
        if st.form_submit_button("기록 저장하기"):
            new_row = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"), "회차": session, "Phase": current_phase,
                "훈련 시간(분)": 60, "평균 파워(W)": power, "평균 심박(bpm)": hr,
                "효율(EF)": round(power/hr, 2) if hr > 0 else 0, "디커플링(%)": dec,
                "피로도": rpe, "메모": notes
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("훈련 데이터가 반영되었습니다!")
            st.rerun()

# 4. 분석 결과 & 일치된 훈련 처방
if not df.empty:
    latest_p = df[power_col].iloc[-1]
    latest_d = df[dec_col].iloc[-1]
    avg_d_recent = df[dec_col].tail(3).mean()
    now_phase = df[phase_col].iloc[-1]

    # 상단 지표
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("최근 파워", f"{latest_p} W")
    c2.metric("최근 디커플링", f"{latest_d} %")
    c3.metric("누적 횟수", f"{len(df)} 회")
    progress = min(latest_p / 160, 1.0)
    c4.write(f"**최종 목표 달성률 ({int(progress*100)}%)**")
    c4.progress(progress)

    st.markdown("---")

    # 🤖 일치된 AI 훈련 처방 섹션
    st.subheader("📋 데이터 기반 Next Step 가이드")
    
    # 처방 로직 (졸업 기준과 직접 비교)
    if now_phase == "Phase 1":
        target_dec = 5.0
        next_power = 140
    elif now_phase == "Phase 2":
        target_dec = 8.0
        next_power = 150
    else:
        target_dec = 10.0
        next_power = 160

    if avg_d_recent < target_dec:
        st.success(f"🔥 **Phase 졸업 및 강도 상향 권장:** 최근 평균 디커플링({avg_d_recent:.1f}%)이 기준({target_dec}%)보다 낮습니다. 다음 훈련은 **{next_power}W**로 상향하여 다음 단계를 시작하세요!")
    else:
        st.info(f"✅ **현재 강도 유지 및 다지기:** 최근 평균 디커플링({avg_d_recent:.1f}%)이 기준({target_dec}%)보다 약간 높습니다. **{latest_p}W**를 유지하며 디커플링이 {target_dec}% 미만으로 안정될 때까지 2~3회 더 반복하세요.")

    # 그래프
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[session_col], y=df[power_col], mode='lines+markers', name="Power", line=dict(color='#00dfd8')))
    fig.add_hline(y=160, line_dash="dash", line_color="#ff4b4b", annotation_text="Target 160W")
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)
