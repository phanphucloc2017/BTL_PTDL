"""
Dashboard phân tích hiệu quả quảng cáo – Shopee Sale 5.5
Chạy:  streamlit run app.py
Dữ liệu: shopee_5_5_cleaned.csv (xuất ra từ notebook làm sạch dữ liệu)
"""
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Shopee 5.5 – Marketing Analytics", page_icon="📊", layout="wide")

DATA_FILE = Path(__file__).parent / "shopee_5_5_cleaned.csv"
COLORS = {"Facebook": "#1877f2", "TikTok": "#111111", "Google": "#34a853",
          "Instagram": "#c13584", "Shopee Ads": "#ee4d2d"}
METRIC_HELP = {
    "ROAS": "Doanh thu / Chi phí (cao hơn = tốt hơn)",
    "CPA": "Chi phí / Đơn chuyển đổi (thấp hơn = tốt hơn)",
    "CVR_%": "Đơn / Click (cao hơn = tốt hơn)",
    "CTR_%": "Click / Lượt hiển thị (cao hơn = tốt hơn)",
    "CPC": "Chi phí / Click (thấp hơn = tốt hơn)",
    "AOV": "Doanh thu / Đơn (giá trị trung bình mỗi đơn)",
}


# ------------------------------------------------------------------ dữ liệu
@st.cache_data
def load_data(file) -> pd.DataFrame:
    df = pd.read_csv(file, encoding="utf-8-sig", parse_dates=["date"])
    df["adset_platform"] = df["ad_set"] + " (" + df["platform"] + ")"
    return df


def ratio(g: pd.DataFrame, num: str, den: str) -> float:
    """Tổng num / tổng den, chỉ trên các dòng có đủ cả hai giá trị."""
    m = g[num].notna() & g[den].notna()
    d = g.loc[m, den].sum()
    return g.loc[m, num].sum() / d if m.any() and d > 0 else np.nan


def summarize(data: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for k, g in data.groupby(by, observed=True, dropna=True):
        rows.append({
            by: k,
            "Số chiến dịch": len(g),
            "Tổng spend": g["spend"].sum(),
            "Tổng revenue": g["revenue"].sum(),
            "CTR_%": ratio(g, "clicks", "impressions") * 100,
            "CPC": ratio(g, "spend", "clicks"),
            "CVR_%": ratio(g, "conversions", "clicks") * 100,
            "CPA": ratio(g, "spend", "conversions"),
            "AOV": ratio(g, "revenue", "conversions"),
            "ROAS": ratio(g, "revenue", "spend"),
        })
    return pd.DataFrame(rows).set_index(by)


def fmt(x, d=2):
    return "–" if pd.isna(x) else f"{x:,.{d}f}"


# ------------------------------------------------------------------ nạp file
st.title("📊 Phân tích hiệu quả quảng cáo – Shopee Sale 5.5")
st.caption("Marketing Analytics · 1.000 chiến dịch · 28/04/2024 – 10/05/2024 · "
           "Facebook, TikTok, Google, Instagram, Shopee Ads")

uploaded = st.sidebar.file_uploader("Dùng file dữ liệu sạch khác (CSV)", type="csv")
if uploaded is not None:
    df_all = load_data(uploaded)
elif DATA_FILE.exists():
    df_all = load_data(DATA_FILE)
else:
    st.error("Không tìm thấy `shopee_5_5_cleaned.csv`. Hãy đặt file cùng thư mục với app.py "
             "hoặc tải lên ở thanh bên.")
    st.stop()

# ------------------------------------------------------------------ bộ lọc
st.sidebar.header("Bộ lọc")
platforms = st.sidebar.multiselect("Nền tảng", sorted(df_all["platform"].unique()),
                                   default=sorted(df_all["platform"].unique()))
groups = st.sidebar.multiselect("Nhóm ad set", sorted(df_all["ad_set_group"].unique()),
                                default=sorted(df_all["ad_set_group"].unique()))
camps = st.sidebar.multiselect("Tên chiến dịch", sorted(df_all["campaign_name"].unique()),
                               default=sorted(df_all["campaign_name"].unique()))
dmin, dmax = df_all["date"].min().date(), df_all["date"].max().date()
d_from, d_to = st.sidebar.date_input("Khoảng ngày", value=(dmin, dmax), min_value=dmin, max_value=dmax)
keep_nodate = st.sidebar.checkbox("Giữ cả dòng thiếu ngày", value=True)

mask = (df_all["platform"].isin(platforms) & df_all["ad_set_group"].isin(groups)
        & df_all["campaign_name"].isin(camps))
in_range = df_all["date"].between(pd.Timestamp(d_from), pd.Timestamp(d_to))
mask &= in_range | (df_all["date"].isna() & keep_nodate)
df = df_all[mask]

if df.empty:
    st.warning("Không có dữ liệu với bộ lọc hiện tại.")
    st.stop()

# ------------------------------------------------------------------ KPI
st.subheader("Chỉ số tổng quan")
kpi = {
    "ROAS": ratio(df, "revenue", "spend"), "CPA": ratio(df, "spend", "conversions"),
    "CVR_%": ratio(df, "conversions", "clicks") * 100, "CTR_%": ratio(df, "clicks", "impressions") * 100,
}
base = {
    "ROAS": ratio(df_all, "revenue", "spend"), "CPA": ratio(df_all, "spend", "conversions"),
    "CVR_%": ratio(df_all, "conversions", "clicks") * 100, "CTR_%": ratio(df_all, "clicks", "impressions") * 100,
}
c = st.columns(6)
c[0].metric("Số chiến dịch", f"{len(df):,}")
c[1].metric("Tổng chi phí", fmt(df["spend"].sum(), 0))
c[2].metric("Tổng doanh thu", fmt(df["revenue"].sum(), 0))
for col, (name, val) in zip(c[3:], list(kpi.items())[:3]):
    delta = None if pd.isna(val) or pd.isna(base[name]) else f"{val - base[name]:+.2f} so với toàn đợt"
    col.metric(name, fmt(val), delta, delta_color="inverse" if name == "CPA" else "normal")
st.caption("ROAS, CPA, CVR… được tính ở mức tổng hợp, chỉ trên các dòng đủ dữ liệu cho từng chỉ số.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Nền tảng", "Ad set", "Theo thời gian", "Mô phỏng ngân sách", "Dữ liệu"])

# ------------------------------------------------------------------ Tab 1
with tab1:
    by_p = summarize(df, "platform")
    metric = st.selectbox("Chỉ số", list(METRIC_HELP), key="m1", help="Chọn chỉ số để so sánh")
    st.caption(METRIC_HELP[metric])
    d = by_p.reset_index().sort_values(metric, ascending=metric == "CPA" or metric == "CPC")
    chart = (alt.Chart(d).mark_bar().encode(
        x=alt.X("platform:N", sort=None, title=""), y=alt.Y(f"{metric}:Q", title=metric),
        color=alt.Color("platform:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values())), legend=None),
        tooltip=["platform", alt.Tooltip(f"{metric}:Q", format=".2f"), "Số chiến dịch"])
        .properties(height=340))
    st.altair_chart(chart, width="stretch")

    both = df.dropna(subset=["spend", "revenue"]).groupby("platform")[["spend", "revenue"]].sum()
    share = pd.DataFrame({"Chi phí": both["spend"] / both["spend"].sum() * 100,
                          "Doanh thu": both["revenue"] / both["revenue"].sum() * 100}).reset_index()
    share = share.melt("platform", var_name="Loại", value_name="Tỉ trọng (%)")
    st.markdown("**Tỉ trọng chi phí vs doanh thu**: nền tảng nào chiếm nhiều ngân sách hơn phần doanh thu mang lại?")
    ch2 = (alt.Chart(share).mark_bar().encode(
        x=alt.X("platform:N", title=""), y="Tỉ trọng (%):Q",
        xOffset="Loại:N", color=alt.Color("Loại:N", scale=alt.Scale(range=["#9aa5b1", "#0b6bcb"])),
        tooltip=["platform", "Loại", alt.Tooltip("Tỉ trọng (%):Q", format=".1f")]).properties(height=300))
    st.altair_chart(ch2, width="stretch")
    st.dataframe(by_p.sort_values("ROAS", ascending=False).style.format("{:,.2f}"), width="stretch")

# ------------------------------------------------------------------ Tab 2
with tab2:
    by_a = summarize(df, "adset_platform")
    by_a["platform"] = by_a.index.str.rsplit("(", n=1).str[-1].str.rstrip(")")
    metric2 = st.selectbox("Chỉ số", list(METRIC_HELP), key="m2")
    min_n = st.slider("Chỉ hiện ad set có tối thiểu … chiến dịch", 1, 60, 10)
    d2 = by_a[by_a["Số chiến dịch"] >= min_n].reset_index().sort_values(
        metric2, ascending=metric2 in ("CPA", "CPC"))
    ch3 = (alt.Chart(d2).mark_bar().encode(
        y=alt.Y("adset_platform:N", sort=None, title=""), x=alt.X(f"{metric2}:Q", title=metric2),
        color=alt.Color("platform:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values())), title="Nền tảng"),
        tooltip=["adset_platform", alt.Tooltip(f"{metric2}:Q", format=".2f"), "Số chiến dịch"])
        .properties(height=max(300, 22 * len(d2))))
    st.altair_chart(ch3, width="stretch")
    st.caption("Lưu ý: Retargeting và Discovery tồn tại ở 2 nền tảng nên được tách riêng theo cặp (ad set, nền tảng).")

    st.markdown("**Heatmap ROAS trung vị: nhóm ad set × nền tảng**")
    pv = df.pivot_table(index="ad_set_group", columns="platform", values="ROAS", aggfunc="median").reset_index()
    pv = pv.melt("ad_set_group", var_name="platform", value_name="ROAS").dropna()
    hm = alt.Chart(pv).mark_rect().encode(
        x="platform:N", y=alt.Y("ad_set_group:N", title=""),
        color=alt.Color("ROAS:Q", scale=alt.Scale(scheme="yellowgreenblue")),
        tooltip=["ad_set_group", "platform", alt.Tooltip("ROAS:Q", format=".2f")])
    txt = alt.Chart(pv).mark_text(fontSize=12).encode(
        x="platform:N", y="ad_set_group:N", text=alt.Text("ROAS:Q", format=".2f"))
    st.altair_chart((hm + txt).properties(height=300), width="stretch")

# ------------------------------------------------------------------ Tab 3
with tab3:
    dd = df.dropna(subset=["date"])
    daily = summarize(dd, "date").reset_index()
    long = daily.melt("date", value_vars=["Tổng spend", "Tổng revenue"], var_name="Loại", value_name="Giá trị")
    sale_rule = alt.Chart(pd.DataFrame({"date": [pd.Timestamp("2024-05-05")]})).mark_rule(
        color="black", strokeDash=[4, 4]).encode(x="date:T")
    top = (alt.Chart(long).mark_bar().encode(
        x=alt.X("date:T", title="", axis=alt.Axis(format="%d/%m")), y="Giá trị:Q", xOffset="Loại:N",
        color=alt.Color("Loại:N", scale=alt.Scale(range=["#9aa5b1", "#0b6bcb"])),
        tooltip=["date:T", "Loại", alt.Tooltip("Giá trị:Q", format=",.0f")]) + sale_rule
    ).properties(height=260, title="Chi phí và doanh thu theo ngày (đường đứt = ngày sale 5/5)")
    line = (alt.Chart(daily).mark_line(point=True, color="#ee4d2d").encode(
        x=alt.X("date:T", title="", axis=alt.Axis(format="%d/%m")),
        y=alt.Y("ROAS:Q", scale=alt.Scale(domain=[0, 7])),
        tooltip=["date:T", alt.Tooltip("ROAS:Q", format=".2f")]) + sale_rule
    ).properties(height=200, title="ROAS theo ngày (trục bắt đầu từ 0 để không phóng đại dao động)")
    st.altair_chart(top & line, width="stretch")

    st.markdown("**Trước / trong / sau ngày sale 5/5**")
    st.dataframe(summarize(df.dropna(subset=["phase"]), "phase").style.format("{:,.2f}"), width="stretch")
    st.markdown("**Cuối tuần vs ngày thường**")
    st.dataframe(summarize(df.dropna(subset=["day_type"]), "day_type").style.format("{:,.2f}"), width="stretch")

# ------------------------------------------------------------------ Tab 4
with tab4:
    st.markdown("**Mô phỏng:** chuyển một phần ngân sách từ nền tảng nguồn sang các nền tảng đích.")
    st.info("Giả định đơn giản: ROAS của mỗi nền tảng giữ nguyên khi đổi ngân sách. "
            "Thực tế ROAS thường giảm khi tăng chi, nên kết quả chỉ mang tính minh họa.")
    by_p2 = summarize(df, "platform")
    plats = list(by_p2.index)
    col_a, col_b = st.columns(2)
    src = col_a.selectbox("Nền tảng nguồn (giảm ngân sách)", plats,
                          index=plats.index("TikTok") if "TikTok" in plats else 0)
    dest_opts = [p for p in plats if p != src]
    default_dest = [p for p in ["Facebook", "Shopee Ads"] if p in dest_opts] or dest_opts[:1]
    dest = col_b.multiselect("Nền tảng đích (tăng ngân sách)", dest_opts, default=default_dest)
    pct = st.slider("% ngân sách chuyển đi", 0, 30, 10)

    if dest:
        sp = df.dropna(subset=["spend", "revenue"]).groupby("platform")["spend"].sum()
        total_rev = df.dropna(subset=["spend", "revenue"])["revenue"].sum()
        roas_dest = (by_p2.loc[dest, "ROAS"] * sp[dest]).sum() / sp[dest].sum()
        moved = sp[src] * pct / 100
        gain = moved * (roas_dest - by_p2.loc[src, "ROAS"])
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"ROAS {src}", fmt(by_p2.loc[src, "ROAS"]))
        m2.metric("ROAS bình quân nền tảng đích", fmt(roas_dest))
        m3.metric("Ngân sách chuyển", fmt(moved, 0))
        m4.metric("Doanh thu tăng thêm", fmt(gain, 0), f"{gain / total_rev * 100:+.2f}% tổng doanh thu")

        sweep = pd.DataFrame({"% chuyển": range(0, 31, 5)})
        sweep["Doanh thu tăng thêm"] = sweep["% chuyển"] / 100 * sp[src] * (roas_dest - by_p2.loc[src, "ROAS"])
        st.altair_chart(alt.Chart(sweep).mark_line(point=True, color="#0b6bcb").encode(
            x="% chuyển:Q", y="Doanh thu tăng thêm:Q",
            tooltip=["% chuyển", alt.Tooltip("Doanh thu tăng thêm:Q", format=",.0f")]).properties(height=260),
            width="stretch")
    else:
        st.warning("Hãy chọn ít nhất một nền tảng đích.")

# ------------------------------------------------------------------ Tab 5
with tab5:
    st.write(f"{len(df):,} dòng sau khi lọc")
    st.dataframe(df.drop(columns=["adset_platform"]), width="stretch", height=420)
    st.download_button("Tải dữ liệu đã lọc (CSV)",
                       df.drop(columns=["adset_platform"]).to_csv(index=False).encode("utf-8-sig"),
                       "shopee_5_5_filtered.csv", "text/csv")
