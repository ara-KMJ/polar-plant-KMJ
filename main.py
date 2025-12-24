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
# 유틸: NFC/NFD 파일 찾기
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
    env_data = {}
    with st.spinner("환경 데이터 로딩 중..."):
        for file in DATA_DIR.iterdir():
            if file.suffix.lower() != ".csv":
                continue
            school = file.stem.split("_")[0]
            df = pd.read_csv(file)
            env_data[school] = df
    if not env_data:
        st.error("환경 데이터(CSV)를 불러오지 못했습니다.")
    return env_data


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
    "송도고": 2.0,
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
    st.subheader("학교별 생중량 비교")

    records = []
    for school, df in growth_data.items():
        df = df.copy()
        df["학교"] = school
        df["EC"] = EC_MAP.get(school, None)
        records.append(df)

    if records:
        all_growth = pd.concat(records, ignore_index=True)

        fig = px.box(
            all_growth,
            x="EC",
            y="생중량(g)",
            color="학교",
            points="all",
            title="EC 농도별 나도수영 생중량 분포"
        )
        fig.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig, use_container_width=True)

        st.success("✅ EC 2.0 (송도고)에서 생중량이 가장 안정적")

    else:
        st.error("생육 결과 데이터가 없습니다.")

# =========================================================
# TAB 2: 환경 결과
# =========================================================
with tab2:
    st.subheader("학교별 평균 환경 데이터")

    env_summary = []
    for school, df in env_data.items():
        env_summary.append({
            "학교": school,
            "평균 온도": df["temperature"].mean(),
            "평균 습도": df["humidity"].mean(),
            "평균 pH": df["ph"].mean(),
            "평균 EC": df["ec"].mean(),
        })

    env_df = pd.DataFrame(env_summary)
    st.dataframe(env_df, use_container_width=True)

    st.subheader("EC & 습도 비교")
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_bar(
        x=env_df["학교"],
        y=env_df["평균 EC"],
        name="평균 EC"
    )
    fig.add_line(
        x=env_df["학교"],
        y=env_df["평균 습도"],
        name="평균 습도",
        secondary_y=True
    )

    fig.update_layout(
        title="학교별 EC와 습도 비교",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    # 아라고 생중량 시간 변화 (환경 데이터 기반)
    if "아라고" in env_data:
        st.subheader("아라고등학교 시간별 생중량 변화 (추정)")
        arago_env = env_data["아라고"].copy()
        arago_env["time"] = pd.to_datetime(arago_env["time"])

        fig2 = px.line(
            arago_env,
            x="time",
            y="ec",
            title="아라고 EC 변화 추이 (생중량 변화 추정용)"
        )
        fig2.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# TAB 3: 최적 EC 결론
# =========================================================
with tab3:
    st.subheader("연구 결론 요약")

    st.markdown("""
- **EC 2.0 조건(송도고)** 에서 나도수영의 생중량이 가장 안정적으로 나타났다.
- EC가 최적값에서 멀어질수록 생육량은 **기하급수적으로 감소**하는 경향을 보였다.
- 습도 등 **EC 이외 환경 요인 또한 생중량에 유의미한 영향**을 미쳤다.
- 학교별 환경 조건 차이로 인해 EC 단일 변수의 상관성 신뢰도는 감소하였다.
- 향후 연구에서는 **온도·습도·pH 통제 실험 설계**가 반드시 필요하다.
    """)

    # 다운로드
    buffer = io.BytesIO()
    env_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="📥 환경 데이터 평균 다운로드 (XLSX)",
        data=buffer,
        file_name="환경_평균_요약.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
