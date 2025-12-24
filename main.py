import streamlit as st
import pandas as pd
import unicodedata
from pathlib import Path
import io

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="EC 농도에 따른 나도수영의 생중량 변화",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 경로 설정
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# =========================================================
# NFC / NFD 안전 파일 탐색
# =========================================================
def find_file_by_normalized_name(directory: Path, target_name: str):
    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for file in directory.iterdir():
        if not file.is_file():
            continue
        name_nfc = unicodedata.normalize("NFC", file.name)
        name_nfd = unicodedata.normalize("NFD", file.name)
        if name_nfc == target_nfc or name_nfd == target_nfd:
            return file
    return None

# =========================================================
# 데이터 로딩
# =========================================================
@st.cache_data
def load_environment_data():
    data = {}
    with st.spinner("환경 데이터 로딩 중..."):
        for file in DATA_DIR.iterdir():
            if file.suffix.lower() != ".csv":
                continue
            school = file.stem.split("_")[0]
            df = pd.read_csv(file)
            data[school] = df
    if not data:
        st.error("환경 데이터(CSV)를 불러오지 못했습니다.")
    return data


@st.cache_data
def load_growth_data():
    with st.spinner("생육 결과 데이터 로딩 중..."):
        target = find_file_by_normalized_name(
            DATA_DIR, "4개교_생육결과데이터.xlsx"
        )
        if target is None:
            st.error("생육 결과 엑셀 파일을 찾을 수 없습니다.")
            return {}

        xls = pd.ExcelFile(target)
        data = {}
        for sheet in xls.sheet_names:
            data[sheet] = pd.read_excel(xls, sheet_name=sheet)
        return data


env_data = load_environment_data()
growth_data = load_growth_data()

# =========================================================
# 학교별 EC 정보
# =========================================================
EC_MAP = {
    "동산고": 1.0,
    "송도고": 2.0,  # 최적
    "하늘고": 4.0,
    "아라고": 8.0,
}

# =========================================================
# 사이드바
# =========================================================
schools = ["전체"] + sorted(env_data.keys())
selected_school = st.sidebar.selectbox("학교 선택", schools)

# =========================================================
# 제목
# =========================================================
st.title("🌱 EC 농도에 따른 나도수영의 생중량 변화")

# =========================================================
# 탭 구성
# =========================================================
tab1, tab2, tab3 = st.tabs(["📈 생육 결과", "🌡 환경 결과", "🧪 최적 EC 결론"])

# =========================================================
# TAB 1: 생육 결과
# =========================================================
with tab1:
    st.subheader("EC 농도별 생중량 분포")

    records = []
    for school, df in growth_data.items():
        temp = df.copy()
        temp["학교"] = school
        temp["EC"] = EC_MAP.get(school)
        records.append(temp)

    if records:
        all_growth = pd.concat(records, ignore_index=True)

        fig = px.box(
            all_growth,
            x="EC",
            y="생중량(g)",
            color="학교",
            points="all",
            title="EC 농도에 따른 나도수영 생중량 비교"
        )

        fig.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )

        st.plotly_chart(fig, use_container_width=True)
        st.success("✅ EC 2.0 (송도고)에서 생중량이 가장 안정적으로 나타남")

    else:
        st.error("생육 결과 데이터가 없습니다.")

# =========================================================
# TAB 2: 환경 결과
# =========================================================
with tab2:
    st.subheader("학교별 환경 데이터 평균")

    summary = []
    for school, df in env_data.items():
        summary.append({
            "학교": school,
            "평균 온도": df["temperature"].mean(),
            "평균 습도": df["humidity"].mean(),
            "평균 pH": df["ph"].mean(),
            "평균 EC": df["ec"].mean(),
        })

    env_df = pd.DataFrame(summary)
    st.dataframe(env_df, use_container_width=True)

    # === EC & 습도 서브플롯 (수정된 핵심 부분) ===
    st.subheader("학교별 평균 EC & 습도 비교")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_bar(
        x=env_df["학교"],
        y=env_df["평균 EC"],
        name="평균 EC",
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=env_df["학교"],
            y=env_df["평균 습도"],
            mode="lines+markers",
            name="평균 습도"
        ),
        secondary_y=True
    )

    fig.update_layout(
        title="학교별 EC와 습도 비교",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    fig.update_yaxes(title_text="EC", secondary_y=False)
    fig.update_yaxes(title_text="습도 (%)", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

    # === 아라고 시간 변화 ===
    if "아라고" in env_data:
        st.subheader("아라고등학교 시간별 EC 변화")

        arago = env_data["아라고"].copy()
        arago["time"] = pd.to_datetime(arago["time"])

        fig2 = px.line(
            arago,
            x="time",
            y="ec",
            title="아라고 EC 시간 변화"
        )

        fig2.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )

        st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# TAB 3: 최적 EC 결론
# =========================================================
with tab3:
    st.subheader("연구 결론")

    st.markdown("""
- **EC 2.0 (송도고)** 조건에서 나도수영의 생중량이 가장 안정적으로 나타났다.  
- EC가 최적값에서 멀어질수록 생육량은 **기하급수적으로 감소**하는 경향을 보였다.  
- 습도 등 **EC 이외 환경 요인도 생중량에 유의미한 영향을 미쳤다.**  
- 학교별 환경 차이로 인해 EC 단일 변수의 상관성 신뢰도는 다소 저하되었다.  
- 향후 연구에서는 **온도·습도·pH를 통제한 실험 설계**가 필요하다.
    """)

    buffer = io.BytesIO()
    env_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="📥 환경 데이터 평균 다운로드 (XLSX)",
        data=buffer,
        file_name="환경_평균_요약.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
