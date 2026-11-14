"""
OmniMarket AI - Hệ thống Hợp nhất với Menu Danh mục bên trái (Sidebar Navigation)
Chạy ứng dụng:
    streamlit run app2.py
"""

from datetime import datetime
import io
from pathlib import Path
import re
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# Thử import hàm làm sạch từ cleaning.py nếu có
try:
    from cleaning import RAW_COLS, clean_raw
    HAS_LOCAL_CLEANING = True
except ImportError:
    HAS_LOCAL_CLEANING = False
    RAW_COLS = ["campaign_name", "platform", "ad_set", "spend", "clicks", "impressions", "conversions", "revenue", "date"]

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG VÀ GIAO DIỆN CHUẨN ENTERPRISE
# ---------------------------------------------------------
st.set_page_config(
    page_title="OmniMarket AI - Quản Trị & Phân Tích",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}
.kpi-card {
    background: #131c31;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: 0 4px 15px -2px rgba(0, 0, 0, 0.3);
}
.kpi-title {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 1.65rem;
    font-weight: 800;
    color: #ffffff;
}
.badge-status {
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    display: inline-block;
}
.status-pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.status-approved { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.status-rejected { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.07); padding: 10px 14px; border-radius: 6px;}
[data-testid="stAppDeployButton"], .stDeployButton {display: none !important;}
</style>
""", unsafe_allow_html=True)

DATA_FILE = Path(__file__).parent / "shopee_5_5_cleaned.csv"
COLORS = {"Facebook": "#1877f2", "TikTok": "#111111", "Google": "#34a853",
          "Instagram": "#c13584", "Shopee Ads": "#ee4d2d", "Khác": "#64748b"}
COLOR_SCALE = alt.Scale(domain=list(COLORS), range=list(COLORS.values()))

METRICS = {
    "ROAS": ("doanh thu trên mỗi 1 đồng chi quảng cáo", True),
    "CPA": ("chi phí để có 1 đơn hàng", False),
    "CVR (%)": ("trong 100 lượt click thì có bao nhiêu đơn", True),
    "CTR (%)": ("trong 100 lượt hiển thị thì có bao nhiêu lượt click", True),
    "CPC": ("chi phí cho mỗi lượt click", False),
    "AOV": ("giá trị trung bình của một đơn hàng", True),
}

# ---------------------------------------------------------
# 2. KHỞI TẠO BỘ NHỚ PHIÊN (SESSION STATE)
# ---------------------------------------------------------
@st.cache_resource
def get_store():
    """Kho dữ liệu dùng chung cho mọi phiên trình duyệt (tài khoản, đề xuất, ngưỡng KPI).
    Giữ trong bộ nhớ của tiến trình Streamlit: tắt/khởi động lại app thì mất."""
    return {
        "users": {
            "director": {"password": "123", "name": "Nguyễn Giám Đốc", "role": "director", "label": "Giám Đốc (CEO / CMO)"},
            "user": {"password": "123", "name": "Trần Media Buyer", "role": "user", "label": "Chuyên Viên (Media Buyer)"},
            "admin": {"password": "123", "name": "Lê Quản Trị Viên", "role": "admin", "label": "Quản Trị Hệ Thống (Admin)"},
        },
        "proposals": [
            {"id": "PRJ-01", "title": "Tăng ngân sách Product Boost Shopee Sale 6.6", "creator": "Trần Media Buyer",
             "platform": "Shopee Ads", "budget": 25000000.0, "expected_revenue": 160000000.0,
             "reason": "Dựa trên số liệu đợt 5.5, Product Boost đạt ROAS 6,77 và CPA thấp nhất trong các nhóm quảng cáo.",
             "status": "Chờ duyệt", "feedback": "", "date": "2026-05-15"},
            {"id": "PRJ-02", "title": "Cắt giảm Live Ads TikTok chuyển sang Lookalike Facebook", "creator": "Trần Media Buyer",
             "platform": "Facebook", "budget": 40000000.0, "expected_revenue": 240000000.0,
             "reason": "Mô phỏng What-If: chuyển 10% ngân sách TikTok sang Facebook và Shopee Ads tăng khoảng 1,0% doanh thu (ước lượng, giả định ROAS không đổi).",
             "status": "Đã duyệt", "feedback": "Đồng ý phân bổ đợt 1.", "date": "2026-05-12"},
        ],
        "target_roas": 4.5,
        "target_cpa": 25.0,
    }


STORE = get_store()


def next_proposal_id():
    """Mã đề xuất tiếp theo = số lớn nhất hiện có + 1 (không bị trùng sau khi xóa)."""
    nums = [int(p["id"].split("-")[1]) for p in STORE["proposals"] if p["id"].split("-")[-1].isdigit()]
    return f"PRJ-{(max(nums) if nums else 0) + 1:02d}"


if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "Xin chào! Mình là trợ lý tiếp thị, trả lời theo quy tắc và tính số trực tiếp từ dữ liệu đang xem. Bạn muốn hỏi về ROAS, CPA, TikTok hay ad set tốt nhất?"}
    ]

if "user_info" not in st.session_state:
    st.session_state.user_info = None


# ---------------------------------------------------------
# 3. CÁC HÀM XỬ LÝ DỮ LIỆU
# ---------------------------------------------------------
def vn(x, d=2):
    if pd.isna(x):
        return "–"
    return f"{x:,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")

def ratio(g, num, den):
    m = g[num].notna() & g[den].notna()
    d = g.loc[m, den].sum()
    return g.loc[m, num].sum() / d if m.any() and d > 0 else np.nan

def summarize(data, by):
    rows = []
    for k, g in data.groupby(by, dropna=True):
        rows.append({
            by: k,
            "Số chiến dịch": len(g),
            "Tổng chi phí": g["spend"].sum(),
            "Tổng doanh thu": g["revenue"].sum(),
            "CTR (%)": ratio(g, "clicks", "impressions") * 100,
            "CPC": ratio(g, "spend", "clicks"),
            "CVR (%)": ratio(g, "conversions", "clicks") * 100,
            "CPA": ratio(g, "spend", "conversions"),
            "AOV": ratio(g, "revenue", "conversions"),
            "ROAS": ratio(g, "revenue", "spend")
        })
    return pd.DataFrame(rows).set_index(by)

def _read(file, **kw):
    name = str(getattr(file, "name", file)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file, **kw)
    return pd.read_csv(file, encoding="utf-8-sig", **kw)

def load_upload(file):
    try:
        head = _read(file, dtype=str)
    except Exception:
        raise ValueError("Không đọc được file dạng bảng. Vui lòng chọn file CSV hoặc Excel (.xlsx).")
    
    NEED_COLS = ["campaign_name", "platform", "ad_set", "spend", "clicks", "impressions", "conversions",
                 "revenue", "date", "ROAS", "ad_set_group", "phase", "day_type"]
    
    log = None
    if all(c in head.columns for c in NEED_COLS):
        if hasattr(file, "seek"):
            file.seek(0)
        df = _read(file)
    else:
        if not HAS_LOCAL_CLEANING:
            raise ValueError("Thiếu file cleaning.py cùng thư mục với app2.py nên không làm sạch được file gốc.")
        missing = [c for c in RAW_COLS if c not in head.columns]
        if missing:
            raise ValueError("thiếu cột " + ", ".join(missing) + ". File cần có đủ các cột: " + ", ".join(RAW_COLS) + ".")
        df, log = clean_raw(head)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["adset_platform"] = df["ad_set"] + " (" + df["platform"] + ")"
    return df, log

def metric_chart(d, cat, metric, horizontal=False, height=320):
    val = alt.Y(field=metric, type="quantitative", title=metric) if not horizontal else \
        alt.X(field=metric, type="quantitative", title=metric)
    ax = alt.Y(field=cat, type="nominal", sort=None, title="") if horizontal else \
        alt.X(field=cat, type="nominal", sort=None, title="")
    enc = dict(color=alt.Color("platform:N", scale=COLOR_SCALE, legend=None if not horizontal else alt.Legend(title="Nền tảng")),
               tooltip=[cat, alt.Tooltip(field=metric, type="quantitative", format=".2f"), "Số chiến dịch"])
    bars = alt.Chart(d).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        **({"y": ax, "x": val} if horizontal else {"x": ax, "y": val}), **enc)
    txt_kw = dict(align="left", dx=4) if horizontal else dict(dy=-7)
    txt = alt.Chart(d).mark_text(fontSize=11, **txt_kw).encode(
        **({"y": ax, "x": val} if horizontal else {"x": ax, "y": val}),
        text=alt.Text(field=metric, type="quantitative", format=".2f"))
    return (bars + txt).properties(height=height).configure_view(strokeOpacity=0)

def kpi_alerts(data):
    """Các cặp (ad set, nền tảng) có ROAS dưới sàn hoặc CPA trên trần do Admin đặt."""
    ba = summarize(data, "adset_platform")
    ba = ba[ba["Số chiến dịch"] >= 10]
    bad = ba[(ba["ROAS"] < STORE["target_roas"]) | (ba["CPA"] > STORE["target_cpa"])]
    return bad[["Số chiến dịch", "ROAS", "CPA"]].sort_values("ROAS")

def tier_summary(data, tol):
    """Phân hạng ad set theo ROAS so với ROAS chung: Ngôi sao / Tiềm năng / Cần xem xét."""
    ba = summarize(data, "adset_platform")
    ba = ba[ba["Số chiến dịch"] >= 10].copy()
    base = ratio(data, "revenue", "spend")
    ba["Hạng"] = np.where(ba["ROAS"] >= base * (1 + tol / 100), "Ngôi sao",
                          np.where(ba["ROAS"] < base * (1 - tol / 100), "Cần xem xét", "Tiềm năng"))
    ok = data.dropna(subset=["spend", "revenue"]).groupby("adset_platform")[["spend", "revenue"]].sum()
    ba = ba.join(ok.rename(columns={"spend": "_sp", "revenue": "_rv"}))
    t = ba.groupby("Hạng").agg(**{"Số ad set": ("ROAS", "size"), "sp": ("_sp", "sum"), "rv": ("_rv", "sum")})
    t["ROAS"] = t["rv"] / t["sp"]
    t["% chi phí"] = t["sp"] / t["sp"].sum() * 100
    t["% doanh thu"] = t["rv"] / t["rv"].sum() * 100
    t = t.reindex([h for h in ["Ngôi sao", "Tiềm năng", "Cần xem xét"] if h in t.index])
    return ba, t[["Số ad set", "% chi phí", "% doanh thu", "ROAS"]], base

def answer_question(q, data):
    """Trợ lý theo quy tắc: nhận diện từ khóa rồi tính số từ dữ liệu đang lọc (không dùng mô hình ngôn ngữ)."""
    q = q.lower()
    bp = summarize(data, "platform")
    if bp.empty:
        return "Chưa có dữ liệu để trả lời."
    ba = summarize(data, "adset_platform")
    ba = ba[ba["Số chiến dịch"] >= 10]
    sp = data.dropna(subset=["spend", "revenue"]).groupby("platform")["spend"].sum()
    if "tiktok" in q or "giảm" in q or "cắt" in q:
        if "TikTok" in bp.index:
            t = bp.loc["TikTok"]
            tk = ba[ba.index.str.endswith("(TikTok)")].sort_values("ROAS")
            weak = f" Ad set yếu nhất của TikTok: {tk.index[0]} (ROAS {vn(tk['ROAS'].iloc[0])})." if len(tk) else ""
            return (f"TikTok có ROAS {vn(t['ROAS'])}, CPA {vn(t['CPA'])}, chiếm {vn(sp['TikTok'] / sp.sum() * 100, 1)}% chi phí.{weak} "
                    "Có thể đề xuất giảm bớt ngân sách ở các ad set ROAS thấp rồi thử chuyển sang kênh có ROAS cao hơn; nên giảm từng bước và theo dõi lại.")
    if "cpa" in q or "chi phí" in q:
        b = bp["CPA"].idxmin()
        top = ba.sort_values("CPA").head(2)
        return (f"Nền tảng có CPA thấp nhất là {b} ({vn(bp.loc[b, 'CPA'])}). Ad set có CPA thấp nhất: "
                + ", ".join(f"{i} ({vn(r['CPA'])})" for i, r in top.iterrows()) + ".")
    if "ad set" in q or "adset" in q or "nhóm" in q:
        top = ba.sort_values("ROAS", ascending=False).head(3)
        return "Ba ad set có ROAS cao nhất: " + ", ".join(f"{i} ({vn(r['ROAS'])})" for i, r in top.iterrows()) + "."
    if "roas" in q or "hiệu quả" in q or "tốt nhất" in q:
        b = bp["ROAS"].idxmax()
        top = ba.sort_values("ROAS", ascending=False).head(2)
        return (f"Nền tảng có ROAS cao nhất là {b} ({vn(bp.loc[b, 'ROAS'])}). Ad set nổi bật: "
                + ", ".join(f"{i} ({vn(r['ROAS'])})" for i, r in top.iterrows()) + ".")
    return ("Mình trả lời được các câu hỏi về ROAS/hiệu quả, CPA/chi phí, TikTok và ad set tốt nhất. "
            f"Ví dụ: 'kênh nào có ROAS tốt nhất?'. ROAS chung của dữ liệu đang xem là {vn(ratio(data, 'revenue', 'spend'))}.")

# ---------------------------------------------------------
# 4. MÀN HÌNH ĐĂNG NHẬP (NẾU CHƯA ĐĂNG NHẬP)
# ---------------------------------------------------------
def login_screen():
    st.markdown(
        """
        <div style="text-align: center; padding: 3rem 0 1.5rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">💎</div>
            <h1 style="font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">OmniMarket AI</h1>
            <p style="color: #94a3b8; font-size: 1.05rem; max-width: 540px; margin: auto;">Hệ thống Hỗ trợ Ra Quyết định & Phân tích Tiếp thị Đa nền tảng Doanh nghiệp</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, col2, _ = st.columns([1, 1.15, 1])
    with col2:
        with st.container(border=True):
            st.markdown("#### 🔐 Đăng nhập Workspace")
            username = st.text_input("Tên đăng nhập", placeholder="director / user / admin", value="director")
            password = st.text_input("Mật khẩu", type="password", value="123")

            if st.button("Truy Cập Hệ Thống ➔", type="primary", use_container_width=True):
                users = STORE["users"]
                if username in users and users[username]["password"] == password:
                    st.session_state.user_info = users[username]
                    st.rerun()
                else:
                    st.error("Tên đăng nhập hoặc mật khẩu không chính xác!")

            st.markdown(
                """
                <div style="background: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 12px; margin-top: 15px; font-size: 0.82rem; color: #94a3b8;">
                    <strong>Tài khoản sẵn có để thử:</strong><br/>
                    • Giám đốc: <code>director</code> | <code>123</code><br/>
                    • Nhân viên: <code>user</code> | <code>123</code><br/>
                    • Quản trị viên: <code>admin</code> | <code>123</code>
                </div>
                """,
                unsafe_allow_html=True,
            )

if st.session_state.user_info is None:
    login_screen()
    st.stop()

# ---------------------------------------------------------
# 5. THANH BÊN (SIDEBAR): DANH MỤC ĐIỀU HƯỚNG & CÔNG CỤ
# ---------------------------------------------------------
user = st.session_state.user_info
role = user["role"]
ss = st.session_state

def label_file(n):
    f = ss.files[n]
    return f"{n} · {vn(len(f['df']), 0)} dòng"

if "files" not in ss:
    ss.files, ss.seen = {}, set()
    sample_candidates = [
        DATA_FILE,
        Path("shopee_5_5_cleaned.csv"),
        Path(__file__).parent / "BTL_PTDL-main" / "shopee_5_5_cleaned.csv",
    ]
    for p in sample_candidates:
        if p.exists():
            d0, l0 = load_upload(p)
            ss.files["Shopee 5.5 (mẫu)"] = {"df": d0, "log": l0, "time": datetime.now()}
            ss.pick = label_file("Shopee 5.5 (mẫu)")
            break

with st.sidebar:
    # 5.1 Hồ sơ người dùng
    st.markdown(
        f"""
        <div style="background: rgba(255, 255, 255, 0.04); padding: 14px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="background: linear-gradient(135deg, #4f46e5, #06b6d4); width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px;">
                    💎
                </div>
                <div>
                    <div style="font-weight: 700; font-size: 15px; color: #f8fafc;">{user['name']}</div>
                    <div style="font-size: 11px; color: #10b981;">● Đang hoạt động</div>
                </div>
            </div>
            <div style="margin-top: 8px; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 6px; padding: 3px 6px; font-size: 11px; color: #a5b4fc; text-align: center; font-weight: 600;">
                {user['label']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state.user_info = None
        st.rerun()

    st.markdown("---")

    # 5.2 DANH MỤC ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR NAVIGATION)
    st.markdown("### 📌 DANH MỤC CHỨC NĂNG")
    
    # Danh mục dùng chung
    nav_options = [
        "📊 Dashboard Tổng Quan",
        "🏬 Phân Tích Nền Tảng",
        "🎯 Phân Tích Ad Set",
        "⏱️ Xu Hướng Thời Gian",
        "📄 Bảng Dữ Liệu Chi Tiết",
    ]
    
    # Bổ sung danh mục theo quyền
    if role == "director":
        nav_options.insert(1, "📑 Phê Duyệt & Cấp Ngân Sách")
        nav_options.insert(2, "💼 Khuyến Nghị Phân Bổ 70/20/10")
        nav_options.insert(3, "🎛️ Chuyển Ngân Sách What-If")
    elif role == "user":
        nav_options.insert(1, "📋 Đề Xuất Của Tôi (Xem & Xóa)")
        nav_options.insert(2, "➕ Tạo Đề Xuất Dự Án Mới")
        nav_options.insert(3, "💬 Cố Vấn Tiếp Thị AI")
    elif role == "admin":
        nav_options.insert(1, "👥 Phân Quyền & Thêm Tài Khoản")
        nav_options.insert(2, "🚀 Khảo Sát Nâng Cấp Hệ Thống")
        nav_options.insert(3, "⚙️ Cài Đặt Ngưỡng Cảnh Báo KPI")

    selected_menu = st.radio("Chọn chức năng để xem:", nav_options, index=0)

    st.markdown("---")

    # 5.3 Quản lý tệp dữ liệu
    with st.expander("📂 **Tải & Quản Lý File**"):
        uploads = st.file_uploader("Tải file (CSV, Excel)", type=["csv", "xlsx"], accept_multiple_files=True)
        for f in uploads or []:
            sig = (f.name, f.size)
            if sig in ss.seen: continue
            try:
                data, log = load_upload(f)
            except Exception as e:
                st.error(f"{f.name}: {e}")
                continue
            name, n = f.name, 2
            while name in ss.files:
                name, n = f"{f.name} ({n})", n + 1
            ss.files[name] = {"df": data, "log": log, "time": datetime.now()}
            ss.seen.add(sig)
            ss.pick = label_file(name)
            ss.pick_file = label_file(name)

        names = list(ss.files)
        if names:
            labels = {label_file(n): n for n in names}
            if ss.get("pick") not in labels:
                ss.pick = list(labels)[-1]
            pick = st.radio("Phiên dữ liệu:", list(labels), key="pick_file")
            cur = labels[pick]
            df_all = ss.files[cur]["df"]
        else:
            st.stop()

        template_csv = "campaign_id,campaign_name,platform,ad_set,spend,clicks,impressions,conversions,revenue,date\nC1001,Shopee Sale 5.5,Facebook,Lookalike 1%,1500,1200,25000,70,8500,2024-05-05"
        st.download_button("📥 Tải Template Mẫu (.CSV)", template_csv.encode("utf-8-sig"), "template.csv", "text/csv", use_container_width=True)

    # 5.4 Bộ lọc dữ liệu
    with st.expander("🔍 **Bộ Lọc Nâng Cao**", expanded=True):
        opts = lambda col: sorted(df_all[col].dropna().unique())
        sel_p = st.multiselect("Kênh quảng cáo:", opts("platform"), default=opts("platform"), key=f"{cur}|p")
        sel_g = st.multiselect("Nhóm Ad Set:", opts("ad_set_group"), default=opts("ad_set_group"), key=f"{cur}|g")
        
        mask = df_all["platform"].isin(sel_p) & df_all["ad_set_group"].isin(sel_g)
        d_min, d_max = df_all["date"].min(), df_all["date"].max()
        if pd.notna(d_min) and d_min < d_max:
            rng = st.date_input("Khoảng ngày:", (d_min.date(), d_max.date()), d_min.date(), d_max.date(), key=f"{cur}|d")
            keep = st.checkbox("Giữ dòng thiếu ngày", True, key=f"{cur}|k")
            if isinstance(rng, tuple) and len(rng) == 2:
                mask &= df_all["date"].between(pd.Timestamp(rng[0]), pd.Timestamp(rng[1])) | (df_all["date"].isna() & keep)
        
        df = df_all[mask]

# Kiểm tra dữ liệu
if df.empty:
    st.warning("Không có dữ liệu khớp với bộ lọc đang chọn.")
    st.stop()

# ---------------------------------------------------------
# 6. KHU VỰC HIỂN THỊ NỘI DUNG THEO DANH MỤC ĐƯỢC CHỌN
# ---------------------------------------------------------
st.markdown(
    f"""
    <div style="margin-bottom: 1.2rem;">
        <h2 style="font-weight: 800; letter-spacing: -0.02em; margin-bottom: 0.2rem;">{selected_menu}</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">Phiên dữ liệu: <strong>{cur}</strong> | Số dòng đang hiển thị: <strong>{vn(len(df), 0)}/{vn(len(df_all), 0)}</strong></p>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# CHỨC NĂNG 1: DASHBOARD TỔNG QUAN
# =========================================================
if selected_menu == "📊 Dashboard Tổng Quan":
    roas, cpa = ratio(df, "revenue", "spend"), ratio(df, "spend", "conversions")
    cvr, ctr = ratio(df, "conversions", "clicks") * 100, ratio(df, "clicks", "impressions") * 100
    tot_spend, tot_rev = df["spend"].sum(), df["revenue"].sum()
    ok = df.dropna(subset=["spend", "revenue"])
    if role == "director":
        c = st.columns(5)
        c[0].metric("Tổng Chi Phí", vn(tot_spend, 0))
        c[1].metric("Tổng Doanh Thu", vn(tot_rev, 0))
        c[2].metric("Doanh Thu − Chi Phí QC", vn(ok["revenue"].sum() - ok["spend"].sum(), 0),
                    help="Chưa trừ giá vốn hàng bán nên chưa phải lợi nhuận. Chỉ tính các dòng có đủ chi phí và doanh thu.")
        c[3].metric("ROAS Toàn Sàn", vn(roas))
        c[4].metric("CPA Trung Bình", vn(cpa))
    else:
        c = st.columns(4)
        c[0].metric("Tổng Chi Phí", vn(tot_spend, 0))
        c[1].metric("Tổng Doanh Thu", vn(tot_rev, 0))
        c[2].metric("ROAS Toàn Sàn", vn(roas))
        c[3].metric("CPA Trung Bình", vn(cpa))

    st.markdown("---")
    st.subheader("Cảnh Báo KPI")
    st.write(f"Ngưỡng do Quản trị viên đặt: ROAS tối thiểu {vn(STORE['target_roas'], 1)}, CPA tối đa {vn(STORE['target_cpa'], 1)}. "
             "Danh sách dưới đây là các ad set (đủ ít nhất 10 chiến dịch) chưa đạt ngưỡng.")
    alerts = kpi_alerts(df)
    if alerts.empty:
        st.write("Không có ad set nào chưa đạt ngưỡng.")
    else:
        st.dataframe(alerts.style.format("{:,.2f}"), width="stretch")

    if role == "director":
        st.markdown("---")
        st.subheader("Chi Phí & Doanh Thu: Kênh Nào Chiếm Bao Nhiêu?")
        st.write("Cột doanh thu thấp hơn cột chi phí nghĩa là kênh đó tốn nhiều ngân sách hơn phần doanh thu mang lại.")
        both = ok.groupby("platform")[["spend", "revenue"]].sum()
        share = (both / both.sum() * 100).rename(columns={"spend": "Chi phí", "revenue": "Doanh thu"}).reset_index()
        sh = share.melt("platform", var_name="Loại", value_name="Tỉ trọng (%)")
        base = alt.Chart(sh).encode(x=alt.X("platform:N", title="Kênh quảng cáo"), xOffset="Loại:N")
        bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            y=alt.Y("Tỉ trọng (%):Q", title="Tỉ trọng đóng góp (%)"),
            color=alt.Color("Loại:N", scale=alt.Scale(range=["#ef4444", "#3b82f6"])))
        lab = base.mark_text(dy=-7, fontSize=11).encode(y="Tỉ trọng (%):Q", text=alt.Text("Tỉ trọng (%):Q", format=".1f"))
        st.altair_chart((bars + lab).properties(height=340), use_container_width=True)

# =========================================================
# CHỨC NĂNG: GIÁM ĐỐC - PHÊ DUYỆT DỰ ÁN
# =========================================================
elif selected_menu == "📑 Phê Duyệt & Cấp Ngân Sách":
    proposals = STORE["proposals"]
    pending_count = sum(1 for p in proposals if p["status"] == "Chờ duyệt")
    approved_budget = sum(p["budget"] for p in proposals if p["status"] == "Đã duyệt")

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Đề Xuất Chờ Duyệt</div><div class="kpi-value">{pending_count} <span style="font-size:1rem;color:#fbbf24;">dự án</span></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Ngân Sách Đã Cấp</div><div class="kpi-value">{approved_budget:,.0f} <span style="font-size:1rem;color:#34d399;">đ</span></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Tổng Số Dự Án</div><div class="kpi-value">{len(proposals)} <span style="font-size:1rem;color:#94a3b8;">hồ sơ</span></div></div>', unsafe_allow_html=True)

    st.markdown("### Danh Sách Dự Án Đề Xuất Chờ Phê Duyệt")
    for idx, p in enumerate(proposals):
        with st.container(border=True):
            col_head, col_b = st.columns([4, 1.2])
            col_head.markdown(f"#### **[{p['id']}] {p['title']}**")
            badge_class = {"Chờ duyệt": "status-pending", "Đã duyệt": "status-approved", "Từ chối": "status-rejected"}.get(p["status"], "status-pending")
            col_b.markdown(f'<span class="badge-status {badge_class}">● {p["status"]}</span>', unsafe_allow_html=True)

            st.markdown(
                f"**Chuyên viên:** `{p['creator']}` | **Kênh triển khai:** `{p['platform']}` | **Ngày nộp:** `{p['date']}`\n\n"
                f"• **Ngân sách xin cấp:** `{p['budget']:,.0f} đ`  \n"
                f"• **Doanh thu kỳ vọng:** `{p['expected_revenue']:,.0f} đ` *(ROAS dự kiến: `{(p['expected_revenue']/p['budget']):.2f}x`)*  \n"
                f"• **Luận cứ chiến lược:** {p['reason']}"
            )
            if p.get("feedback"):
                st.info(f"💬 **Chỉ đạo của Giám đốc:** {p['feedback']}")

            if p["status"] == "Chờ duyệt":
                b1, b2, b_comm = st.columns([1.2, 1, 3])
                feedback_text = b_comm.text_input("Ghi chú phê duyệt", key=f"f_{idx}", placeholder="Ý kiến chỉ đạo cấp vốn...")
                if b1.button("✅ Phê Duyệt & Cấp Vốn", key=f"app_{idx}", type="primary", use_container_width=True):
                    STORE["proposals"][idx]["status"] = "Đã duyệt"
                    STORE["proposals"][idx]["feedback"] = feedback_text if feedback_text else "Đồng ý cấp vốn triển khai."
                    st.success(f"Đã duyệt dự án [{p['id']}]!")
                    st.rerun()
                if b2.button("❌ Từ Chối", key=f"rej_{idx}", use_container_width=True):
                    STORE["proposals"][idx]["status"] = "Từ chối"
                    STORE["proposals"][idx]["feedback"] = feedback_text if feedback_text else "Cần tối ưu lại CPA."
                    st.warning(f"Đã từ chối dự án [{p['id']}]!")
                    st.rerun()

elif selected_menu == "💼 Khuyến Nghị Phân Bổ 70/20/10":
    st.subheader("Khung Chiến Lược Phân Bổ Ngân Sách 70/20/10")
    st.caption("Đây là khung đề xuất tham khảo của nhóm dựa trên kết quả phân tích đợt 5.5, không phải đầu ra của một mô hình tối ưu.")
    st.markdown("""
    - **70% Ngân sách Trụ cột (Core Performance):** Dồn vào **Facebook** (Prospecting Lookalike) và **Shopee Ads** (Product Boost, Keyword Auto) có ROAS từ 5,7 trở lên, CPA khoảng 18,6–20,0.
    - **20% Ngân sách Mở rộng (Growth):** Tối ưu lại **Google Search** bằng cách chặn từ khóa đắt đỏ để hạ CPC (đang ở mức 1,87), giữ chân khách hàng có CVR 7,0%.
    - **10% Ngân sách Thử nghiệm (Experimentation):** Thu hẹp ngân sách video/livestream của **TikTok** (chỉ giữ nhóm có ROAS dương), chuyển sang xây dựng thương hiệu.
    """)

# =========================================================
# CHỨC NĂNG: USER - ĐỀ XUẤT CỦA TÔI / TẠO DỰ ÁN / CHAT AI
# =========================================================
elif selected_menu == "📋 Đề Xuất Của Tôi (Xem & Xóa)":
    st.subheader("Danh Sách Dự Án Do Bạn Đề Xuất")
    my_proposals = [p for p in STORE["proposals"] if p.get("creator") == user["name"]]

    if not my_proposals:
        st.info("💡 Bạn chưa có đề xuất nào. Hãy chọn mục **'➕ Tạo Đề Xuất Dự Án Mới'** ở danh mục bên trái để gửi dự án lên Giám đốc.")
    else:
        for p in my_proposals:
            with st.container(border=True):
                col_info, col_del = st.columns([5, 1.2])
                badge_class = {"Chờ duyệt": "status-pending", "Đã duyệt": "status-approved", "Từ chối": "status-rejected"}.get(p["status"], "status-pending")

                with col_info:
                    st.markdown(f"#### **[{p['id']}] {p['title']}**")
                    st.markdown(f'<span class="badge-status {badge_class}">● Trạng thái: {p["status"]}</span>', unsafe_allow_html=True)
                    st.markdown(
                        f"\n• **Kênh:** `{p['platform']}` | **Ngày nộp:** `{p['date']}`  \n"
                        f"• **Ngân sách xin cấp:** `{p['budget']:,.0f} đ` | **Doanh thu dự toán:** `{p['expected_revenue']:,.0f} đ`  \n"
                        f"• **Luận cứ:** {p['reason']}"
                    )
                    if p.get("feedback"):
                        st.info(f"💬 **Ý kiến Giám đốc:** {p['feedback']}")

                with col_del:
                    st.write("")
                    st.write("")
                    if p["status"] != "Chờ duyệt":
                        st.caption("Đã được xử lý, không xóa được")
                    elif st.button("🗑️ Xóa Đề Xuất", key=f"del_{p['id']}", use_container_width=True):
                        STORE["proposals"] = [item for item in STORE["proposals"] if item["id"] != p["id"]]
                        st.success(f"Đã xóa đề xuất [{p['id']}]!")
                        st.rerun()

elif selected_menu == "➕ Tạo Đề Xuất Dự Án Mới":
    st.subheader("Soạn Thảo Đề Xuất Dự Án Trình Giám Đốc")
    with st.form("create_proposal_form_side"):
        p_title = st.text_input("Tiêu đề dự án", placeholder="VD: Mở rộng ngân sách Lookalike 1% Facebook đợt Mega Sale 6.6...")
        col_p1, col_p2 = st.columns(2)
        p_platform = col_p1.selectbox("Kênh trọng tâm", ["Shopee Ads", "Facebook", "Google", "TikTok", "Instagram"])
        p_budget = col_p2.number_input("Ngân sách đề xuất (VNĐ)", min_value=1000000.0, value=25000000.0, step=1000000.0)

        col_p3, col_p4 = st.columns(2)
        p_rev = col_p3.number_input("Doanh thu mục tiêu (VNĐ)", min_value=1000000.0, value=150000000.0, step=1000000.0)
        est_roas = p_rev / p_budget if p_budget > 0 else 0
        col_p4.metric("ROAS dự kiến", f"{est_roas:.2f}x")

        p_reason = st.text_area("Luận cứ & Căn cứ số liệu", placeholder="VD: Dựa trên số liệu đợt sale trước, nhóm ad set này đạt CVR > 5.5% và CPA tối ưu...")
        if st.form_submit_button("🚀 Gửi Đề Xuất Lên Bàn Giám Đốc", type="primary"):
            if not p_title or not p_reason:
                st.error("Vui lòng điền đủ tiêu đề và luận cứ dự án!")
            else:
                new_proposal = {
                    "id": next_proposal_id(),
                    "title": p_title,
                    "creator": user["name"],
                    "platform": p_platform,
                    "budget": p_budget,
                    "expected_revenue": p_rev,
                    "reason": p_reason,
                    "status": "Chờ duyệt",
                    "feedback": "",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
                STORE["proposals"].insert(0, new_proposal)
                st.success("✅ Đã gửi đề xuất thành công tới Giám đốc! Hãy bấm qua mục 'Đề Xuất Của Tôi' để theo dõi.")
                st.rerun()

elif selected_menu == "💬 Cố Vấn Tiếp Thị AI":
    st.subheader("Trò Chuyện Trực Tiếp với Cố Vấn Marketing AI")
    st.caption("Trợ lý dựa trên quy tắc: nhận diện từ khóa trong câu hỏi rồi tính số trực tiếp từ dữ liệu đang xem, không dùng mô hình ngôn ngữ.")

    chat_box = st.container(height=380, border=True)
    for msg in st.session_state.chat_messages:
        with chat_box.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Hỏi về ROAS, CPA, TikTok hoặc ad set tốt nhất..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        st.session_state.chat_messages.append({"role": "assistant", "content": answer_question(prompt, df)})
        st.rerun()

# =========================================================
# CHỨC NĂNG: ADMIN - PHÂN QUYỀN / KHẢO SÁT / CẤU HÌNH
# =========================================================
elif selected_menu == "👥 Phân Quyền & Thêm Tài Khoản":
    st.subheader("Danh Sách Tài Khoản Phân Quyền")
    users_table = pd.DataFrame([
        {"Tài khoản": u, "Họ tên": d["name"], "Mã vai trò": d["role"], "Quyền hạn": d["label"]}
        for u, d in STORE["users"].items()
    ])
    st.table(users_table)

    st.divider()
    st.subheader("➕ Cấp Mới Tài Khoản & Gán Quyền")
    with st.form("add_user_form_side"):
        u1, u2 = st.columns(2)
        new_u = u1.text_input("Tên đăng nhập", placeholder="vd: analyst_lead")
        new_p = u2.text_input("Mật khẩu", type="password", value="123")

        u3, u4 = st.columns(2)
        new_name = u3.text_input("Họ và tên đầy đủ", placeholder="Phạm Văn B")
        new_r = u4.selectbox("Vai trò cấp quyền", ["user", "director", "admin"],
                             format_func=lambda x: {"director": "Giám Đốc (Phê duyệt)", "user": "Nhân viên (Tác nghiệp)", "admin": "Quản trị viên"}[x])

        if st.form_submit_button("Tạo Tài Khoản", type="primary"):
            if not new_u or not new_name:
                st.error("Vui lòng điền đủ tên tài khoản và họ tên!")
            elif new_u in STORE["users"]:
                st.error("Tài khoản này đã tồn tại!")
            else:
                r_labels = {"director": "Giám Đốc (CEO / CMO)", "user": "Nhân viên (Media Buyer)", "admin": "Quản trị hệ thống (Admin)"}
                STORE["users"][new_u] = {"password": new_p, "name": new_name, "role": new_r, "label": r_labels[new_r]}
                st.success(f"Đã tạo tài khoản '{new_u}' thành công!")
                st.rerun()

elif selected_menu == "🚀 Khảo Sát Nâng Cấp Hệ Thống":
    st.subheader("Báo Cáo Sức Khỏe & Khảo Sát Nâng Cấp Hệ Thống")
    c1, c2, c3 = st.columns(3)
    c1.metric("Phiên bản", "v4.0.0 Enterprise")
    c2.metric("Tài khoản vận hành", len(STORE["users"]))
    c3.metric("Hồ sơ dự án", len(STORE["proposals"]))

    with st.form("survey_form_side"):
        st.multiselect(
            "Chọn các module cần ưu tiên tích hợp kỳ tới:",
            [
                "Kết nối trực tiếp API Facebook Marketing & TikTok Ads (Auto-sync)",
                "Mô hình Machine Learning (XGBoost) dự báo doanh thu trước khi duyệt",
                "Gửi thông báo phê duyệt thời gian thực qua Telegram / Zalo ZNS",
                "Tự động xuất báo cáo Slide thuyết trình (.PPTX)",
            ],
            default=["Kết nối trực tiếp API Facebook Marketing & TikTok Ads (Auto-sync)"],
        )
        st.text_area("Đóng góp thêm ý kiến vận hành:")
        if st.form_submit_button("Gửi Khảo Sát", type="primary"):
            st.success("Đã ghi nhận đóng góp khảo sát nâng cấp hệ thống!")

elif selected_menu == "⚙️ Cài Đặt Ngưỡng Cảnh Báo KPI":
    st.subheader("Thiết Lập Ngưỡng Cảnh Báo KPI")
    with st.form("kpi_config_form_side"):
        t_roas = st.number_input("ROAS Sàn kỳ vọng", min_value=1.0, max_value=20.0, value=float(STORE["target_roas"]), step=0.1)
        t_cpa = st.number_input("CPA trần tối đa (cùng đơn vị với dữ liệu)", min_value=5.0, max_value=200.0, value=float(STORE["target_cpa"]), step=1.0)
        if st.form_submit_button("Lưu Thiết Lập", type="primary"):
            STORE["target_roas"] = t_roas
            STORE["target_cpa"] = t_cpa
            st.success("Đã cập nhật ngưỡng cảnh báo KPI!")

# =========================================================
# CÁC CHỨC NĂNG PHÂN TÍCH CHUYÊN SÂU
# =========================================================
elif selected_menu == "🏬 Phân Tích Nền Tảng":
    by_p = summarize(df, "platform")
    metric = st.selectbox("Chỉ số muốn so sánh", list(METRICS), key="side_m1")
    note, higher_better = METRICS[metric]
    st.write(f"**{metric}**: {note}. " + ("Càng cao càng tốt." if higher_better else "Càng thấp càng tốt."))
    d = by_p.reset_index().sort_values(metric, ascending=not higher_better)
    st.altair_chart(metric_chart(d, "platform", metric), width="stretch")

    st.subheader("Bảng Số Liệu Chi Tiết Theo Nền Tảng")
    st.dataframe(
        by_p.sort_values("ROAS", ascending=False).style.format(
            lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) and not pd.isna(x) else ("-" if pd.isna(x) else str(x))
        ),
        width="stretch"
    )

elif selected_menu == "🎯 Phân Tích Ad Set":
    by_a = summarize(df, "adset_platform")
    by_a["platform"] = by_a.index.str.rsplit("(", n=1).str[-1].str.rstrip(")")
    metric2 = st.selectbox("Chỉ số", list(METRICS), key="side_m2")
    min_n = st.slider("Chỉ hiện ad set có ít nhất … chiến dịch", 1, 60, 10, key="side_slider")
    hb2 = METRICS[metric2][1]
    d2 = by_a[by_a["Số chiến dịch"] >= min_n].reset_index().sort_values(metric2, ascending=not hb2)
    if not d2.empty:
        st.altair_chart(metric_chart(d2.rename(columns={"adset_platform": "Ad set"}), "Ad set", metric2, horizontal=True, height=max(300, 24 * len(d2))), width="stretch")
    
    st.subheader("Heatmap ROAS Theo Nhóm Ad Set & Nền Tảng")
    pv = df.pivot_table(index="ad_set_group", columns="platform", values="ROAS", aggfunc="median").reset_index()
    pv = pv.melt("ad_set_group", var_name="platform", value_name="ROAS").dropna()
    hm = alt.Chart(pv).mark_rect().encode(x=alt.X("platform:N", title=""), y=alt.Y("ad_set_group:N", title=""),
                                          color=alt.Color("ROAS:Q", scale=alt.Scale(scheme="yellowgreenblue")))
    tx = alt.Chart(pv).mark_text(fontSize=12).encode(x="platform:N", y="ad_set_group:N", text=alt.Text("ROAS:Q", format=".2f"))
    st.altair_chart((hm + tx).properties(height=300), width="stretch")

    st.subheader("Phân Hạng Ad Set Theo ROAS")
    tol = st.slider("Ngưỡng chênh lệch so với ROAS chung (%)", 5, 25, 10, key="tier_tol",
                    help="Ngôi sao: ROAS cao hơn ROAS chung ít nhất bằng ngưỡng. Cần xem xét: thấp hơn ROAS chung ít nhất bằng ngưỡng.")
    ba_t, tsum, base_roas = tier_summary(df, tol)
    st.write(f"ROAS chung là {vn(base_roas)}. Mỗi ad set được xếp hạng theo ROAS của nó so với mức này (chỉ xét ad set có ít nhất 10 chiến dịch).")
    st.dataframe(tsum.style.format({"% chi phí": "{:.1f}", "% doanh thu": "{:.1f}", "ROAS": "{:.2f}"}), width="stretch")
    st.dataframe(ba_t[["Hạng", "Số chiến dịch", "ROAS", "CPA"]].sort_values("ROAS", ascending=False)
                 .style.format({"ROAS": "{:.2f}", "CPA": "{:.2f}"}), width="stretch")

elif selected_menu == "⏱️ Xu Hướng Thời Gian":
    dd = df.dropna(subset=["date"])
    if not dd.empty:
        daily = summarize(dd, "date").reset_index()
        rule = alt.Chart(pd.DataFrame({"date": [pd.Timestamp("2024-05-05")]})).mark_rule(color="black", strokeDash=[4, 4]).encode(x="date:T")
        
        st.write("**Chi phí và doanh thu mỗi ngày:**")
        long = daily.melt("date", value_vars=["Tổng chi phí", "Tổng doanh thu"], var_name="Loại", value_name="Giá trị")
        top = alt.Chart(long).mark_bar().encode(
            x=alt.X("date:T", title="", axis=alt.Axis(format="%d/%m")), y=alt.Y("Giá trị:Q", title=""), xOffset="Loại:N",
            color=alt.Color("Loại:N", scale=alt.Scale(range=["#9aa5b1", "#0b6bcb"])),
            tooltip=["date:T", "Loại", alt.Tooltip("Giá trị:Q", format=",.0f")])
        st.altair_chart((top + rule).properties(height=260), width="stretch")

        st.write("**ROAS mỗi ngày:**")
        line = alt.Chart(daily).mark_line(point=True, color="#ee4d2d").encode(
            x=alt.X("date:T", title="", axis=alt.Axis(format="%d/%m")),
            y=alt.Y("ROAS:Q", scale=alt.Scale(domain=[0, 7])),
            tooltip=["date:T", alt.Tooltip("ROAS:Q", format=".2f")])
        st.altair_chart((line + rule).properties(height=200), width="stretch")
        st.caption("Đường nét đứt đánh dấu ngày sale 5/5. Trục ROAS bắt đầu từ 0 để không phóng đại dao động.")
        st.subheader("Trước / Ngày sale / Sau sale")
        if df["phase"].notna().any():
            st.dataframe(summarize(df.dropna(subset=["phase"]), "phase").style.format("{:,.2f}"), width="stretch")

elif selected_menu == "🎛️ Chuyển Ngân Sách What-If":
    st.subheader("Mô Phỏng Chuyển Ngân Sách Tối Ưu")
    st.caption("Giả định ROAS của mỗi nền tảng giữ nguyên khi đổi ngân sách. Thực tế tăng chi thường làm ROAS giảm, nên đây là ước lượng để tham khảo.")
    bp = summarize(df, "platform")
    plats = list(bp.index)
    a, b = st.columns(2)
    src = a.selectbox("Bớt ngân sách ở:", plats, index=plats.index("TikTok") if "TikTok" in plats else 0, key="side_whatif_src")
    others = [p for p in plats if p != src]
    dest = b.multiselect("Dồn sang:", others, default=[p for p in ["Facebook", "Shopee Ads"] if p in others] or others[:1], key="side_whatif_dest")
    pct = st.slider("Chuyển bao nhiêu % ngân sách nguồn:", 0, 30, 10, key="side_whatif_pct")
    if dest:
        ok = df.dropna(subset=["spend", "revenue"])
        sp = ok.groupby("platform")["spend"].sum()
        roas_dest = (bp.loc[dest, "ROAS"] * sp[dest]).sum() / sp[dest].sum()
        gain = (sp[src] * pct / 100) * (roas_dest - bp.loc[src, "ROAS"])
        m = st.columns(4)
        m[0].metric(f"ROAS của {src}", vn(bp.loc[src, "ROAS"]))
        m[1].metric("ROAS bình quân nơi nhận", vn(roas_dest))
        m[2].metric("Số tiền chuyển", vn(sp[src] * pct / 100, 0))
        m[3].metric("Doanh thu tăng thêm", vn(gain, 0), f"{gain / ok['revenue'].sum() * 100:+.2f}%")

elif selected_menu == "📄 Bảng Dữ Liệu Chi Tiết":
    log = ss.files[cur].get("log")
    if role == "admin":
        st.subheader("Nhật Ký Kiểm Toán Làm Sạch Dữ Liệu")
        if log:
            st.dataframe(pd.DataFrame(log, columns=["Hạng mục", "Kết quả"]), width="stretch", hide_index=True)
        else:
            st.write("File này đã được làm sạch sẵn từ notebook nên không có nhật ký tự động. Tải file gốc để xem nhật ký.")
    st.subheader("Bảng Dữ Liệu Sau Khi Lọc")
    st.dataframe(df.drop(columns=["adset_platform"], errors="ignore"), width="stretch", height=420)