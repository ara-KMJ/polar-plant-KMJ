import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
# 경로 설정 (Cloud 안전)
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# =========================
# 유틸
# =========================
def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text)

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_environment_data():
    if not DATA_DIR.exists():
        st.error("❌ data 폴더를 찾을 수 없습니다.")
        return {}

    result = {}
    for p in DATA_DIR.iterdir():
        if p.is_file() and p.suffix.lower() == ".csv":
            school = normalize(p.stem.replace("_환경데이터", ""))
            result[school] = pd.read_csv(p)
    return result


@st.cache_data
def load_growth_data():
    if not DATA_DIR.exists():
        st.error("❌ data 폴더를 찾을 수 없습니다.")
        return None

    xlsx_file = None
    for p in DATA_DIR.iterdir():
        if p.is_file() and p.suffix.lower() == ".xlsx":
            xlsx_file = p
            break

    if xlsx_file is None:
        st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return None

    xls = pd.ExcelFile(xlsx_file, engine="openpyxl")
    data = {}
    for sheet in xls.sheet_names:
        data[normalize(sheet)] = pd.read_excel(xls, sheet_name=sheet)

    return data


with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or growth_data is None:
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

schools = list(growth_data.keys())

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

tab1, tab2, tab3 = st.tabs(
    ["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"]
)

# =====================================================
# TAB 1 : 실험 개요
# =====================================================
with tab1:
    st.markdown("""
    **극지식물의 생육에 적합한 EC(전기전도도) 농도**를 탐구하기 위해  
    서로 다른 EC 조건에서 재배된 식물의 환경 요인과 생육 결과를 비교하였다.
    """)

    overview = []
    for s in schools:
        overview.append({
            "학교": s,
            "EC 조건": EC_INFO.get(s),
            "개체수": len(growth_data[s])
        })

    st.dataframe(pd.DataFrame(overview), use_container_width=True)

    total_cnt = sum(len(df) for df in growth_data.values())
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    mean_weight = {
        s: growth_data[s]["생중량(g)"].mean()
        for s in schools
    }
    best_school = max(mean_weight, key=mean_weight.get)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_cnt)
    c2.metric("평균 온도(℃)", f"{avg_temp:.1f}")
    c3.metric("평균 습도(%)", f"{avg_hum:.1f}")
    c4.metric("최적 EC", f"{EC_INFO[best_school]} (하늘고)")

# =====================================================
# TAB 2 : 환경 데이터
# =====================================================
with tab2:
    rows = []
    for s, df in env_data.items():
        rows.append({
            "학교": s,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "실측 EC": df["ec"].mean(),
            "목표 EC": EC_INFO.get(s)
        })

    avg_df = pd.DataFrame(rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "EC 비교")
    )

    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["온도"]), 1, 1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["습도"]), 1, 2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["pH"]), 2, 1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["실측 EC"], name="실측"), 2, 2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["목표 EC"], name="목표"), 2, 2)

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
        st.plotly_chart(fig_ts, use_container_width=True)

# =====================================================
# TAB 3 : 생육 결과
# =====================================================
with tab3:
    weight_df = pd.DataFrame([
        {
            "학교": s,
            "EC": EC_INFO[s],
            "평균 생중량": growth_data[s]["생중량(g)"].mean()
        }
        for s in schools
    ])

    best = weight_df.loc[weight_df["평균 생중량"].idxmax()]

    st.metric(
        "🥇 최대 평균 생중량",
        f"{best['평균 생중량']:.2f} g",
        f"EC {best['EC']} (하늘고)"
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수")
    )

    fig.add_trace(go.Bar(
        x=schools,
        y=weight_df["평균 생중량"]
    ), 1, 1)

    fig.add_trace(go.Bar(
        x=schools,
        y=[growth_data[s]["잎 수(장)"].mean() for s in schools]
    ), 1, 2)

    fig.add_trace(go.Bar(
        x=schools,
        y=[growth_data[s]["지상부 길이(mm)"].mean() for s in schools]
    ), 2, 1)

    fig.add_trace(go.Bar(
        x=schools,
        y=[len(growth_data[s]) for s in schools]
    ), 2, 2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig, use_container_width=True)

    dist_df = pd.concat(
        [growth_data[s].assign(학교=s) for s in schools]
    )

    fig_box = px.box(
        dist_df,
        x="학교",
        y="생중량(g)",
        color="학교",
        title="학교별 생중량 분포"
    )
    st.plotly_chart(fig_box, use_container_width=True)

    fig_sc1 = px.scatter(
        dist_df,
        x="잎 수(장)",
        y="생중량(g)",
        color="학교"
    )
    fig_sc2 = px.scatter(
        dist_df,
        x="지상부 길이(mm)",
        y="생중량(g)",
        color="학교"
    )

    st.plotly_chart(fig_sc1, use_container_width=True)
    st.plotly_chart(fig_sc2, use_container_width=True)

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
