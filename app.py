import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# --- [Data Loading with Enhanced Stability] ---
@st.cache_data(ttl=300)
def load_data(_conn):
    try:
        df = _conn.read(ttl=0)
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Clean and Format
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
        df = df.dropna(subset=['날짜'])
        
        # Numeric Force Conversion
        num_cols = ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간', '디커플링(%)']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['회차'] = df['회차'].astype(int)
        return df.sort_values("회차", ascending=False)
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

# 2. Gemini API Setup
try:
    import google.generativeai as genai
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        ai_model = genai.GenerativeModel('models/gemini-1.5-flash')
        gemini_ready = True
    else: gemini_ready = False
except: gemini_ready = False

# 3. Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Lexend:wght@300;500&display=swap');
    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    h1, h2, h3, p { color: #ffffff; font-family: 'Lexend', sans-serif; }
    div[data-testid="stMetricValue"] { color: #938172 !important; font-size: 2.2rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: #0c0c0e; padding: 8px 12px; border-radius: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #71717a; text-transform: uppercase; padding: 0 25px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border: 1px solid #938172 !important; }
    .summary-box { background-color: #0c0c0e; border: 1px solid #1c1c1f; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
    .recovery-badge { display: inline-block; background-color: #938172; color: #000000; padding: 2px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .section-title { color: #938172; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; border-left: 3px solid #938172; padding-left: 15px; margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

# 4. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = load_data(conn)

# 5. Sidebar
with st.sidebar:
    st.markdown("<h2 style='letter-spacing:0.1em;'>ZONE 2 LAB</h2>", unsafe_allow_html=True)
    if not df.empty:
        session_list = df["회차"].tolist()
        selected_session = st.selectbox("SESSION ARCHIVE", session_list, index=0)
        s_data = df[df["회차"] == selected_session].iloc[0].to_dict() # Dictionary 변환으로 참조 오류 방지
    else: s_data = None
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 6. Main Content
tab_entry, tab_analysis, tab_trends = st.tabs(["[ REGISTRATION ]", "[ PERFORMANCE ]", "[ PROGRESSION ]"])

# --- [TAB 1: REGISTRATION] ---
with tab_entry:
    st.markdown('<p class="section-title">Session Configuration</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    f_date = c1.date_input("Date", value=datetime.now().date())
    f_session = c2.number_input("Session No.", value=int(df["회차"].max() + 1) if not df.empty else 1, step=1)
    f_duration = c3.slider("Main Training Duration (min)", 15, 180, 60, step=5)
    
    p1, p2, p3 = st.columns(3)
    f_wp = p1.number_input("Warm-up Power (W)", value=100)
    f_mp = p2.number_input("Target Main (W)", value=140)
    f_cp = p3.number_input("Cool-down Power (W)", value=90)

    st.divider()
    st.markdown('<p class="section-title">Biometric Telemetry</p>', unsafe_allow_html=True)
    total_pts = ((10 + f_duration + 5) // 5) + 1
    hr_inputs = []
    
    # 세션 데이터에서 기존 심박수 가져오기 로직 안전화
    existing_raw = str(s_data.get('전체심박데이터', '')) if s_data else ''
    existing_hrs = [x.strip() for x in existing_raw.split(',')] if existing_raw else []
    
    h_cols = st.columns(4)
    for i in range(total_pts):
        with h_cols[i % 4]:
            val = int(float(existing_hrs[i])) if i < len(existing_hrs) and existing_hrs[i] else 130
            hr_val = st.number_input(f"T + {i*5}m HR", value=val, key=f"hr_v77_{i}", step=1)
            hr_inputs.append(str(int(hr_val)))

    if st.button("COMMIT PERFORMANCE DATA", use_container_width=True):
        main_hrs = [int(x) for x in hr_inputs[2:-1]]
        mid = len(main_hrs) // 2
        f_ef = f_mp / np.mean(main_hrs[:mid]) if mid > 0 else 0
        s_ef = f_mp / np.mean(main_hrs[mid:]) if mid > 0 else 0
        f_dec = round(((f_ef - s_ef) / f_ef) * 100, 2) if f_ef > 0 else 0
        
        new_row = {
            "날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session), 
            "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp), 
            "본훈련시간": int(f_duration), "디커플링(%)": f_dec, 
            "전체심박데이터": ", ".join(hr_inputs)
        }
        updated_df = pd.concat([df[df["회차"] != f_session], pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
        conn.update(data=updated_df)
        st.cache_data.clear()
        st.success("Cloud Database Updated.")
        st.rerun()

# --- [TAB 2: PERFORMANCE INTELLIGENCE] ---
with tab_analysis:
    if s_data:
        st.markdown(f"### Intelligence Briefing: Session {int(s_data['회차'])}")
        
        c_dec = float(s_data['디커플링(%)'])
        c_p = int(s_data['본훈련파워'])
        hr_raw = str(s_data['전체심박데이터']).split(',')
        hr_array = [int(float(x)) for x in hr_raw if x.strip()]
        avg_hr = np.mean(hr_array[2:-1]) if len(hr_array) > 2 else 1
        avg_ef = round(c_p / avg_hr, 2)
        
        recovery = "24 Hours" if c_dec < 5 else "36 Hours" if c_dec < 8 else "48 Hours+"
        
        st.markdown(f"""
        <div class="summary-box">
            <p style="color:#A1A1AA; font-style:italic;">Session {int(s_data['회차'])} at {c_p}W showed a {c_dec}% decoupling. Efficiency is at {avg_ef} EF.</p>
            <span class="recovery-badge">Recommended Recovery: {recovery}</span>
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Target Output", f"{c_p}W")
        m2.metric("Decoupling", f"{c_dec}%")
        m3.metric("Avg Pulse", f"{int(avg_hr)}bpm")
        m4.metric("Efficiency", f"{avg_ef}")

        col_graph, col_guide = st.columns([3, 1])
        
        with col_graph:
            time_x = [i*5 for i in range(len(hr_array))]
            main_dur = int(s_data['본훈련시간'])
            # Power Array Logic
            power_y = []
            for t in time_x:
                if t < 10: power_y.append(int(s_data['웜업파워']))
                elif t < 10 + main_dur: power_y.append(c_p)
                else: power_y.append(int(s_data['쿨다운파워']))
            
            ef_trend = [round(p/h, 2) if h > 0 else 0 for p, h in zip(power_y, hr_array)]

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.15,
                                specs=[[{"secondary_y": True}], [{"secondary_y": False}]])

            # Row 1
            fig.add_trace(go.Scatter(x=time_x, y=power_y, name="Power", line=dict(color='#938172', width=4, shape='hv'), fill='tozeroy', fillcolor='rgba(147, 129, 114, 0.05)'), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(x=time_x, y=hr_array, name="Heart Rate", line=dict(color='#F4F4F5', width=2, dash='dot')), row=1, col=1, secondary_y=True)
            # Row 2
            fig.add_trace(go.Scatter(x=time_x[2:-1], y=ef_trend[2:-1], name="Efficiency Drift", line=dict(color='#FF4D00', width=3)), row=2, col=1)

            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=650, margin=dict(l=0, r=0, t=20, b=0))
            
            # Axes Formatting
            fig.update_yaxes(title_text="Power (W)", titlefont=dict(color="#938172"), tickfont=dict(color="#938172"), row=1, col=1, secondary_y=False)
            fig.update_yaxes(title_text="HR (bpm)", titlefont=dict(color="#F4F4F5"), tickfont=dict(color="#F4F4F5"), row=1, col=1, secondary_y=True)
            fig.update_yaxes(title_text="Efficiency (EF)", titlefont=dict(color="#FF4D00"), tickfont=dict(color="#FF4D00"), row=2, col=1)
            st.plotly_chart(fig, use_container_width=True)

        with col_guide:
            st.markdown(f"""
            <div style="color:#71717a; font-size:0.85rem; padding:10px; border-left:1px solid #27272a; margin-top:60px;">
            <p><b style="color:#938172;">Copper Axis</b>: Power intensity.</p>
            <p><b style="color:#F4F4F5;">White Axis</b>: Heart rate response.</p>
            <p><b style="color:#FF4D00;">Magma Axis</b>: Efficiency Drift (Lower Chart).</p>
            </div>
            """, unsafe_allow_html=True)

        if gemini_ready:
            st.divider()
            if pr := st.chat_input("Discuss with Gemini Coach..."):
                with st.spinner("Reviewing your laps..."):
                    res = ai_model.generate_content(f"Analyze: Session {int(s_data['회차'])}, Power {c_p}W, Decoupling {c_dec}%. User asks: {pr}")
                    st.info(res.text)

# --- [TAB 3: PROGRESSION] ---
with tab_trends:
    if not df.empty:
        st.markdown('<p class="section-title">Aerobic Stability Trend</p>', unsafe_allow_html=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=df['날짜'], y=df['디커플링(%)'], mode='lines+markers', line=dict(color='#FF4D00', width=2), fill='tozeroy', fillcolor='rgba(255, 77, 0, 0.05)'))
        fig3.add_hline(y=5.0, line_dash="dash", line_color="#10b981", annotation_text="Optimal")
        fig3.update_layout(template="plotly_dark", height=350, yaxis_title="Decoupling (%)")
        st.plotly_chart(fig3, use_container_width=True)
