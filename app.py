import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Zone 2 Precision Step-Power Lab", layout="wide")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 3. 사이드바 (조회 및 입력)
with st.sidebar:
    st.header("🔍 데이터 조회 및 기록")
    if not df.empty:
        sessions = sorted(df["회차"].unique().tolist())
        selected_session = st.selectbox("조회할 회차 선택", sessions, index=len(sessions)-1)
        s_data = df[df["회차"] == selected_session].iloc[0]
    else:
        selected_session = 1
        s_data = None

    st.divider()
    with st.form(key="sequence_form"):
        st.subheader(f"📝 {selected_session}회차 데이터 관리")
        # 입력 필드들 (필요시 수정 가능)
        w_p = st.number_input("웜업 파워(W)", value=int(s_data['웜업파워']) if s_data is not None else 97)
        main_p = st.number_input("본 훈련 파워(W)", value=int(s_data['본훈련파워']) if s_data is not None else 135)
        c_p = st.number_input("쿨다운 파워(W)", value=int(s_data['쿨다운파워']) if s_data is not None else 107)
        st.form_submit_button("변경사항 저장")

# 4. 메인 분석 대시보드
if not df.empty and s_data is not None:
    st.title(f"📊 Session {selected_session} 정밀 시퀀스 분석")
    
    # 데이터 파싱
    hr_array = [float(x.strip()) for x in str(s_data['전체심박데이터']).split(",")]
    wp, mp, cp = s_data['웜업파워'], s_data['본훈련파워'], s_data['쿨다운파워']
    
    # 5분 단위 시간 축 생성
    time_array = [i*5 for i in range(len(hr_array))]
    
    # --- 스텝 차트용 파워 배열 구성 ---
    # 인덱스 0, 1: 웜업 (0분, 5분) -> 파워 wp
    # 인덱스 2 ~ (마지막-1): 본 훈련 (10분 ~ 마지막 전) -> 파워 mp
    # 인덱스 (마지막): 쿨다운 (마지막 시점) -> 파워 cp
    # 'hv' 모드에서는 현재 인덱스의 값을 다음 인덱스 직전까지 유지함
    power_array = [wp, wp] + [mp] * (len(hr_array) - 3) + [cp]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. 파워 그래프 (Step-Up & Step-Down 구현)
    fig.add_trace(
        go.Scatter(
            x=time_array, 
            y=power_array, 
            name="Actual Power (W)",
            line=dict(color='rgba(0, 223, 216, 1.0)', width=3, shape='hv'), # 수직/수평 전환 핵심
            fill='tozeroy',
            fillcolor='rgba(0, 223, 216, 0.15)'
        ),
        secondary_y=False
    )

    # 2. 심박수 그래프 (생체 반응이므로 부드러운 곡선)
    fig.add_trace(
        go.Scatter(
            x=time_array, 
            y=hr_array, 
            name="Heart Rate (BPM)",
            line=dict(color='#ff4b4b', width=4, shape='spline')
        ),
        secondary_y=True
    )

    # 구간 시각적 가이드 (수직 점선)
    main_start = 10
    main_end = time_array[-2]
    
    # 웜업/본훈련/쿨다운 영역 배경색 구분
    fig.add_vrect(x0=0, x1=main_start, fillcolor="gray", opacity=0.1, layer="below", line_width=0, annotation_text="WU")
    fig.add_vrect(x0=main_start, x1=main_end, fillcolor="blue", opacity=0.05, layer="below", line_width=0, annotation_text="Main Set")
    fig.add_vrect(x0=main_end, x1=max(time_array), fillcolor="gray", opacity=0.1, layer="below", line_width=0, annotation_text="CD")

    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=50, r=50, t=80, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        hovermode="x unified"
    )

    fig.update_xaxes(title_text="Time (minutes)", showgrid=False)
    fig.update_yaxes(title_text="<b>Power</b> (Watts)", secondary_y=False, range=[0, max(power_array)*1.25], showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="<b>Heart Rate</b> (BPM)", secondary_y=True, range=[min(hr_array)-10, max(hr_array)+10], showgrid=False)

    st.plotly_chart(fig, use_container_width=True)
    
    # 분석 요약
    st.info(f"💡 본 훈련 구간 ({main_start}분~{main_end}분) 디커플링 분석 결과: **{s_data['디커플링(%)']}%**")
