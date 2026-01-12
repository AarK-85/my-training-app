import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# (기존 라이브러리 로드 부분...)

if not df.empty and s_data is not None:
    # --- [NEW] AI 코치 헤드라인 섹션 ---
    st.markdown("### 🤖 AI Coach's Daily Briefing")
    
    # 분석 데이터 준비
    hr_array = [float(x.strip()) for x in str(s_data['전체심박데이터']).split(",")]
    max_hr = max(hr_array)
    current_dec = s_data['디커플링(%)']
    current_p = s_data['본훈련파워']
    
    # 기승전결 문구 생성 로직
    if current_dec <= 5.0:
        status = "완벽한 유산소 제어 상태입니다."
        reason = f"디커플링 {current_dec}%로 심폐 효율이 매우 안정적이며,"
        action = f"이제 자신감을 갖고 {current_p + 5}W로 강도를 높여 엔진을 확장할 시점입니다!"
    elif current_dec <= 8.0 and max_hr < 170: # 17회차 케이스 (5.8% 이지만 심박 제어 양호)
        status = "엔진 확장 가능성이 확인되었습니다."
        reason = f"디커플링({current_dec}%)이 기준을 근소하게 상회하나, 최대심박({max_hr}bpm)이 안정 범위 내에서 통제되고 있으므로,"
        action = f"다음 세션은 {current_p + 5}W로 스텝 업하여 새로운 자극을 주어도 좋습니다!"
    else:
        status = "현재 구간에서의 적응이 더 필요합니다."
        reason = f"심박 표류({current_dec}%)가 관찰되어 아직 유산소 베이스를 다지는 단계이므로,"
        action = f"조급해하기보다 {current_p}W를 2~3회 더 반복하여 심박 제어력을 완벽히 확보합시다."

    # 헤드라인 출력 (스타일 적용)
    st.info(f"**{status}** {reason} {action}")
    st.divider()

    # (이후 그래프 및 상세 분석 로직 계속...)

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Final Precision Lab", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 3. 사이드바 (조회 및 입력)
with st.sidebar:
    st.header("🔍 데이터 관리")
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist())
        selected_session = st.selectbox("조회할 회차 선택", sessions, index=len(sessions)-1)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else:
        selected_session = 1
        s_data = None

    st.divider()
    with st.form(key="recovery_form"):
        st.subheader(f"📝 {selected_session}회차 기록 수정")
        
        # 파워 설정
        w_p = st.number_input("웜업W", value=int(s_data['웜업파워']) if s_data is not None else 97)
        main_p = st.number_input("본훈련W", value=int(s_data['본훈련파워']) if s_data is not None else 135)
        c_p = st.number_input("쿨다운W", value=int(s_data['쿨다운파워']) if s_data is not None else 90) # 17회차 쿨다운 90W 반영
        
        # 가변 본 훈련 시간 (17회차는 90분)
        duration = st.slider("본 훈련 시간(분)", 15, 180, int(s_data['본훈련시간']) if s_data is not None else 90, step=5)
        
        # --- 심박수 입력칸 (데이터 유실 방지 로직) ---
        num_main_steps = duration // 5
        total_steps = 2 + num_main_steps + 1 # 웜업2 + 본훈련N + 쿨다운1
        
        existing_hrs = [x.strip() for x in str(s_data['전체심박데이터']).split(",")] if s_data is not None else []
        
        st.subheader(f"💓 심박 데이터 (총 {total_steps}개)")
        hr_inputs = []
        cols = st.columns(3)
        for i in range(total_steps):
            t = i * 5
            # 기존 데이터가 있으면 로드, 없으면 130 기본값
            default_val = float(existing_hrs[i]) if i < len(existing_hrs) else 130.0
            with cols[i % 3]:
                hr_val = st.number_input(f"{t}분 시점", value=default_val, key=f"hr_input_{i}")
                hr_inputs.append(str(hr_val))
        
        if st.form_submit_button("기록 업데이트"):
            full_hr_str = ", ".join(hr_inputs)
            # 디커플링 및 저장 로직 (생략)
            st.rerun()

# 4. 메인 분석 대시보드
if not df.empty and s_data is not None:
    st.title(f"📊 Session {selected_session} 시퀀스 정밀 분석")
    
    hr_array = [float(x.strip()) for x in str(s_data['전체심박데이터']).split(",")]
    time_array = [i*5 for i in range(len(hr_array))]
    wp, mp, cp = s_data['웜업파워'], s_data['본훈련파워'], s_data['쿨다운파워']
    
    # --- 가변적 파워 스텝 로직 (105분 심박수 반영) ---
    # 17회차 기준: 0~5분(WU), 10~95분(Main), 100~105분(CD)
    # 100분 지점에서 수직 낙하하려면 100분 데이터부터 cp로 설정되어야 함
    power_array = []
    num_main_end_idx = 2 + (s_data['본훈련시간'] // 5) # 본훈련이 끝나는 인덱스 (100분 지점)
    
    for i in range(len(time_array)):
        if i < 2: # 0, 5분
            power_array.append(wp)
        elif i < num_main_end_idx: # 10분 ~ 본훈련 종료 직전까지
            power_array.append(mp)
        else: # 본훈련 종료 시점(수직 낙하 시작)부터 마지막(105분)까지
            power_array.append(cp)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. 파워 스텝 그래프
    fig.add_trace(go.Scatter(
        x=time_array, y=power_array, name="Target Power (W)",
        line=dict(color='rgba(0, 223, 216, 1.0)', width=3, shape='hv'),
        fill='tozeroy', fillcolor='rgba(0, 223, 216, 0.1)'
    ), secondary_y=False)
    
    # 2. 심박수 그래프 (105분 데이터 포함)
    fig.add_trace(go.Scatter(
        x=time_array, y=hr_array, name="Heart Rate (BPM)",
        line=dict(color='#ff4b4b', width=4, shape='spline')
    ), secondary_y=True)

    # 배경 구간 가이드
    m_end_time = s_data['본훈련시간'] + 10 # 웜업 10분 포함
    fig.add_vrect(x0=0, x1=10, fillcolor="gray", opacity=0.1, annotation_text="WU")
    fig.add_vrect(x0=10, x1=m_end_time, fillcolor="blue", opacity=0.05, annotation_text="Main")
    fig.add_vrect(x0=m_end_time, x1=time_array[-1], fillcolor="gray", opacity=0.1, annotation_text="CD")

    fig.update_layout(template="plotly_dark", height=600, hovermode="x unified")
    fig.update_yaxes(range=[0, 200], secondary_y=False)
    fig.update_yaxes(range=[min(hr_array)-10, max(hr_array)+10], secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"💡 105분 시점 최종 심박수: **{hr_array[-1]} BPM** / 디커플링: **{s_data['디커플링(%)']}%**")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 4. 메인 분석 대시보드
if not df.empty and s_data is not None:
    st.title(f"📊 Session {selected_session} 정밀 분석")
    
    # 데이터 파싱
    hr_array = [float(x.strip()) for x in str(s_data['전체심박데이터']).split(",")]
    time_array = [i*5 for i in range(len(hr_array))]
    wp, mp, cp = s_data['웜업파워'], s_data['본훈련파워'], s_data['쿨다운파워']
    
    # 1️⃣ 첫 번째 그래프: 전체 시퀀스 (이미 구현된 스텝 파워 그래프)
    # (중략 - 이전 코드의 fig1 로직)

    st.divider()

    # 2️⃣ 두 번째 그래프: Cardiac Drift 시각화 (Power/HR Correlation)
    st.subheader("🎯 Cardiac Drift 시각적 분석 (전반 vs 후반)")
    
    # 본 훈련 데이터만 추출 (웜업 2개, 쿨다운 1개 제외)
    main_hrs = hr_array[2:-1]
    main_times = time_array[2:-1]
    mid_point = len(main_hrs) // 2
    
    first_half_hr = main_hrs[:mid_point]
    second_half_hr = main_hrs[mid_point:]
    
    # 시각적 비교를 위한 Scatter + Trendline 그래프
    fig2 = go.Figure()

    # 전반부 데이터 (파란색)
    fig2.add_trace(go.Scatter(
        x=list(range(len(first_half_hr))), 
        y=first_half_hr,
        mode='lines+markers',
        name='1st Half HR (Stability)',
        line=dict(color='#00dfd8', width=2),
        marker=dict(size=8)
    ))

    # 후반부 데이터 (빨간색)
    fig2.add_trace(go.Scatter(
        x=list(range(len(second_half_hr))), 
        y=second_half_hr,
        mode='lines+markers',
        name='2nd Half HR (Drift)',
        line=dict(color='#ff4b4b', width=2),
        marker=dict(size=8)
    ))

    # 드리프트 영역 채우기 (두 라인 사이의 간격이 곧 피로도와 효율 저하를 의미)
    fig2.add_trace(go.Scatter(
        x=list(range(len(second_half_hr))),
        y=second_half_hr,
        fill='tonexty',
        fillcolor='rgba(255, 75, 75, 0.1)',
        line=dict(width=0),
        name='Drift Area',
        showlegend=False
    ))

    fig2.update_layout(
        template="plotly_dark",
        title=f"동일 파워({mp}W)에서의 심박수 변화 비교",
        xaxis_title="구간 내 경과 시간 (5분 단위)",
        yaxis_title="Heart Rate (BPM)",
        height=450,
        hovermode="x unified"
    )
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.plotly_chart(fig2, use_container_width=True)
    with col_b:
        # 수치 기반 요약
        f_avg = np.mean(first_half_hr)
        s_avg = np.mean(second_half_hr)
        drift_bpm = s_avg - f_avg
        
        st.write("### 📈 Drift 리포트")
        st.metric("전반부 평균 심박", f"{f_avg:.1f} bpm")
        st.metric("후반부 평균 심박", f"{s_avg:.1f} bpm")
        st.metric("심박 상승 폭", f"+{drift_bpm:.1f} bpm", delta=f"{s_data['디커플링(%)']}%", delta_color="inverse")
        
        if s_data['디커플링(%)'] > 5.0:
            st.error("🚨 디커플링이 5%를 초과했습니다. 유산소 베이스 보강이 필요합니다.")
        else:
            st.success("✅ 유산소 엔진이 안정적입니다. 다음 단계로 나아갈 준비가 되었습니다.")

# 5. 전체 효율성(EF) 추이 분석
st.divider()
st.subheader("📈 유산소 효율성(EF) 장기 추이")

if not df.empty:
    # EF 계산 (본훈련파워 / 본훈련평균심박)
    # 전체 심박 데이터에서 본훈련 구간만 추출하여 평균 계산
    def calculate_main_hr_avg(row):
        try:
            hrs = [float(x.strip()) for x in str(row['전체심박데이터']).split(",")]
            main_hrs = hrs[2:-1] # 웜업2, 쿨다운1 제외
            return np.mean(main_hrs)
        except:
            return np.nan

    # 추이 분석용 임시 데이터프레임 생성
    trend_df = df.copy()
    trend_df['본훈련평균심박'] = trend_df.apply(calculate_main_hr_avg, axis=1)
    trend_df['EF'] = trend_df['본훈련파워'] / trend_df['본훈련평균심박']
    
    # EF 추이 그래프
    fig3 = go.Figure()
    
    # EF 라인
    fig3.add_trace(go.Scatter(
        x=trend_df['회차'], 
        y=trend_df['EF'],
        mode='lines+markers',
        name='Efficiency Factor (EF)',
        line=dict(color='#00df8a', width=3),
        marker=dict(size=10, symbol='diamond')
    ))

    # 추세선 (상향 곡선 확인용)
    z = np.polyfit(trend_df['회차'], trend_df['EF'], 1)
    p = np.poly1d(z)
    fig3.add_trace(go.Scatter(
        x=trend_df['회차'], 
        y=p(trend_df['회차']),
        name='성장 추세선',
        line=dict(color='rgba(255, 255, 255, 0.3)', dash='dash')
    ))

    fig3.update_layout(
        template="plotly_dark",
        height=400,
        xaxis_title="훈련 회차 (Session)",
        yaxis_title="Efficiency Factor (W/bpm)",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig3, use_container_width=True)

    # EF 분석 코멘트
    current_ef = trend_df['EF'].iloc[-1]
    initial_ef = trend_df['EF'].iloc[0]
    improvement = ((current_ef - initial_ef) / initial_ef) * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("현재 EF", f"{current_ef:.2f}")
    c2.metric("초기 대비 개선율", f"{improvement:+.1f}%")
    c3.write(f"**AI 코치 분석:** {'엔진 효율이 상승 중입니다! 파워 상향을 고려해 보세요.' if improvement > 5 else '기초 유산소 다지기 단계입니다.'}")

# (앞부분 EF 추이 로직 하단에 추가)

st.divider()
st.subheader("💓 심박 회복력 (HR Recovery) 분석")

if not df.empty:
    def calculate_hrr(row):
        try:
            hrs = [float(x.strip()) for x in str(row['전체심박데이터']).split(",")]
            # 본 훈련 종료 직전 심박 (마지막에서 두 번째 점)
            main_end_hr = hrs[-2]
            # 쿨다운 5분 후 심박 (마지막 점)
            cd_5min_hr = hrs[-1]
            return main_end_hr - cd_5min_hr
        except:
            return np.nan

    # HRR 계산 및 데이터프레임 적용
    hrr_df = df.copy()
    hrr_df['HRR'] = hrr_df.apply(calculate_hrr, axis=1)
    
    # HRR 추이 그래프
    fig4 = go.Figure()
    
    # HRR 바 차트 (회복량은 높을수록 좋음)
    fig4.add_trace(go.Bar(
        x=hrr_df['회차'], 
        y=hrr_df['HRR'],
        name='HR Recovery (1min/5min)',
        marker_color='rgba(255, 165, 0, 0.7)',
        text=hrr_df['HRR'].astype(int),
        textposition='outside'
    ))

    # 목표선 (보통 20~30 이상이면 우수)
    fig4.add_hline(y=20, line_dash="dot", line_color="rgba(255, 255, 255, 0.5)", annotation_text="Good Recovery")

    fig4.update_layout(
        template="plotly_dark",
        height=400,
        xaxis_title="훈련 회차 (Session)",
        yaxis_title="심박 하강 폭 (BPM)",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig4, use_container_width=True)

    # HRR 분석 코멘트
    latest_hrr = hrr_df['HRR'].iloc[-1]
    avg_hrr = hrr_df['HRR'].mean()
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("최근 세션 회복량", f"{latest_hrr:.0f} BPM")
    with c2:
        if latest_hrr > avg_hrr:
            st.success(f"평균({avg_hrr:.1f})보다 회복 속도가 빠릅니다! 심장 근육이 강화되고 있습니다.")
        else:
            st.warning(f"누적 피로도가 있을 수 있습니다. 충분한 휴식을 고려하세요.")

    st.caption("※ HRR(Heart Rate Recovery): 본 훈련 종료 직후부터 5분간 심박수가 얼마나 떨어졌는지를 측정합니다. 수치가 높을수록 유산소 기초 체력이 우수함을 의미합니다.")
