# 스타일 부분(CSS)만 이 내용으로 교체하거나, 전체 코드를 확인해 보세요.
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Lexend:wght@300;500&display=swap');

    .main { background-color: #000000; font-family: 'Inter', sans-serif; }
    
    /* [개선] 버튼: 제네시스의 정교한 버튼 디자인 */
    div.stButton > button {
        background-color: #18181b; 
        color: #ffffff;
        border: 1px solid #938172; /* 제네시스 구리색 테두리 */
        border-radius: 4px;
        padding: 0.6rem 1.2rem;
        font-family: 'Lexend', sans-serif;
        letter-spacing: 0.1em;
        transition: all 0.3s ease;
        text-transform: uppercase;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #938172; /* 호버 시 구리색으로 채워짐 */
        color: #000000;
        border: 1px solid #938172;
        box-shadow: 0 0 15px rgba(147, 129, 114, 0.3);
    }

    /* [개선] 탭: 선택된 탭과 비활성 탭의 구분 강화 */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 12px; 
        background-color: #0c0c0e; 
        padding: 8px 12px; 
        border-radius: 8px;
        border: 1px solid #1c1c1f;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px; 
        background-color: #18181b; 
        border-radius: 4px;
        border: 1px solid #27272a;
        color: #71717a; 
        font-size: 0.8rem; 
        letter-spacing: 0.1em;
        padding: 0px 25px;
    }
    .stTabs [aria-selected="true"] { 
        color: #ffffff !important; 
        background-color: #27272a !important;
        border: 1px solid #938172 !important; /* 선택된 탭에 구리색 테두리 */
    }

    /* [개선] 입력창 테두리 */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border: 1px solid #27272a !important;
        border-radius: 4px !important;
    }
    div[data-baseweb="input"]:focus-within {
        border: 1px solid #938172 !important;
    }

    .section-title { 
        color: #938172; font-size: 0.75rem; font-weight: 500; 
        text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 0.2em; 
        border-left: 3px solid #938172; padding-left: 15px; /* 타이틀 옆에 수직 바 추가 */
    }
    </style>
    """, unsafe_allow_html=True)
