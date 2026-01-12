import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정 및 데이터 연결
st.set_page_config(page_title="Zone 2 Precision Lab", layout="wide")

# 구글 시트 연결 (ttl=0으로 실시간 데이터 반영)
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 데이터 전처리: 주요 수치들을 정수형으로 변환하여 .0 제거
if not df.empty:
    for col in ['회차', '웜업파워', '본훈련파워', '쿨다운파워', '본훈련시간']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 2. 사이드바: 기록 조회 및 실시간 입력/수정
with st.sidebar:
    st.header("⚙️ 훈련 데이터 관리")
    mode = st.radio("작업 선택", ["기존 기록 조회/수정", "🆕 새로운 회차 기록"])
    st.divider()
    
    if mode == "기존 기록 조회/수정" and not df.empty:
        sessions = sorted(df["회차"].unique().tolist())
        selected_session = st.selectbox("회차 선택", sessions, index=len(sessions)-1)
        s_data = df[df["회차"] == selected_session].iloc[0]
        btn_label = "데이터 수정 및 저장"
    else:
        # 새 회차 자동 계산
        next_session = int(df["회차"].max() + 1) if not df.empty else 1
        s_data = None
        selected_session = next_session
        btn_label = "🚀 새로운 훈련 데이터 저장"

    with st.form(key="training_input_form"):
        st.subheader(f"📝 {int(selected_session)}회차 기록")
        f_date = st.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now())
        f_session = st.number_input("회차 번호", value=int(selected_session), step=1)
        
        col1, col2, col3 = st.columns(3)
        f_wp = col1.number_input("웜업W", value=int(s_data['웜업파워']) if s_data is not None else 97, step=1)
        f_mp = col2.number_input("본훈련W", value=int(s_data['본훈련파워']) if s_data is not None else 140, step=1)
        f_cp = col3.number_input("쿨다운W", value=int(s_data['쿨다운파워']) if s_data is not None else 90, step=1)
        
        f_duration = st.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 90, step=5)
        
        # 동적 심박수 입력 필드 (정수 처리)
        num_main = f_duration // 5
        total_steps = 2 + num_main + 1
        existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
        
        st.write(f"💓 심박 데이터 ({total_steps}개 지점)")
        hr_inputs = []
        h_cols = st.columns(3)
        for i in range(total_steps):
            try:
                def_hr = int(float(existing_hrs[i].strip())) if i < len(existing_hrs) else 130
            except:
                def_hr = 130
                
            with h_cols[i % 3]:
                hr_val = st.number_input(f"{i*5}분", value=def_hr, key=f"hr_input_{i}", step=1)
                hr_inputs.append(str(int(hr_val)))
        
        if st.form_submit_button(btn_label):
            # 디커플링 계산 (본훈련 구간)
            main_hrs = [int(x) for x in hr_inputs[2:-1]]
            mid = len(main_hrs) // 2
            f_ef_val = f_mp / np.mean(main_hrs[:mid])
            s_ef_val = f_mp / np.mean(main_hrs[mid:])
            f_dec = round(((f_ef_val - s_ef_val) / f_ef_val) * 100, 2)
            
            new_row = {
                "날짜": f_date.strftime("%Y-%m-%d"),
                "회차": int(f_session),
                "웜업파워": int(f_wp),
                "본훈련파워": int(f_mp),
                "쿨다운파워": int(f_cp),
                "본훈련시간": int(f_duration),
                "디커플링(%)": f_dec,
                "전체심박데이터": ", ".join(hr_inputs)
            }
            
            if not df.empty:
                df = df[df["회차"] != f_session]
            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
            conn.update(data=updated_df)
            st.success(f"✅ {int(f_session)}회차 데이터 저장 완료!")
            st.balloons()
            st.rerun()

# 4. 메인 분석 대시보드
if not df.empty and s_data is not None:
    st.title(f"📊 Session {int(s_data['회차'])} 분석 리포트")
    
    tab1, tab2 = st.tabs(["🎯 오늘의 훈련 분석", "📈 장기 성장 추이"])

    with tab1:
        # --- AI Coach Headline ---
        st.markdown("### 🤖 AI Coach's Daily Briefing")
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        max_hr = int(max(hr_array))
        current_dec = s_data['디커플링(%)']
        current_p = int(s_data['본훈련파워'])
        
        if current_dec <= 5.0:
            headline = f"🔥 **완벽한 제어 상태입니다.** 디커플링 {current_dec}%로 심폐 효율이 안정적이니, {current_p + 5}W로 엔진을 확장할 시점입니다!"
        elif current_dec <= 8.0 and max_hr < 170:
            headline = f"✅ **엔진 확장 가능성이 높습니다.** 디커플링({current_dec}%)이 소폭 있으나 최대심박({max_hr}bpm)이 잘 통제되고 있습니다. 다음 세션은 {current_p + 5}W 도전을 추천합니다!"
        else:
            headline = f"⏳ **현재 구간 적응이 더 필요합니다.** 심박 표류({current_dec}%)가 관찰되니, {current_p}W를 반복하여 제어력을 완벽히 확보합시다."
        st.info(headline)

        # 주요 지표 카드
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("훈련 파워", f"{current_p} W")
        dec_color = "normal" if current_dec <= 5.0 else "inverse"
        m2.metric("디커플링", f"{current_dec}%", delta="- 안정" if current_dec <= 5.0 else "+ 주의", delta_color=dec_color)
        m3.metric("최대 심박", f"{max_hr} BPM")
        m4.metric("훈련 시간", f"{int(s_data['본훈련시간'])} 분")

        st.divider()

        # --- 정밀 시퀀스 분석 그래프 (105분 데이터 완벽 대응) ---
        time_array = [i*5 for i in range(len(hr_array))]
        wp, mp, cp = int(s_data['웜업파워']), int(s_data['본훈련파워']), int(s_data['쿨다운파워'])
        
        # 파워 어레이 로직: 타임 어레이 길이와 100% 일치시켜 마지막 포인트 유실 방지
        power_array = []
        num_main_end_idx = 2 + (int(s_data['본훈련시간']) // 5)
        for i in range(len(time_array)):
            if i < 2: power_array.append(wp)
            elif i < num_main_end_idx: power_array.append(mp)
            else: power_array.append(cp)

        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=time_array, y=power_array, name="Power (W)", line=dict(color='cyan', width=3, shape='hv'), fill='tozeroy', fillcolor='rgba(0, 255, 255, 0.1)'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_array, y=hr_array, name="HR (BPM)", line=dict(color='red', width=4, shape='spline')), secondary_y=True)
        
        m_end_time = int(s_data['본훈련시간']) + 10
        fig1.add_vrect(x0=0, x1=10, fillcolor="gray", opacity=0.1, annotation_text="WU")
        fig1.add_vrect(x0=10, x1=m_end_time, fillcolor="blue", opacity=0.05, annotation_text="Main")
        fig1.add_vrect(x0=m_end_time, x1=time_array[-1], fillcolor="gray", opacity=0.1, annotation_text="CD")
        fig1.update_layout(template="plotly_dark", height=500, hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig1, use_container_width=True)
        st.caption("**💡 그래프 해석:** 파란색 면적은 목표 파워(W)이며, 빨간색 선은 심박수(BPM)의 변화입니다. 본 훈련 구간에서 심박수 선이 파워 면적과 평행을 유지할수록 유산소 기초가 탄탄함을 의미합니다.")

        # --- Cardiac Drift 분석 ---
        st.subheader("🎯 Cardiac Drift 시각적 분석 (전반 vs 후반)")
        main_hrs = hr_array[2:-1]
        mid = len(main_hrs) // 2
        f_half, s_half = main_hrs[:mid], main_hrs[mid:]
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(y=f_half, name='전반부 (Stability)', line=dict(color='cyan', width=2)))
        fig2.add_trace(go.Scatter(y=s_half, name='후반부 (Drift)', line=dict(color='red', width=2), fill='tonexty', fillcolor='rgba(255, 0, 0, 0.1)'))
        fig2.update_layout(template="plotly_dark", height=350, margin=dict(l=20, r=20, t=10, b=10))
        
        cola, colb = st.columns([2, 1])
        with cola: st.plotly_chart(fig2, use_container_width=True)
        with colb:
            drift_val = np.mean(s_half) - np.mean(f_half)
            st.metric("심박 상승 폭", f"+{drift_val:.1f} bpm", delta=f"{current_dec}%", delta_color="inverse")
            st.caption(f"**분석:** 동일한 {int(mp)}W 파워에서 전/후반 심박 차이를 분석합니다. 5% 이내 유지가 목표입니다.")

    with tab2:
        # --- 목표 달성률 게이지 ---
        target_w = 160
        progress = min(current_p / target_w, 1.0)
        st.subheader(f"🏁 최종 목표({target_w}W) 달성률: {progress*100:.1f}%")
        st.progress(progress)
        
        st.divider()

        # --- 장기 지표 (EF & HRR) ---
        c_left, c_right = st.columns(2)
        with c_left:
            st.subheader("📈 유산소 효율성(EF) 추이")
            def calc_ef_func(row):
                hrs = [float(x.strip()) for x in str(row['전체심박데이터']).split(",")]
                return int(row['본훈련파워']) / np.mean(hrs[2:-1])
            t_df = df.copy()
            t_df['EF'] = t_df.apply(calc_ef_func, axis=1)
            fig3 = go.Figure(go.Scatter(x=t_df['회차'], y=t_df['EF'], mode='lines+markers', line=dict(color='springgreen', width=3)))
            fig3.update_layout(template="plotly_dark", height=350, xaxis=dict(dtick=1))
            st.plotly_chart(fig3, use_container_width=True)
            st.info("**EF(Efficiency Factor):** 수치가 우상향할수록 동일 심박에서 더 높은 파워를 내고 있다는 뜻입니다.")
        with c_right:
            st.subheader("💓 심박 회복력 (HRR)")
            def calc_hrr_func(row):
                hrs = [float(x.strip()) for x in str(row['전체심박데이터']).split(",")]
                return int(hrs[-2] - hrs[-1])
            h_df = df.copy()
            h_df['HRR'] = h_df.apply(calc_hrr_func, axis=1)
            fig4 = go.Figure(go.Bar(x=h_df['회차'], y=h_df['HRR'], marker_color='orange'))
            fig4.update_layout(template="plotly_dark", height=350, xaxis=dict(dtick=1))
            st.plotly_chart(fig4, use_container_width=True)
            st.info("**HRR(Heart Rate Recovery):** 훈련 종료 직후 심박이 떨어지는 속도입니다. 높을수록 심폐 회복력이 좋습니다.")
