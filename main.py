import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import io

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 유틸 함수
# =========================
def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFC", name)

def find_file(data_dir: Path, target_name: str):
    target_nfc = normalize_name(target_name)
    for p in data_dir.iterdir():
        if normalize_name(p.name) == target_nfc:
            return p
    return None

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_environment_data():
    data_dir = Path("data")
    school_files = {}
    for p in data_dir.iterdir():
        if p.suffix == ".csv":
            school_name = p.stem.replace("_환경데이터", "")
            school_files[school_name] = pd.read_csv(p)
    return school_files

@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    xlsx_file = None
    for p in data_dir.iterdir():
        if p.suffix == ".xlsx":
            xlsx_file = p
            break

    if xlsx_file is None:
        return None

    xls = pd.ExcelFile(xlsx_file, engine="openpyxl")
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = pd.read_excel(xls, sheet_name=sheet)
    return data

# =========================
# 데이터 로딩 실행
# =========================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or growth_data is None:
    st.error("❌ 데이터 파일을 불러올 수 없습니다. data 폴더 구조를 확인하세요.")
    st.stop()

# =========================
# 메타 정보
# =========================
EC_INFO = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLORS = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

schools = list(env_data.keys())

# =========================
# 사이드바
# =========================
selected_school = st.sidebar.selectbox(
    "🏫 학교 선택",
    ["전체"] + schools
)

# =========================
# 제목
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =========================================================
# TAB 1 : 실험 개요
# =========================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown("""
    본 연구는 **극지식물 생육에 적합한 EC(전기전도도) 농도**를 규명하기 위해  
    서로 다른 EC 조건에서 재배된 식물의 **환경 데이터와 생육 결과**를 비교·분석하였다.
    """)

    overview_rows = []
    for school, ec in EC_INFO.items():
        overview_rows.append({
            "학교명": school,
            "EC 목표": ec,
            "개체수": len(growth_data.get(school, [])),
            "색상": SCHOOL_COLORS.get(school)
        })

    st.dataframe(pd.DataFrame(overview_rows), use_container_width=True)

    total_plants = sum(len(df) for df in growth_data.values())
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    mean_weights = {
        school: df["생중량(g)"].mean()
        for school, df in growth_data.items()
    }
    best_school = max(mean_weights, key=mean_weights.get)
    best_ec = EC_INFO[best_school]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체수", total_plants)
    col2.metric("평균 온도(℃)", f"{avg_temp:.1f}")
    col3.metric("평균 습도(%)", f"{avg_hum:.1f}")
    col4.metric("최적 EC", f"{best_ec} (하늘고)")

# =========================================================
# TAB 2 : 환경 데이터
# =========================================================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_df = []
    for school, df in env_data.items():
        avg_df.append({
            "학교": school,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "EC": df["ec"].mean(),
            "목표 EC": EC_INFO.get(school)
        })
    avg_df = pd.DataFrame(avg_df)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["온도"]), 1, 1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["습도"]), 1, 2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["pH"]), 2, 1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["EC"], name="실측 EC"), 2, 2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["목표 EC"], name="목표 EC"), 2, 2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]
        fig_ts = px.line(
            df,
            x="time",
            y=["temperature", "humidity", "ec"],
            title=f"{selected_school} 환경 변화"
        )
        fig_ts.add_hline(
            y=EC_INFO[selected_school],
            line_dash="dash",
            annotation_text="목표 EC"
        )
        fig_ts.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📥 환경 데이터 원본 다운로드"):
        merged = pd.concat(
            [df.assign(학교=school) for school, df in env_data.items()]
        )
        st.dataframe(merged, use_container_width=True)

        buffer = io.BytesIO()
        merged.to_csv(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "CSV 다운로드",
            data=buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# =========================================================
# TAB 3 : 생육 결과
# =========================================================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    weight_df = pd.DataFrame([
        {
            "학교": school,
            "EC": EC_INFO[school],
            "평균 생중량": df["생중량(g)"].mean()
        }
        for school, df in growth_data.items()
    ])

    best_row = weight_df.loc[weight_df["평균 생중량"].idxmax()]

    st.metric(
        label="최대 평균 생중량",
        value=f"{best_row['평균 생중량']:.2f} g",
        delta=f"EC {best_row['EC']} (하늘고)"
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수")
    )

    fig.add_trace(go.Bar(
        x=weight_df["학교"], y=weight_df["평균 생중량"]), 1, 1)

    fig.add_trace(go.Bar(
        x=growth_data.keys(),
        y=[df["잎 수(장)"].mean() for df in growth_data.values()]
    ), 1, 2)

    fig.add_trace(go.Bar(
        x=growth_data.keys(),
        y=[df["지상부 길이(mm)"].mean() for df in growth_data.values()]
    ), 2, 1)

    fig.add_trace(go.Bar(
        x=growth_data.keys(),
        y=[len(df) for df in growth_data.values()]
    ), 2, 2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    dist_df = pd.concat(
        [df.assign(학교=school) for school, df in growth_data.items()]
    )
    fig_box = px.box(
        dist_df,
        x="학교",
        y="생중량(g)",
        color="학교",
        title="학교별 생중량 분포"
    )
    fig_box.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    fig_scatter1 = px.scatter(
        dist_df, x="잎 수(장)", y="생중량(g)", color="학교"
    )
    fig_scatter2 = px.scatter(
        dist_df, x="지상부 길이(mm)", y="생중량(g)", color="학교"
    )

    st.plotly_chart(fig_scatter1, use_container_width=True)
    st.plotly_chart(fig_scatter2, use_container_width=True)

    with st.expander("📥 생육 데이터 다운로드"):
        buffer = io.BytesIO()
        dist_df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


