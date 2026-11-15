"""
Phân tích quảng cáo – Shopee Sale 5.5
Chạy:  streamlit run app.py
Đọc file CSV đã làm sạch (xuất từ notebook). Có thể tải nhiều file, các file đã tải
được giữ trong danh sách ở thanh bên để xem lại (danh sách mất khi tải lại trang).
"""
from datetime import datetime
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from cleaning import RAW_COLS, clean_raw

st.set_page_config(page_title="Phân tích quảng cáo Shopee 5.5", layout="wide")
st.markdown("""
<style>
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.07);
                          padding: 10px 14px; border-radius: 6px;}
[data-testid="stAppDeployButton"], .stDeployButton {display: none !important;}
h1 {font-size: 1.7rem !important;}
h2, h3 {font-size: 1.2rem !important;}
</style>""", unsafe_allow_html=True)

DATA_FILE = Path(__file__).parent / "shopee_5_5_cleaned.csv"
COLORS = {"Facebook": "#1877f2", "TikTok": "#222222", "Google": "#34a853",
          "Instagram": "#c13584", "Shopee Ads": "#ee4d2d"}
COLOR_SCALE = alt.Scale(domain=list(COLORS), range=list(COLORS.values()))
NEED_COLS = ["campaign_name", "platform", "ad_set", "spend", "clicks", "impressions", "conversions",
             "revenue", "date", "ROAS", "ad_set_group", "phase", "day_type"]
# tên chỉ số: (giải thích, True nếu càng cao càng tốt)
METRICS = {
    "ROAS": ("doanh thu trên mỗi 1 đồng chi quảng cáo", True),
    "CPA": ("chi phí để có 1 đơn hàng", False),
    "CVR (%)": ("trong 100 lượt click thì có bao nhiêu đơn", True),
    "CTR (%)": ("trong 100 lượt hiển thị thì có bao nhiêu lượt click", True),
    "CPC": ("chi phí cho mỗi lượt click", False),
    "AOV": ("giá trị trung bình của một đơn hàng", True),
}


# ---------------------------------------------------------------- hàm dùng chung
def vn(x, d=2):
    """Định dạng số kiểu Việt Nam: 1.204.095 và 4,99."""
    if pd.isna(x):
        return "–"
    return f"{x:,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def ratio(g, num, den):
    """Tổng num / tổng den, chỉ lấy các dòng có đủ cả hai giá trị."""
    m = g[num].notna() & g[den].notna()
    d = g.loc[m, den].sum()
    return g.loc[m, num].sum() / d if m.any() and d > 0 else np.nan


def summarize(data, by):
    rows = []
    for k, g in data.groupby(by, dropna=True):
        rows.append({by: k, "Số chiến dịch": len(g), "Tổng chi phí": g["spend"].sum(),
                     "Tổng doanh thu": g["revenue"].sum(),
                     "CTR (%)": ratio(g, "clicks", "impressions") * 100, "CPC": ratio(g, "spend", "clicks"),
                     "CVR (%)": ratio(g, "conversions", "clicks") * 100, "CPA": ratio(g, "spend", "conversions"),
                     "AOV": ratio(g, "revenue", "conversions"), "ROAS": ratio(g, "revenue", "spend")})
    return pd.DataFrame(rows).set_index(by)


def _read(file, **kw):
    name = str(getattr(file, "name", file)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file, **kw)
    return pd.read_csv(file, encoding="utf-8-sig", **kw)


def load_upload(file):
    """Trả về (bảng dữ liệu đã sạch, báo cáo làm sạch hoặc None).
    - File đã chạy qua notebook (có đủ cột ROAS, phase...): dùng luôn.
    - File gốc chưa làm sạch: tự làm sạch và trả kèm báo cáo.
    - File khác: báo thiếu cột."""
    try:
        head = _read(file, dtype=str)
    except Exception:
        raise ValueError("không đọc được file này như một bảng dữ liệu. Hãy dùng file CSV hoặc Excel (.xlsx).")
    log = None
    if all(c in head.columns for c in NEED_COLS):
        if hasattr(file, "seek"):
            file.seek(0)
        df = _read(file)
    else:
        missing = [c for c in RAW_COLS if c not in head.columns]
        if missing:
            raise ValueError("thiếu cột " + ", ".join(missing) + ". File cần có đủ các cột: " + ", ".join(RAW_COLS) + ".")
        df, log = clean_raw(head)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["adset_platform"] = df["ad_set"] + " (" + df["platform"] + ")"
    return df, log


def metric_chart(d, cat, metric, horizontal=False, height=320):
    """Biểu đồ cột có ghi số trên cột. d có cột `cat`, `metric`, `platform`."""
    val = alt.Y(field=metric, type="quantitative", title=metric) if not horizontal else \
        alt.X(field=metric, type="quantitative", title=metric)
    ax = alt.Y(field=cat, type="nominal", sort=None, title="") if horizontal else \
        alt.X(field=cat, type="nominal", sort=None, title="")
    enc = dict(color=alt.Color("platform:N", scale=COLOR_SCALE, legend=None if not horizontal else alt.Legend(title="Nền tảng")),
               tooltip=[cat, alt.Tooltip(field=metric, type="quantitative", format=".2f"), "Số chiến dịch"])
    bars = alt.Chart(d).mark_bar().encode(**({"y": ax, "x": val} if horizontal else {"x": ax, "y": val}), **enc)
    txt_kw = dict(align="left", dx=4) if horizontal else dict(dy=-7)
    txt = alt.Chart(d).mark_text(fontSize=11, **txt_kw).encode(
        **({"y": ax, "x": val} if horizontal else {"x": ax, "y": val}),
        text=alt.Text(field=metric, type="quantitative", format=".2f"))
    return (bars + txt).properties(height=height)


# ---------------------------------------------------------------- lịch sử file đã tải
ss = st.session_state


def label(n):
    f = ss.files[n]
    return f"{n} · {vn(len(f['df']), 0)} dòng · {f['time']:%H:%M}"


if "files" not in ss:
    ss.files, ss.seen = {}, set()
    if DATA_FILE.exists():
        d0, l0 = load_upload(DATA_FILE)
        ss.files["Shopee 5.5 (file mẫu)"] = {"df": d0, "log": l0, "time": datetime.now()}
        ss.pick = label("Shopee 5.5 (file mẫu)")

st.sidebar.header("Dữ liệu")
uploads = st.sidebar.file_uploader("Tải file dữ liệu (CSV hoặc Excel)", type=["csv", "xlsx"], accept_multiple_files=True)
st.sidebar.caption("File gốc chưa làm sạch sẽ được làm sạch tự động khi tải lên.")
for f in uploads or []:
    sig = (f.name, f.size)
    if sig in ss.seen:
        continue
    try:
        data, log = load_upload(f)
    except Exception as e:                      # file sai định dạng: báo lỗi, không thêm vào danh sách
        st.sidebar.error(f"{f.name}: {e}")
        continue
    name, n = f.name, 2
    while name in ss.files:
        name, n = f"{f.name} ({n})", n + 1
    ss.files[name] = {"df": data, "log": log, "time": datetime.now()}
    ss.seen.add(sig)
    ss.pick = label(name)                       # file mới tải lên thì tự chuyển sang xem file đó

names = list(ss.files)
st.title("Dashboard đánh giá hiệu quả quảng cáo – Shopee Sale 5.5")
st.caption("So sánh hiệu quả các nền tảng và nhóm quảng cáo, theo dõi diễn biến theo ngày "
           "và thử chuyển ngân sách giữa các nền tảng.")
if not names:
    st.write("Chưa có dữ liệu. Hãy tải một file CSV hoặc Excel ở thanh bên.")
    st.stop()

labels = {label(n): n for n in names}
if ss.get("pick") not in labels:
    ss.pick = list(labels)[-1]
pick = st.sidebar.radio("Các file đã tải lên (bấm để xem lại)", list(labels), key="pick")
cur = labels[pick]
st.sidebar.caption("Danh sách chỉ lưu trong phiên làm việc hiện tại, tải lại trang sẽ mất.")
df_all = ss.files[cur]["df"]
d_min, d_max = df_all["date"].min(), df_all["date"].max()
st.caption(f"Đang xem: {cur} · {vn(len(df_all), 0)} chiến dịch"
           + (f" · từ {d_min:%d/%m/%Y} đến {d_max:%d/%m/%Y}" if pd.notna(d_min) else ""))

if ss.files[cur].get("log"):
    st.caption("File này là file gốc và đã được làm sạch tự động khi tải lên. Xem chi tiết ở tab Dữ liệu.")

# ---------------------------------------------------------------- bộ lọc (nhớ riêng cho từng file)
st.sidebar.header("Lọc dữ liệu")
opts = lambda c: sorted(df_all[c].dropna().unique())
sel_p = st.sidebar.multiselect("Nền tảng", opts("platform"), default=opts("platform"), key=f"{cur}|p")
sel_g = st.sidebar.multiselect("Nhóm ad set", opts("ad_set_group"), default=opts("ad_set_group"), key=f"{cur}|g")
sel_c = st.sidebar.multiselect("Tên chiến dịch", opts("campaign_name"), default=opts("campaign_name"), key=f"{cur}|c")
mask = df_all["platform"].isin(sel_p) & df_all["ad_set_group"].isin(sel_g) & df_all["campaign_name"].isin(sel_c)
if pd.notna(d_min):
    rng = st.sidebar.date_input("Khoảng ngày", (d_min.date(), d_max.date()), d_min.date(), d_max.date(), key=f"{cur}|d")
    keep = st.sidebar.checkbox("Giữ cả dòng bị thiếu ngày", True, key=f"{cur}|k")
    if len(rng) == 2:
        mask &= df_all["date"].between(pd.Timestamp(rng[0]), pd.Timestamp(rng[1])) | (df_all["date"].isna() & keep)
df = df_all[mask]
if df.empty:
    st.warning("Không có dòng nào khớp với bộ lọc hiện tại.")
    st.stop()

# ---------------------------------------------------------------- chỉ số chính
roas, cpa = ratio(df, "revenue", "spend"), ratio(df, "spend", "conversions")
cvr, ctr = ratio(df, "conversions", "clicks") * 100, ratio(df, "clicks", "impressions") * 100
roas0, cpa0 = ratio(df_all, "revenue", "spend"), ratio(df_all, "spend", "conversions")
cvr0 = ratio(df_all, "conversions", "clicks") * 100

c = st.columns(6)
c[0].metric("Số chiến dịch", vn(len(df), 0))
c[1].metric("Tổng chi phí", vn(df["spend"].sum(), 0))
c[2].metric("Tổng doanh thu", vn(df["revenue"].sum(), 0))
c[3].metric("ROAS", vn(roas), f"{roas - roas0:+.2f} so với cả file".replace(".", ",") if len(df) < len(df_all) else None)
c[4].metric("CPA", vn(cpa), f"{cpa - cpa0:+.2f} so với cả file".replace(".", ",") if len(df) < len(df_all) else None,
            delta_color="inverse")
c[5].metric("CVR", vn(cvr) + "%", f"{cvr - cvr0:+.2f} điểm so với cả file".replace(".", ",") if len(df) < len(df_all) else None)
st.caption("ROAS = doanh thu / chi phí. CPA = chi phí / số đơn. CVR = số đơn / số click. "
           "Các tỉ lệ được tính trên tổng của các dòng có đủ dữ liệu, dòng nào thiếu số thì bỏ qua cho chỉ số đó.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Nền tảng", "Ad set", "Theo thời gian", "Chuyển ngân sách", "Dữ liệu"])

# ---------------------------------------------------------------- tab nền tảng
with tab1:
    by_p = summarize(df, "platform")
    metric = st.selectbox("Chỉ số muốn so sánh", list(METRICS), key="m1")
    note, higher_better = METRICS[metric]
    st.write(f"**{metric}**: {note}. " + ("Càng cao càng tốt." if higher_better else "Càng thấp càng tốt."))
    d = by_p.reset_index().sort_values(metric, ascending=not higher_better)
    st.altair_chart(metric_chart(d, "platform", metric), width="stretch")

    if len(d) > 1:
        best, worst = d.iloc[0], d.iloc[-1]
        st.write(f"Nền tảng tốt nhất theo {metric} là **{best['platform']}** ({vn(best[metric])}), "
                 f"kém nhất là **{worst['platform']}** ({vn(worst[metric])}).")

    st.subheader("Chi phí và doanh thu: ai chiếm bao nhiêu?")
    st.write("Nếu cột doanh thu thấp hơn cột chi phí, nền tảng đó đang tốn nhiều ngân sách hơn phần doanh thu nó mang lại.")
    both = df.dropna(subset=["spend", "revenue"]).groupby("platform")[["spend", "revenue"]].sum()
    share = (both / both.sum() * 100).rename(columns={"spend": "Chi phí", "revenue": "Doanh thu"}).reset_index()
    sh = share.melt("platform", var_name="Loại", value_name="Tỉ trọng (%)")
    base = alt.Chart(sh).encode(x=alt.X("platform:N", title=""), xOffset="Loại:N")
    bars = base.mark_bar().encode(y="Tỉ trọng (%):Q", color=alt.Color("Loại:N", scale=alt.Scale(range=["#9aa5b1", "#0b6bcb"])))
    lab = base.mark_text(dy=-7, fontSize=11).encode(y="Tỉ trọng (%):Q", text=alt.Text("Tỉ trọng (%):Q", format=".1f"))
    st.altair_chart((bars + lab).properties(height=300), width="stretch")
    if len(share) > 1:
        share["lệch"] = share["Doanh thu"] - share["Chi phí"]
        w = share.sort_values("lệch").iloc[0]
        if w["lệch"] < -1:
            st.write(f"**{w['platform']}** chiếm {vn(w['Chi phí'], 1)}% chi phí nhưng chỉ đem lại {vn(w['Doanh thu'], 1)}% doanh thu.")
    st.dataframe(by_p.sort_values("ROAS", ascending=False).style.format("{:,.2f}"), width="stretch")

# ---------------------------------------------------------------- tab ad set
with tab2:
    st.write("Ad set là nhóm quảng cáo (cách nhắm đối tượng hoặc hình thức hiển thị). "
             "Retargeting và Discovery xuất hiện ở hai nền tảng nên được tách riêng, ghi kèm tên nền tảng trong ngoặc.")
    by_a = summarize(df, "adset_platform")
    by_a["platform"] = by_a.index.str.rsplit("(", n=1).str[-1].str.rstrip(")")
    metric2 = st.selectbox("Chỉ số", list(METRICS), key="m2")
    min_n = st.slider("Chỉ hiện ad set có ít nhất … chiến dịch", 1, 60, 10,
                      help="Ad set có quá ít chiến dịch thì số liệu dễ bị lệch, nên nên đặt mức tối thiểu.")
    hb2 = METRICS[metric2][1]
    d2 = by_a[by_a["Số chiến dịch"] >= min_n].reset_index().sort_values(metric2, ascending=not hb2)
    if d2.empty:
        st.write("Không có ad set nào đủ số chiến dịch tối thiểu, hãy kéo thanh trượt xuống thấp hơn.")
    else:
        st.altair_chart(metric_chart(d2.rename(columns={"adset_platform": "Ad set"}), "Ad set", metric2,
                                     horizontal=True, height=max(300, 24 * len(d2))), width="stretch")
        st.write(f"Tốt nhất: **{d2.iloc[0]['adset_platform']}** ({vn(d2.iloc[0][metric2])}). "
                 f"Kém nhất: **{d2.iloc[-1]['adset_platform']}** ({vn(d2.iloc[-1][metric2])}).")

    st.subheader("ROAS theo nhóm ad set và nền tảng")
    st.write("Mỗi ô là ROAS trung vị của một nhóm ad set trên một nền tảng; màu đậm hơn là hiệu quả tốt hơn. Ô trống là nền tảng đó không có nhóm này.")
    pv = df.pivot_table(index="ad_set_group", columns="platform", values="ROAS", aggfunc="median").reset_index()
    pv = pv.melt("ad_set_group", var_name="platform", value_name="ROAS").dropna()
    hm = alt.Chart(pv).mark_rect().encode(x=alt.X("platform:N", title=""), y=alt.Y("ad_set_group:N", title=""),
                                          color=alt.Color("ROAS:Q", scale=alt.Scale(scheme="yellowgreenblue")))
    tx = alt.Chart(pv).mark_text(fontSize=12).encode(x="platform:N", y="ad_set_group:N",
                                                    text=alt.Text("ROAS:Q", format=".2f"))
    st.altair_chart((hm + tx).properties(height=300), width="stretch")

# ---------------------------------------------------------------- tab thời gian
with tab3:
    dd = df.dropna(subset=["date"])
    if dd.empty:
        st.write("Không có dòng nào có ngày hợp lệ trong bộ lọc hiện tại.")
    else:
        daily = summarize(dd, "date").reset_index()
        sale = pd.DataFrame({"date": [pd.Timestamp("2024-05-05")], "nhãn": ["Ngày sale 5/5"]})
        rule = alt.Chart(sale).mark_rule(color="black", strokeDash=[4, 4]).encode(x="date:T")
        rtxt = alt.Chart(sale).mark_text(align="left", dx=4, baseline="top", fontSize=11).encode(
            x="date:T", y=alt.value(2), text="nhãn:N")
        st.write("**Chi phí và doanh thu mỗi ngày.** Cột xám là tiền bỏ ra, cột xanh là tiền thu về; khoảng cách giữa hai cột càng lớn thì ngày đó càng có lời.")
        long = daily.melt("date", value_vars=["Tổng chi phí", "Tổng doanh thu"], var_name="Loại", value_name="Giá trị")
        top = alt.Chart(long).mark_bar().encode(
            x=alt.X("date:T", title="", axis=alt.Axis(format="%d/%m")), y=alt.Y("Giá trị:Q", title=""), xOffset="Loại:N",
            color=alt.Color("Loại:N", scale=alt.Scale(range=["#9aa5b1", "#0b6bcb"])),
            tooltip=["date:T", "Loại", alt.Tooltip("Giá trị:Q", format=",.0f")])
        st.altair_chart((top + rule + rtxt).properties(height=260), width="stretch")

        st.write("**ROAS mỗi ngày.** Trục bắt đầu từ 0 để không làm các dao động nhỏ trông lớn hơn thực tế. "
                 "Đường nét đứt là ROAS trung bình của cả giai đoạn đang xem.")
        avg = pd.DataFrame({"ROAS": [roas]})
        line = alt.Chart(daily).mark_line(point=True, color="#ee4d2d").encode(
            x=alt.X("date:T", title="", axis=alt.Axis(format="%d/%m")),
            y=alt.Y("ROAS:Q", scale=alt.Scale(domain=[0, 7])),
            tooltip=["date:T", alt.Tooltip("ROAS:Q", format=".2f")])
        avg_rule = alt.Chart(avg).mark_rule(color="gray", strokeDash=[3, 3]).encode(y="ROAS:Q")
        st.altair_chart((line + avg_rule + rule).properties(height=200), width="stretch")

    st.subheader("Trước, trong và sau ngày sale")
    if df["phase"].notna().any():
        st.dataframe(summarize(df.dropna(subset=["phase"]), "phase").style.format("{:,.2f}"), width="stretch")
    else:
        st.write("Không có dòng nào có ngày trong bộ lọc hiện tại.")
    st.subheader("Cuối tuần và ngày thường")
    if df["day_type"].notna().any():
        st.dataframe(summarize(df.dropna(subset=["day_type"]), "day_type").style.format("{:,.2f}"), width="stretch")
    else:
        st.write("Không có dòng nào có ngày trong bộ lọc hiện tại.")

# ---------------------------------------------------------------- tab chuyển ngân sách
with tab4:
    st.write("Thử xem nếu bớt tiền ở một nền tảng rồi dồn sang nơi hiệu quả hơn thì doanh thu thay đổi ra sao. "
             "Phép tính giả định ROAS của mỗi nền tảng giữ nguyên khi đổi ngân sách. Thực tế tăng chi thường làm ROAS giảm, "
             "nên đây chỉ là ước lượng cho thấy hướng đi, không phải con số chắc chắn.")
    bp = summarize(df, "platform")
    plats = list(bp.index)
    a, b = st.columns(2)
    src = a.selectbox("Bớt ngân sách ở", plats, index=plats.index("TikTok") if "TikTok" in plats else 0)
    others = [p for p in plats if p != src]
    dest = b.multiselect("Dồn sang", others, default=[p for p in ["Facebook", "Shopee Ads"] if p in others] or others[:1])
    pct = st.slider("Chuyển bao nhiêu % ngân sách của nền tảng nguồn", 0, 30, 10)
    if not dest:
        st.write("Hãy chọn ít nhất một nền tảng để dồn ngân sách sang.")
    else:
        ok = df.dropna(subset=["spend", "revenue"])
        sp = ok.groupby("platform")["spend"].sum()
        roas_dest = (bp.loc[dest, "ROAS"] * sp[dest]).sum() / sp[dest].sum()
        per_pct = sp[src] / 100 * (roas_dest - bp.loc[src, "ROAS"])      # doanh thu tăng thêm cho mỗi 1%
        gain = per_pct * pct
        m = st.columns(4)
        m[0].metric(f"ROAS của {src}", vn(bp.loc[src, "ROAS"]))
        m[1].metric("ROAS bình quân nơi nhận", vn(roas_dest))
        m[2].metric("Số tiền chuyển", vn(sp[src] * pct / 100, 0))
        m[3].metric("Doanh thu tăng thêm", vn(gain, 0), f"{gain / ok['revenue'].sum() * 100:+.2f}% tổng doanh thu".replace(".", ","))
        sweep = pd.DataFrame({"pct": range(0, 31, 5)})
        sweep["gain"] = sweep["pct"] * per_pct
        ln = alt.Chart(sweep).mark_line(point=True, color="#0b6bcb").encode(
            x=alt.X("pct:Q", title="% ngân sách chuyển đi"), y=alt.Y("gain:Q", title="Doanh thu tăng thêm"),
            tooltip=["pct", alt.Tooltip("gain:Q", format=",.0f")])
        cur_pt = alt.Chart(pd.DataFrame({"pct": [pct], "gain": [gain]})).mark_point(size=120, color="#ee4d2d", filled=True).encode(
            x="pct:Q", y="gain:Q")
        st.altair_chart((ln + cur_pt).properties(height=260), width="stretch")
        st.caption("Chấm đỏ là mức bạn đang chọn. Đường thẳng vì mô phỏng giả định ROAS không đổi.")

# ---------------------------------------------------------------- tab dữ liệu
with tab5:
    log = ss.files[cur].get("log")
    if log:
        st.subheader("Báo cáo làm sạch của file đang xem")
        st.write("Đây là những gì app đã sửa trên file gốc trước khi phân tích. Các quy tắc giống với notebook làm sạch.")
        st.dataframe(pd.DataFrame(log, columns=["Hạng mục", "Kết quả"]), width="stretch", hide_index=True)
        st.download_button("Tải file đã làm sạch (CSV)", df_all.drop(columns=["adset_platform"]).to_csv(index=False).encode("utf-8-sig"),
                           "du_lieu_da_lam_sach.csv", "text/csv")
    st.subheader("Các file đã tải trong phiên này")
    hist = pd.DataFrame([{
        "File": n, "Số dòng": len(v["df"]), "Tải lúc": v["time"].strftime("%H:%M:%S"),
        "Tổng chi phí": v["df"]["spend"].sum(), "ROAS chung": ratio(v["df"], "revenue", "spend"),
        "Nguồn": "làm sạch tự động" if v.get("log") else "đã làm sạch sẵn",
        "Đang xem": "✓" if n == cur else ""} for n, v in ss.files.items()])
    st.dataframe(hist.style.format({"Số dòng": "{:,}", "Tổng chi phí": "{:,.0f}", "ROAS chung": "{:.2f}"}),
                 width="stretch", hide_index=True)
    st.subheader("Dữ liệu đang xem")
    st.write(f"{vn(len(df), 0)} dòng sau khi lọc")
    show = df.drop(columns=["adset_platform"])
    st.dataframe(show, width="stretch", height=380)
    st.download_button("Tải dữ liệu đã lọc (CSV)", show.to_csv(index=False).encode("utf-8-sig"),
                       "du_lieu_da_loc.csv", "text/csv")
