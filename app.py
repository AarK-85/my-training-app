import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정 및 shadcn 스타일 테마
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #09090b; }
    div[data-testid="stMetricValue"] { color: #fafafa; font-size: 1.8rem; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; background-color: #18181b; border-radius: 8px;
        border: 1px solid #27272a; color: #a1a1aa; padding: 0px 25px;
    }
    .stTabs [aria-selected="true"] { background-color: #27272a; color: #fff; border: 1px solid #3f3f46; }
    .stInfo, .stSuccess, .stWarning, .stError { border-radius: 12px; border: 1px solid #27272a; background-color: #18181b; }
    .section-title { color: #a1a1aa; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; margin-bottom: 12px; letter-spacing: 0.05em; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 연결 및 전처리
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    for col in ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 3. 사이드바
with st.sidebar:
    st.markdown("### 🔍 기록 선택")
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("조회할 회차", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else:
        s_data = None
    st.divider()
    st.caption("새 훈련 기록은 'New Session' 탭을 이용하세요.")

# 4. 메인 탭 구성
st.title("Zone 2 Precision Lab")
tab_entry, tab_analysis, tab_trends = st.tabs(["🆕 New Session", "🎯 Analysis", "📈 Trends"])

# --- [TAB 1: 데이터 입력/수정] ---
with tab_entry:
    st.markdown('<p class="section-title">Record Training Data</p>', unsafe_allow_html=True)
    with st.form(key="modern_entry_form"):
        c1, c2, c3 = st.columns([1, 1, 2])
        f_date = c1.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now())
        f_session = c2.number_input("회차", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
        f_duration = c3.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 90, step=5)
        
        st.markdown('<p class="section-title">Target Power (W)</p>', unsafe_allow_html=True)
        p1, p2, p3 = st.columns(3)
        f_wp = p1.number_input("웜업", value=int(s_data['웜업파워']) if s_data is not None else 97, step=1)
        f_mp = p2.number_input("본훈련", value=int(s_data['본훈련파워']) if s_data is not None else 140, step=1)
        f_cp = p3.number_input("쿨다운", value=int(s_data['쿨다운파워']) if s_data is not None else 90, step=1)
        
        st.markdown('<p class="section-title">Heart Rate Grid (BPM)</p>', unsafe_allow_html=True)
        num_main = f_duration // 5
        total_steps = 2 + num_main + 1
        existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
        
        hr_inputs = []
        h_cols = st.columns(4)
        for i in range(total_steps):
            t_label = f"{i*5}m"
            tag = f"🟢 {t_label}" if i < 2 else (f"🔵 {t_label}" if i < 2 + num_main else f"⚪ {t_label}")
            try: def_hr = int(float(existing_hrs[i].strip()))
            except: def_hr = 130
            with h_cols[i % 4]:
                hr_val = st.number_input(tag, value=def_hr, key=f"hr_input_{i}", step=1)
                hr_inputs.append(str(int(hr_val)))
        
        if st.form_submit_button("🚀 SAVE TRAINING RECORD", use_container_width=True):
            main_hrs = [int(x) for x in hr_inputs[2:-1]]
            mid = len(main_hrs) // 2
            f_ef_val = f_mp / np.mean(main_hrs[:mid]) if len(main_hrs[:mid]) > 0 else 1
            s_ef_val = f_mp / np.mean(main_hrs[mid:]) if len(main_hrs[mid:]) > 0 else 1
            f_dec = round(((f_ef_val - s_ef_val) / f_ef_val) * 100, 2)
            new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
            updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
            conn.update(data=updated_df)
            st.success("✅ 저장되었습니다!")
            st.rerun()

# --- [TAB 2: 분석 결과] ---
with tab_analysis:
    if not df.empty and s_data is not None:
        st.markdown("### 🤖 AI Coach's Daily Briefing")
        try:
            hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
            current_dec = s_data['디커플링(%)']
            current_p, current_dur = int(s_data['본훈련파워']), int(s_data['본훈련시간'])
            max_hr = int(max(hr_array))

            if current_dec <= 5.0:
                msg = f"**현재 {current_p}W 파워에 완벽히 적응했습니다.** {'시간을 ' + str(current_dur+15) + '분으로 늘려보세요.' if current_dur < 90 else '강도를 ' + str(current_p+5) + 'W로 상향해보세요!'}"
                st.success(msg)
            elif current_dec <= 8.0:
                st.warning(f"**적응 신호가 보입니다.** 현재 강도({current_p}W)를 유지하며 5% 이내 진입을 목표로 하세요.")
            else:
                st.error(f"**안정이 필요합니다.** 강도를 낮추거나 시간을 줄여 심박 제어력을 확보하세요.")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("훈련 파워", f"{current_p}W")
            m2.metric("디커플링", f"{current_dec}%", delta="- 안정" if current_dec <= 5.0 else "+ 주의", delta_color="normal" if current_dec <= 5.0 else "inverse")
            m3.metric("최대 심박", f"{max_hr}BPM")
            m4.metric("볼륨", f"{current_dur}m")

            st.divider()
            time_array = [i*5 for i in range(len(hr_array))]
            power_array = [int(s_data['웜업파워'])]*2 + [current_p]*(current_dur//5) + [int(s_data['쿨다운파워'])]
            power_array = power_array[:len(time_array)] # 길이 맞춤 안전장치

            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(go.Scatter(x=time_array, y=power_array, name="Power", line=dict(color='#3b82f6', width=3, shape='hv'), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'), secondary_y=False)
            fig1.add_trace(go.Scatter(x=time_array, y=hr_array, name="HR", line=dict(color='#ef4444', width=4, shape='spline')), secondary_y=True)
            fig1.update_layout(template="plotly_dark", height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig1, use_container_width=True)
        except:
            st.error("⚠️ 이 회차의 심박 데이터 형식이 올바르지 않습니다.")

# --- [TAB 3: 장기 트렌드] ---
with tab_trends:
    if not df.empty:
        # [수정된 에러 방지 함수들]
        def safe_get_ef(r):
            try:
                hrs = [float(x.strip()) for x in str(r['전체심박데이터']).split(",")]
                main = hrs[2:-1]
                return int(r['본훈련파워']) / np.mean(main) if len(main) > 0 else 0
            except: return 0

        def safe_get_hrr(r):
            try:
                hrs = [float(x.strip()) for x in str(r['전체심박데이터']).split(",")]
                if len(hrs) >= 2: return int(hrs[-2] - hrs[-1]) # 뒤에서 두번째 - 마지막
                return 0
            except: return 0

        df['EF'] = df.apply(safe_get_ef, axis=1)
        df['HRR'] = df.apply(safe_get_hrr, axis=1)
        
        st.subheader(f"🏁 최종 목표(160W) 달성률: {min(int(s_data['본훈련파워'])/160*100, 100.0) if s_data is not None else 0:.1f}%")
        st.progress(min(int(s_data['본훈련파워'])/160, 1.0) if s_data is not None else 0)
        
        st.divider()
        col_ef, col_hrr = st.columns(2)
        with col_ef:
            st.markdown("### Efficiency Index (EF)")
            fig_ef = go.Figure(go.Scatter(x=df['회차'], y=df['EF'], mode='lines+markers', line=dict(color='#10b981', width=3)))
            fig_ef.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=350, xaxis=dict(dtick=1))
            st.plotly_chart(fig_ef, use_container_width=True)
            
        with col_hrr:
            st.markdown("### HR Recovery (BPM)")
            fig_hrr = go.Figure(go.Bar(x=df['회차'], y=df['HRR'], marker_color='#f59e0b'))
            fig_hrr.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=350, xaxis=dict(dtick=1))
            st.plotly_chart(fig_hrr, use_container_width=True)
