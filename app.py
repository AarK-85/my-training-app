import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정 및 shadcn 스타일 테마 적용 (Custom CSS)
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

st.markdown("""
    <style>
    /* shadcn/ui 스타일 CSS */
    .main { background-color: #09090b; }
    .stMetric { 
        background-color: #18181b; 
        padding: 15px; 
        border-radius: 12px; 
        border: 1px solid #27272a; 
    }
    div[data-testid="stMetricValue"] { color: #fafafa; font-size: 1.8rem; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: #18181b;
        border-radius: 6px;
        border: 1px solid #27272a;
        color: #a1a1aa;
        padding: 0px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #27272a; color: #fff; border: 1px solid #3f3f46; }
    .stInfo, .stSuccess, .stWarning, .stError { border-radius: 12px; border: 1px solid #27272a; background-color: #18181b; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 연결 및 전처리
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    for col in ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 3. 사이드바 (내림차순 정렬 및 입력 폼)
with st.sidebar:
    st.markdown("### ⚙️ Management")
    mode = st.radio("Task", ["View & Edit", "🆕 New Session"], label_visibility="collapsed")
    st.divider()
    
    if mode == "View & Edit" and not df.empty:
        sessions = sorted(df["회차"].unique().tolist(), reverse=True)
        selected_session = st.selectbox("Select Session", sessions, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0]
        btn_label = "Update Changes"
    else:
        next_session = int(df["회차"].max() + 1) if not df.empty else 1
        s_data, selected_session = None, next_session
        btn_label = "Save New Record"

    with st.form(key="training_form"):
        f_date = st.date_input("Date", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now())
        f_session = st.number_input("Session No.", value=int(selected_session), step=1)
        f_wp = st.number_input("Warmup (W)", value=int(s_data['웜업파워']) if s_data is not None else 97, step=1)
        f_mp = st.number_input("Main (W)", value=int(s_data['본훈련파워']) if s_data is not None else 140, step=1)
        f_cp = st.number_input("Cooldown (W)", value=int(s_data['쿨다운파워']) if s_data is not None else 90, step=1)
        f_duration = st.slider("Duration (Min)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 90, step=5)
        
        # 심박수 입력 필드
        num_main = f_duration // 5
        total_steps = 2 + num_main + 1
        existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
        hr_inputs = []
        for i in range(total_steps):
            try: def_hr = int(float(existing_hrs[i].strip()))
            except: def_hr = 130
            hr_val = st.number_input(f"HR at {i*5}m", value=def_hr, key=f"hr_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))
        
        if st.form_submit_button(btn_label):
            main_hrs = [int(x) for x in hr_inputs[2:-1]]
            mid = len(main_hrs) // 2
            f_ef_val = f_mp / np.mean(main_hrs[:mid])
            s_ef_val = f_mp / np.mean(main_hrs[mid:])
            f_dec = round(((f_ef_val - s_ef_val) / f_ef_val) * 100, 2)
            new_row = {"날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)}
            updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
            conn.update(data=updated_df)
            st.rerun()

# 4. 메인 대시보드 (shadcn 리디자인)
if not df.empty and s_data is not None:
    st.title(f"📊 Session {int(s_data['회차'])} Precision Report")
    
    tab1, tab2 = st.tabs(["Analysis", "Trends"])

    with tab1:
        # AI Briefing Card
        current_dec = s_data['디커플링(%)']
        current_p, current_dur = int(s_data['본훈련파워']), int(s_data['본훈련시간'])
        
        if current_dec <= 5.0:
            msg = f"**🔥 Optimal State.** {current_p}W is now your base. {'Increase duration to ' + str(current_dur+15) + 'm' if current_dur < 90 else 'Increase intensity to ' + str(current_p+5) + 'W'} next."
            st.success(msg)
        else:
            st.warning(f"**⏳ Adaptation Required.** Decoupling at {current_dec}%. Stay at {current_p}W for 1-2 more sessions.")

        # Metric Grid
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Target Power", f"{current_p}W")
        m2.metric("Decoupling", f"{current_dec}%", delta="Stable" if current_dec <= 5.0 else "High", delta_color="normal" if current_dec <= 5.0 else "inverse")
        m3.metric("Peak HR", f"{int(max([float(x) for x in str(s_data['전체심박데이터']).split(',')]))}BPM")
        m4.metric("Total Volume", f"{current_dur}m")

        # Sequence Plot (Plotly shadcn 스타일링)
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        time_array = [i*5 for i in range(len(hr_array))]
        power_array = [int(s_data['웜업파워'])]*2 + [current_p]*(current_dur//5) + [int(s_data['쿨다운파워'])]
        
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=time_array, y=power_array, name="Power", line=dict(color='#3b82f6', width=3, shape='hv'), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_array, y=hr_array, name="HR", line=dict(color='#ef4444', width=3, shape='spline')), secondary_y=True)
        fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        # Progress Tracker
        progress = min(current_p / 160, 1.0)
        st.markdown(f"**Road to 160W** ({progress*100:.1f}%)")
        st.progress(progress)
        
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("### Efficiency Index")
            def get_ef(r): return int(r['본훈련파워']) / np.mean([float(x) for x in str(r['전체심박데이터']).split(",")][2:-1])
            df['EF'] = df.apply(get_ef, axis=1)
            fig_ef = go.Figure(go.Scatter(x=df['회차'], y=df['EF'], mode='lines+markers', line=dict(color='#10b981', width=3)))
            fig_ef.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_ef, use_container_width=True)
        with c_right:
            st.markdown("### HR Recovery")
            def get_hrr(r): 
                hrs = [float(x) for x in str(r['전체심박데이터']).split(",")]
                return int(hrs[-2] - hrs[-1])
            df['HRR'] = df.apply(get_hrr, axis=1)
            fig_hrr = go.Figure(go.Bar(x=df['회차'], y=df['HRR'], marker_color='#f59e0b'))
            fig_hrr.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_hrr, use_container_width=True)
