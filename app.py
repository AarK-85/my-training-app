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
    .guide-box { background-color: #111827; padding: 20px; border-radius: 10px; border-left: 5px solid #00dfd8; margin-bottom: 20px; }
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

# --- 🎯 훈련 로드맵 가이드보드 (추가된 섹션) ---
st.subheader("🏁 Phase별 훈련 로드맵")
guide_data = {
    "구분": ["Phase 1", "Phase 2", "Phase 3"],
    "목표 파워": ["130W - 135W", "140W - 150W", "150W - 160W+"],
    "훈련 구성": ["순수 Zone 2 (이틀에 한 번)", "Zone 2 (2회) + Sweet Spot #1 (1회)", "Zone 2 (2회) + Sweet Spot #3 (1회)"],
    "졸업 기준 (디커플링)": ["5.0% 미만 유지", "5.0% - 8.0% 이내", "7.0% - 10.0% 이내 (최종 160W)"],
    "훈련 목적": ["기초 유산소 엔진 및 미토콘드리아 강화", "유산소 한계 상향 및 젖산 내성 기초", "고강도 지속주 능력 완성 (3월 최종 목표)"]
}
st.table(pd.DataFrame(guide_data))

st.markdown("---")

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

# 4. 분석 결과 & 넥스트 스텝
if not df.empty:
    latest_p = df[power_col].iloc[-1]
    latest_d = df[dec_col].iloc[-1]
    avg_dec_recent = df[dec_col].tail(3).mean()

    # 요약 지표
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("최근 파워", f"{latest_p} W")
    c2.metric("최근 디커플링", f"{latest_d} %")
    c3.metric("누적 횟수", f"{len(df)} 회")
    progress = min(latest_p / 160, 1.0)
    c4.write(f"**최종 목표 달성률 ({int(progress*100)}%)**")
    c4.progress(progress)

    # 🤖 AI 훈련 처방
    st.subheader("📋 AI 훈련 처방 (Next Step)")
    if avg_dec_recent <= 4.5:
        st.success(f"🔥 **졸업 임박:** 디커플링이 매우 안정적입니다. 현재 Phase를 조기 졸업하고 파워를 5W 높여 다음 단계로 진행하는 것을 고려하세요!")
    elif avg_dec_recent <= 7.0:
        st.info(f"✅ **순항 중:** 현재 강도에 잘 적응하고 있습니다. 졸업 기준인 디커플링 수치에 도달할 때까지 정진하세요.")
    else:
        st.warning(f"⚠️ **강도 조정 필요:** 디커플링이 기준치보다 높습니다. 파워를 낮추거나 휴식 일을 추가하여 심박을 먼저 안정시키세요.")

    # 📈 그래프
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[session_col], y=df[power_col], mode='lines+markers', name="Power", line=dict(color='#00dfd8')))
    fig.add_hline(y=160, line_dash="dash", line_color="#ff4b4b", annotation_text="Final Target 160W")
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📝 전체 훈련 로그 확인"):
        st.table(df.sort_values(by=session_col, ascending=False).head(10))
