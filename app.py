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

# 2. 사이드바: 입력 인터페이스 (필요할 때만 사용하도록 구성)
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
        next_session = int(df["회차"].max() + 1) if not df.empty else 1
        s_data = None
        selected_session = next_session
        btn_label = "🚀 새로운 훈련 데이터 저장"

    with st.form(key="training_input_form"):
        st.subheader(f"📝 {int(selected_session)}회차 기록")
        f_date = st.date_input("날짜", value=pd.to_datetime(s_data['날짜']) if s_data is not None else pd.Timestamp.now())
        f_session = st.number_input("회차 번호", value=int(selected_session), step=1)
        
        c1, c2, c3 = st.columns(3)
        f_wp = c1.number_input("웜업W", value=int(s_data['웜업파워']) if s_data is not None else 97, step=1)
        f_mp = c2.number_input("본훈련W", value=int(s_data['본훈련파워']) if s_data is not None else 140, step=1)
        f_cp = c3.number_input("쿨다운W", value=int(s_data['쿨다운파워']) if s_data is not None else 90, step=1)
        
        f_duration = st.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 90, step=5)
        
        # 심박수 일괄 입력 안내 및 동적 필드
        num_main = f_duration // 5
        total_steps = 2 + num_main + 1
        existing_hrs = str(s_data['전체심박데이터']).split(",") if s_data is not None else []
        
        st.write(f"💓 심박수 입력 ({total_steps}개 지점)")
        hr_inputs = []
        h_cols = st.columns(3)
        for i in range(total_steps):
            try:
                def_hr = int(float(existing_hrs[i].strip())) if i < len(existing_hrs) else 130
            except: def_hr = 130
            with h_cols[i % 3]:
                hr_val = st.number_input(f"{i*5}분", value=def_hr, key=f"hr_input_{i}", step=1)
                hr_inputs.append(str(int(hr_val)))
        
        if st.form_submit_button(btn_label):
            main_hrs = [int(x) for x in hr_inputs[2:-1]]
            mid = len(main_hrs) // 2
            f_ef_val = f_mp / np.mean(main_hrs[:mid])
            s_ef_val = f_mp / np.mean(main_hrs[mid:])
            f_dec = round(((f_ef_val - s_ef_val) / f_ef_val) * 100, 2)
            
            new_row = {
                "날짜": f_date.strftime("%Y-%m-%d"), "회차": int(f_session),
                "웜업파워": int(f_wp), "본훈련파워": int(f_mp), "쿨다운파워": int(f_cp),
                "본훈련시간": int(f_duration), "디커플링(%)": f_dec, "전체심박데이터": ", ".join(hr_inputs)
            }
            if not df.empty: df = df[df["회차"] != f_session]
            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).sort_values("회차")
            conn.update(data=updated_df)
            st.success("✅ 저장 완료!")
            st.rerun()

# 3. 메인 분석 대시보드 (UX 개선 반영)
if not df.empty and s_data is not None:
    st.title(f"📊 Session {int(s_data['회차'])} 분석 리포트")
    
    # [개선 1] 탭 구조 도입
    tab1, tab2 = st.tabs(["🎯 오늘의 훈련 분석", "📈 장기 성장 추이"])

    with tab1:
        # AI 코치 헤드라인
        hr_array = [int(float(x.strip())) for x in str(s_data['전체심박데이터']).split(",")]
        current_dec = s_data['디커플링(%)']
        current_p = int(s_data['본훈련파워'])
        max_hr = int(max(hr_array))

        if current_dec <= 5.0:
            st.success(f"🤖 **AI 코치:** 완벽한 제어 상태입니다! {current_p + 5}W로 확장을 추천합니다.")
        elif current_dec <= 8.0:
            st.warning(f"🤖 **AI 코치:** 엔진 확장 가능성이 보입니다. 심박 통제에 집중하며 {current_p + 5}W에 도전해보세요.")
        else:
            st.error(f"🤖 **AI 코치:** 현재 구간({current_p}W) 적응이 더 필요합니다. 반복 훈련을 권장합니다.")

        # [개선 2] 조건부 컬러 메트릭 카드
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("훈련 파워", f"{current_p} W")
        
        # 디커플링 상태에 따른 색상 시각화
        dec_color = "normal" if current_dec <= 5.0 else "inverse"
        m2.metric("디커플링", f"{current_dec}%", delta="- 안정" if current_dec <= 5.0 else "+ 주의", delta_color=dec_color)
        m3.metric("최대 심박", f"{max_hr} BPM")
        m4.metric("훈련 시간", f"{int(s_data['본훈련시간'])} 분")

        st.divider()

        # 그래프 배치 (시퀀스 분석)
        time_array = [i*5 for i in range(len(hr_array))]
        power_array = [int(s_data['웜업파워'])]*2 + [current_p]*(int(s_data['본훈련시간'])//5) + [int(s_data['쿨다운파워'])]
        
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=time_array, y=power_array, name="Power", line=dict(color='cyan', width=3, shape='hv'), fill='tozeroy'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=time_array, y=hr_array, name="HR", line=dict(color='red', width=4)), secondary_y=True)
        fig1.update_layout(template="plotly_dark", height=450, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig1, use_container_width=True)
        st.caption("**💡 시퀀스 해석:** 파워(하늘색 면적) 대비 심박(빨간 선)이 평행하게 유지되는지 확인하세요. 후반부에 빨간 선이 위로 치솟는다면 유산소 부하가 한계에 도달한 것입니다.")

        # Drift 분석
        st.subheader("🎯 Cardiac Drift (전반 vs 후반)")
        main_hrs = hr_array[2:-1]
        mid = len(main_hrs) // 2
        f_h, s_h = main_hrs[:mid], main_hrs[mid:]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(y=f_h, name='전반부', line=dict(color='cyan')))
        fig2.add_trace(go.Scatter(y=s_h, name='후반부', line=dict(color='red'), fill='tonexty'))
        fig2.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        # [개선 3] 최종 목표 달성률 시각화
        target_w = 160
        progress = min(current_p / target_w, 1.0)
        st.subheader(f"🏁 최종 목표({target_w}W) 달성률: {progress*100:.1f}%")
        st.progress(progress)
        st.write(f"현재 **{current_p}W** 구간에서 훈련 중입니다. 목표까지 **{target_w - current_p}W** 남았습니다!")
        
        st.divider()

        # 장기 지표 트렌드 (EF & HRR)
        c_left, c_right = st.columns(2)
        with c_left:
            st.subheader("📈 유산소 효율(EF) 추이")
            def get_ef(r): return int(r['본훈련파워']) / np.mean([float(x) for x in str(r['전체심박데이터']).split(",")][2:-1])
            df_ef = df.copy(); df_ef['EF'] = df_ef.apply(get_ef, axis=1)
            fig_ef = go.Figure(go.Scatter(x=df_ef['회차'], y=df_ef['EF'], mode='lines+markers', line=dict(color='springgreen')))
            fig_ef.update_layout(template="plotly_dark", height=350, xaxis=dict(dtick=1))
            st.plotly_chart(fig_ef, use_container_width=True)
            st.info("성장할수록 '더 낮은 심박으로 더 높은 파워'를 내게 되어 EF 수치가 우상향합니다.")

        with c_right:
            st.subheader("💓 심박 회복력(HRR) 추이")
            def get_hrr(r): 
                hrs = [float(x) for x in str(r['전체심박데이터']).split(",")]
                return int(hrs[-2] - hrs[-1])
            df_hrr = df.copy(); df_hrr['HRR'] = df_hrr.apply(get_hrr, axis=1)
            fig_hrr = go.Figure(go.Bar(x=df_hrr['회차'], y=df_hrr['HRR'], marker_color='orange'))
            fig_hrr.update_layout(template="plotly_dark", height=350, xaxis=dict(dtick=1))
            st.plotly_chart(fig_hrr, use_container_width=True)
            st.info("훈련 직후 심박수가 빠르게 떨어질수록(높은 막대) 심폐 회복 능력이 뛰어난 상태입니다.")
