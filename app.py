import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정
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

# 2. 데이터 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜'])
    for col in ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 3. 사이드바
with st.sidebar:
    st.markdown("### 🔍 History")
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("조회할 회차", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else:
        s_data = None

# 4. 메인 탭
st.title("Zone 2 Precision Lab")
tab_entry, tab_analysis, tab_trends = st.tabs(["🆕 New Session", "🎯 Analysis", "📈 Trends"])

# --- [TAB 1: 데이터 입력] ---
with tab_entry:
    st.markdown('<p class="section-title">Record Training Data</p>', unsafe_allow_html=True)
    with st.form(key="modern_entry_form"):
        c1, c2, c3 = st.columns([1, 1, 2])
        f_date = c1.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now().date())
        f_session = c2.number_input("회차", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
        f_duration = c3.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 60, step=5)
        
        p1, p2, p3 = st.columns(3)
        f_wp = p1.number_input("웜업 파워 (10분 고정)", value=int(s_data['웜업파워']) if s_data is not None else 100, step=1)
        f_mp = p2.number_input("본훈련 파워", value=int(s_data['본훈련파워']) if s_data is not None else 140, step=1)
        f_cp = p3.number_input("쿨다운 파워 (5분 고정)", value=int(s_data['쿨다운파워']) if s_data is not None else 90, step=1)
        
        # 입력창 구성: 웜업(10분=2개) + 본훈련(Dur/5개) + 쿨다운(5분=1개)
        num_main = f_duration // 5
        total_steps = 2 + num_main + 1
        existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
        
        hr_inputs = []
        h_cols = st.columns(4)
        for i in range(total_steps):
            t_min = i * 5
            if i < 2: label = f"🟢 웜업 {t_min}m"
            elif i < 2 + num_main: label = f"🔵 본훈련 {t_min}m"
            else: label = f"⚪ 쿨다운 {t_min}m"
            
            try: def_hr = int(float(existing_hrs[i].strip()))
            except: def_hr = 130
            with h_cols[i % 4]:
                hr_val = st.number_input(label, value=def_hr, key=f"hr_input_{i}", step=1)
                hr_inputs.append(str(int(hr_val)))
        
        if st.form_submit_button("🚀 SAVE TRAINING RECORD", use_container_width=True):
            # 디커플링 계산 로직 (웜업 2개 제외, 본훈련 데이터만 추출)
            main_hrs = [int(x) for x in hr_inputs[2:-1]]
            mid = len(main_hrs) // 2
            f_ef_val = f_mp / np.mean(main_hrs[:mid]) if len(main_hrs[:mid]) > 0 else 1
            s_ef_val = f_mp / np.mean(main_hrs[mid:]) if len(main_hrs[mid:]) > 0 else 1
            f_dec = round(((f_ef_val - s_ef_val) / f_ef_val) * 100, 2)
            
            new_row = {
                "날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), 
                "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), 
                "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)
            }
            updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
            updated_df['날짜'] = updated_df['날짜'].astype(str)
            conn.update(data=updated_df)
            st.success("✅ 저장되었습니다!")
            st.rerun()

# --- [TAB 2: 분석 결과 및 수직 그래프] ---
with tab_analysis:
    if not df.empty and s_data is not None:
        st.markdown("### 🤖 AI Coach's Daily Briefing")
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        current_dec = s_data['디커플링(%)']
        current_p, current_dur = int(s_data['본훈련파워']), int(s_data['본훈련시간'])
        max_hr = int(max(hr_array))

        # 코칭 로직 (5.8% 상향 제안 포함)
        if current_dec <= 5.0: st.success(f"**🔥 유산소 제어 완벽.** {current_p+5}W로 상향 제안!")
        elif current_dec <= 8.0: st.info(f"**✅ 엔진 확장 확인.** {current_dec}%로 5%를 약간 넘었지만, 통제력이 좋으니 {current_p+5}W로 전진합시다!")
        else: st.error(f"**⏳ 적응 필요.** {current_p}W를 유지하며 심박을 먼저 잡으세요.")

        st.divider()

        # 수직 파워 그래프 데이터 (Step Chart Logic)
        time_x = [i*5 for i in range(len(hr_array))]
        p_warm = [int(s_data['웜업파워'])] * 2
        p_main = [current_p] * (current_dur // 5)
        p_cool = [int(s_data['쿨다운파워'])]
        power_y = (p_warm + p_main + p_cool)[:len(time_x)]

        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(
            x=time_x, y=power_y, name="Power(W)",
            line=dict(color='#3b82f6', width=4, shape='hv'),
            fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'
        ), secondary_y=False)
        fig1.add_trace(go.Scatter(
            x=time_x, y=hr_array, name="HR(BPM)",
            line=dict(color='#ef4444', width=3, shape='spline')
        ), secondary_y=True)

        fig1.update_layout(template="plotly_dark", height=450, hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig1, use_container_width=True)

# --- [TAB 3: Trends] ---
with tab_trends:
    if not df.empty:
        df_vol = df.copy(); df_vol['날짜'] = pd.to_datetime(df_vol['날짜'])
        weekly_v = df_vol.set_index('날짜')['본훈련시간'].resample('W').sum().reset_index()
        weekly_v['날짜'] = weekly_v['날짜'].dt.strftime('%m/%d')
        
        st.markdown("### 📅 Weekly Training Volume")
        fig_vol = go.Figure(go.Bar(x=weekly_v['날짜'], y=weekly_v['본훈련시간'], text=(weekly_v['본훈련시간']/60).round(1), textposition='auto', marker_color='#8b5cf6'))
        fig_vol.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_vol, use_container_width=True)
