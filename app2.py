"""
OmniMarket AI - Hệ thống Hợp nhất với Menu Danh mục bên trái (Sidebar Navigation)
Chạy ứng dụng:
    py -m streamlit run app2_2.py
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
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "director": {"password": "123", "name": "Nguyễn Giám Đốc", "role": "director", "label": "Giám Đốc (CEO / CMO)"},
        "user": {"password": "123", "name": "Trần Media Buyer", "role": "user", "label": "Chuyên Viên (Media Buyer)"},
        "admin": {"password": "123", "name": "Lê Quản Trị Viên", "role": "admin", "label": "Quản Trị Hệ Thống (Admin)"},
    }

if "proposals" not in st.session_state:
    st.session_state.proposals = [
        {
            "id": "PRJ-01",
            "title": "Tăng ngân sách Product Boost Shopee Sale 6.6",
            "creator": "Trần Media Buyer",
            "platform": "Shopee Ads",
            "budget": 25000000.0,
            "expected_revenue": 160000000.0,
            "reason": "Dựa trên số liệu đợt 5.5, Product Boost đạt ROAS 6.77x và CPA thấp nhất toàn sàn.",
            "status": "Chờ duyệt",
            "feedback": "",
            "date": "2026-05-15",
        },
        {
            "id": "PRJ-02",
            "title": "Cắt giảm Live Ads TikTok chuyển sang Lookalike Facebook",
            "creator": "Trần Media Buyer",
            "platform": "Facebook",
            "budget": 40000000.0,
            "expected_revenue": 240000000.0,
            "reason": "Mô hình What-If cho thấy chuyển dịch 10% ngân sách TikTok sang Facebook tăng 1.0% doanh thu thuần.",
            "status": "Đã duyệt",
            "feedback": "Đồng ý phân bổ đợt 1.",
            "date": "2026-05-12",
        },
    ]

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "Xin chào! Tôi là Cố vấn Tiếp thị AI. Bạn đang muốn tìm cách hạ CPA hay chuẩn bị số liệu lập đề xuất dự án trình Giám đốc?"}
    ]

if "user_info" not in st.session_state:
    st.session_state.user_info = None

if "target_roas" not in st.session_state:
    st.session_state.target_roas = 4.5
if "target_cpa" not in st.session_state:
    st.session_state.target_cpa = 25.0

if "proposal_notice" not in st.session_state:
    st.session_state.proposal_notice = None

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

def fallback_clean(df_raw):
    df = df_raw.copy()
    col_map = {c: str(c).strip().lower() for c in df.columns}
    df.rename(columns=col_map, inplace=True)
    log = []
    
    PLAT_MAP = {
        'facebook': 'Facebook', 'facebookads': 'Facebook', 'fb': 'Facebook',
        'tiktok': 'TikTok', 'tiktokads': 'TikTok', 'ttads': 'TikTok',
        'google': 'Google', 'googleads': 'Google', 'gg': 'Google',
        'instagram': 'Instagram', 'instagramads': 'Instagram', 'ig': 'Instagram', 'insta': 'Instagram',
        'shopee': 'Shopee Ads', 'shopeeads': 'Shopee Ads', 'spads': 'Shopee Ads'
    }
    if 'platform' in df.columns:
        df['platform'] = df['platform'].astype(str).str.lower().str.replace(r'[^a-z]', '', regex=True).map(PLAT_MAP).fillna('Khác')
        log.append(('Nền tảng', f"Chuẩn hóa về {df['platform'].nunique()} nền tảng chuẩn"))

    for c in ['spend', 'clicks', 'impressions', 'revenue']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce')
    if 'conversions' in df.columns:
        df['conversions'] = pd.to_numeric(df['conversions'], errors='coerce')

    if 'spend' in df.columns:
        df['spend'] = df['spend'].abs()
        df.loc[df['spend'] == 0, 'spend'] = np.nan
    if 'clicks' in df.columns and 'impressions' in df.columns:
        df.loc[df['clicks'] > df['impressions'], 'impressions'] = np.nan

    def get_group(a):
        a = str(a)
        if 'Retargeting' in a: return 'Retargeting'
        if a.startswith('Lookalike') or a == 'Prospecting': return 'Lookalike / Prospecting'
        if a.startswith('Search') or a == 'Keyword Auto': return 'Search'
        if any(x in a for x in ['Shopping', 'PMAX', 'Catalog Sales', 'Shop Ads', 'Product Boost', 'GMV Max']): return 'Shopping / Catalog'
        if any(x in a for x in ['Video View', 'Stories', 'Reels', 'Live Ads', 'Discovery']): return 'Video / Content'
        if any(x in a for x in ['Influencer', 'Creator Post']): return 'Influencer / Creator'
        return 'Khác'

    df['ad_set_group'] = df['ad_set'].apply(get_group)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['ROAS'] = df['revenue'] / df['spend']
    df['day_type'] = np.where(df['date'].dt.dayofweek >= 5, 'Cuối tuần', 'Ngày thường')
    
    def get_phase(d):
        if pd.isna(d): return np.nan
        if d < pd.Timestamp('2024-05-05'): return '1. Trước sale (28/4-4/5)'
        if d == pd.Timestamp('2024-05-05'): return '2. Ngày sale (5/5)'
        return '3. Sau sale (6/5-10/5)'
    df['phase'] = df['date'].apply(get_phase)
    return df, log

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
        if HAS_LOCAL_CLEANING:
            missing = [c for c in RAW_COLS if c not in head.columns]
            if missing:
                df, log = fallback_clean(head)
            else:
                df, log = clean_raw(head)
        else:
            df, log = fallback_clean(head)
            
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
                users = st.session_state.users_db
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
        "🎛️ Chuyển Ngân Sách What-If",
        "📄 Bảng Dữ Liệu Chi Tiết",
    ]
    
    # Bổ sung danh mục theo quyền (có đếm số lượng trực quan)
    if role == "director":
        pending_n = sum(1 for p in st.session_state.proposals if p["status"] == "Chờ duyệt")
        menu_approve = f"📑 Phê Duyệt & Cấp Ngân Sách ({pending_n} chờ)"
        nav_options.insert(1, menu_approve)
        nav_options.insert(2, "💼 Khuyến Nghị Phân Bổ 70/20/10")
    elif role == "user":
        my_count = sum(1 for p in st.session_state.proposals if p.get("creator") == user["name"])
        menu_my_props = f"📋 Đề Xuất Của Tôi ({my_count})"
        nav_options.insert(1, menu_my_props)
        nav_options.insert(2, "➕ Tạo Đề Xuất Dự Án Mới")
        nav_options.insert(3, "💬 Cố Vấn Tiếp Thị AI")
    elif role == "admin":
        nav_options.insert(1, "👥 Phân Quyền & Quản Lý Tài Khoản")
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
    net_profit = tot_rev - tot_spend

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Tổng Chi Phí", vn(tot_spend, 0))
    col2.metric("Tổng Doanh Thu", vn(tot_rev, 0))
    col3.metric("Lợi Nhuận Gộp", vn(net_profit, 0))
    col4.metric("ROAS Toàn Sàn", f"{vn(roas)}x")
    col5.metric("CPA Trung Bình", vn(cpa))

    st.markdown("---")
    st.subheader("Chi Phí & Doanh Thu: Kênh Nào Chiếm Bao Nhiêu?")
    both = df.dropna(subset=["spend", "revenue"]).groupby("platform")[["spend", "revenue"]].sum()
    share = (both / both.sum() * 100).rename(columns={"spend": "Chi phí", "revenue": "Doanh thu"}).reset_index()
    sh = share.melt("platform", var_name="Loại", value_name="Tỉ trọng (%)")
    base = alt.Chart(sh).encode(x=alt.X("platform:N", title="Kênh quảng cáo"), xOffset="Loại:N")
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        y=alt.Y("Tỉ trọng (%):Q", title="Tỉ trọng đóng góp (%)"),
        color=alt.Color("Loại:N", scale=alt.Scale(range=["#ef4444", "#3b82f6"]))
    )
    lab = base.mark_text(dy=-7, fontSize=11).encode(y="Tỉ trọng (%):Q", text=alt.Text("Tỉ trọng (%):Q", format=".1f"))
    st.altair_chart((bars + lab).properties(height=340), use_container_width=True)

# =========================================================
# CHỨC NĂNG: GIÁM ĐỐC - PHÊ DUYỆT DỰ ÁN
# =========================================================
elif selected_menu.startswith("📑 Phê Duyệt & Cấp Ngân Sách"):
    proposals = st.session_state.proposals
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
                feedback_text = b_comm.text_input("Ghi chú phê duyệt", key=f"f_dir_{idx}_{p['id']}", placeholder="Ý kiến chỉ đạo cấp vốn...")
                if b1.button("✅ Phê Duyệt & Cấp Vốn", key=f"app_dir_{idx}_{p['id']}", type="primary", use_container_width=True):
                    st.session_state.proposals[idx]["status"] = "Đã duyệt"
                    st.session_state.proposals[idx]["feedback"] = feedback_text if feedback_text else "Đồng ý cấp vốn triển khai."
                    st.toast(f"Đã phê duyệt dự án [{p['id']}]!", icon="✅")
                    st.rerun()
                if b2.button("❌ Từ Chối", key=f"rej_dir_{idx}_{p['id']}", use_container_width=True):
                    st.session_state.proposals[idx]["status"] = "Từ chối"
                    st.session_state.proposals[idx]["feedback"] = feedback_text if feedback_text else "Cần tối ưu lại CPA."
                    st.toast(f"Đã từ chối dự án [{p['id']}]!", icon="❌")
                    st.rerun()

elif selected_menu == "💼 Khuyến Nghị Phân Bổ 70/20/10":
    st.subheader("Khung Chiến Lược Phân Bổ Ngân Sách 70/20/10")
    st.markdown("""
    - **70% Ngân sách Trụ cột (Core Performance):** Dồn vào **Facebook** (Prospecting Lookalike) và **Shopee Ads** (Product Boost, Keyword Auto) có ROAS > 5.7x, CPA an toàn dưới 20.0.
    - **20% Ngân sách Mở rộng (Growth):** Tối ưu lại **Google Search** bằng cách chặn từ khóa đắt đỏ để hạ CPC (đang ở mức 1.87), giữ chân khách hàng có CVR 7.0%.
    - **10% Ngân sách Thử nghiệm (Experimentation):** Thu hẹp ngân sách video/livestream của **TikTok** (chỉ giữ nhóm có ROAS dương), chuyển sang xây dựng thương hiệu.
    """)

# =========================================================
# CHỨC NĂNG: USER - ĐỀ XUẤT CỦA TÔI / TẠO DỰ ÁN / CHAT AI
# =========================================================
elif selected_menu.startswith("📋 Đề Xuất Của Tôi"):
    st.subheader("Danh Sách Dự Án Do Bạn Đề Xuất")
    my_proposals = [p for p in st.session_state.proposals if p.get("creator") == user["name"]]

    if not my_proposals:
        st.info("💡 Bạn chưa có đề xuất nào. Hãy chọn mục **'➕ Tạo Đề Xuất Dự Án Mới'** ở danh mục bên trái để gửi dự án lên Giám đốc.")
    else:
        for idx, p in enumerate(my_proposals):
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
                    if st.button("🗑️ Xóa Đề Xuất", key=f"del_side_{idx}_{p['id']}", use_container_width=True):
                        st.session_state.proposals = [item for item in st.session_state.proposals if item is not p]
                        st.toast(f"Đã xóa đề xuất [{p['id']}]!", icon="🗑️")
                        st.rerun()

elif selected_menu == "➕ Tạo Đề Xuất Dự Án Mới":
    st.subheader("Soạn Thảo Đề Xuất Dự Án Trình Giám Đốc")

    # Hiển thị thông báo thành công nếu vừa gửi xong ở lượt chạy trước
    if st.session_state.get("proposal_notice"):
        st.success(st.session_state.proposal_notice)
        st.toast(st.session_state.proposal_notice, icon="🎉")
        st.session_state.proposal_notice = None

    with st.form("create_proposal_form_side", clear_on_submit=True):
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
            if not p_title.strip() or not p_reason.strip():
                st.error("⚠️ Vui lòng điền đủ tiêu đề và luận cứ dự án!")
            else:
                # Sinh mã PRJ-XX không trùng lặp ngay cả khi đã xóa đề xuất cũ
                existing_nums = [
                    int(item["id"].split("-")[1])
                    for item in st.session_state.proposals
                    if item["id"].startswith("PRJ-") and len(item["id"].split("-")) > 1 and item["id"].split("-")[1].isdigit()
                ]
                next_num = max(existing_nums, default=0) + 1
                new_id = f"PRJ-{next_num:02d}"

                new_proposal = {
                    "id": new_id,
                    "title": p_title.strip(),
                    "creator": user["name"],
                    "platform": p_platform,
                    "budget": p_budget,
                    "expected_revenue": p_rev,
                    "reason": p_reason.strip(),
                    "status": "Chờ duyệt",
                    "feedback": "",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
                st.session_state.proposals.insert(0, new_proposal)
                st.session_state.proposal_notice = f"✅ Đã gửi đề xuất [{new_id}] thành công tới Giám đốc! Hãy bấm qua mục 'Đề Xuất Của Tôi' ở thanh bên để theo dõi."
                st.rerun()

elif selected_menu == "💬 Cố Vấn Tiếp Thị AI":
    st.subheader("Trò Chuyện Trực Tiếp với Cố Vấn Marketing AI")
    st.caption("Truy vấn trực tiếp số liệu từ tập dữ liệu chiến dịch để chuẩn bị luận cứ thuyết phục Giám đốc.")

    chat_box = st.container(height=380, border=True)
    for msg in st.session_state.chat_messages:
        with chat_box.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Hỏi AI về chiến dịch hoặc cách tối ưu CPA..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        p_lower = prompt.lower()
        if "roas" in p_lower or "hiệu quả" in p_lower:
            best_plat = df.groupby("platform").apply(lambda g: g["revenue"].sum() / g["spend"].sum()).idxmax()
            answer = f"Theo dữ liệu hiện tại, kênh có ROAS tốt nhất là **{best_plat}**. Bạn nên đề xuất tăng ngân sách vào nhóm **Product Boost** và **Prospecting Lookalike**, vì đây là các nhóm mang lại biên lợi nhuận cao nhất."
        elif "tiktok" in p_lower or "giảm" in p_lower:
            answer = "Kênh TikTok đang chiếm tỷ trọng chi phí cao nhưng CPA bị đẩy lên cao (~27.9 đ) và ROAS thấp (~4.25x). Bạn nên đề xuất cắt bớt ngân sách nhóm Video View/Live Ads của TikTok để điều chuyển sang Shopee Ads hoặc Facebook."
        elif "cpa" in p_lower or "chi phí" in p_lower:
            answer = "Shopee Ads hiện có CPA trung bình thấp nhất (khoảng 18.6 đ). Nếu muốn hạ CPA toàn chiến dịch, bạn nên tập trung đề xuất tăng các nhóm Keyword Auto và Product Boost."
        else:
            answer = f"Dựa trên dữ liệu hiện tại: Doanh thu trung bình toàn chiến dịch đạt ROAS ~{ratio(df, 'revenue', 'spend'):.2f}x. Bạn có thể chọn mục **'Tạo Đề Xuất Dự Án Mới'** ở danh mục bên trái để trình kế hoạch này."
        
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        st.rerun()

# =========================================================
# CHỨC NĂNG: ADMIN - PHÂN QUYỀN / KHẢO SÁT / CẤU HÌNH
# =========================================================
elif selected_menu == "👥 Phân Quyền & Quản Lý Tài Khoản":
    st.subheader("Danh Sách Tài Khoản Phân Quyền & Quản Lý Truy Cập")

    # Xác định username hiện tại đang đăng nhập để khóa nút tự xóa chính mình
    current_username = next(
        (u for u, d in st.session_state.users_db.items() if d["name"] == user["name"]),
        None,
    )

    for u_key, u_data in list(st.session_state.users_db.items()):
        with st.container(border=True):
            col_u_info, col_u_role, col_u_action = st.columns([3, 2, 1.2])
            
            with col_u_info:
                st.markdown(f"**{u_data['name']}** (`@{u_key}`)")
                st.caption(f"Mã vai trò: `{u_data['role']}`")
            
            with col_u_role:
                st.markdown(
                    f'<span class="badge-status status-approved" style="margin-top:6px;">{u_data["label"]}</span>',
                    unsafe_allow_html=True,
                )
            
            with col_u_action:
                is_protected = (u_key == "admin") or (u_key == current_username)
                if is_protected:
                    st.button(
                        "🔒 Mặc định",
                        key=f"lock_side_user_{u_key}",
                        disabled=True,
                        use_container_width=True,
                        help="Không thể xóa tài khoản Admin gốc hoặc tài khoản đang đăng nhập.",
                    )
                else:
                    if st.button(
                        "🚫 Kick / Xóa",
                        key=f"kick_side_user_{u_key}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        del st.session_state.users_db[u_key]
                        st.toast(f"Đã thu hồi quyền và xóa tài khoản '{u_key}'!", icon="🚫")
                        st.rerun()

    st.divider()
    st.subheader("➕ Cấp Mới Tài Khoản & Gán Quyền")
    with st.form("add_user_form_side", clear_on_submit=True):
        u1, u2 = st.columns(2)
        new_u = u1.text_input("Tên đăng nhập", placeholder="vd: analyst_lead")
        new_p = u2.text_input("Mật khẩu", type="password", value="123")

        u3, u4 = st.columns(2)
        new_name = u3.text_input("Họ và tên đầy đủ", placeholder="Phạm Văn B")
        new_r = u4.selectbox("Vai trò cấp quyền", ["user", "director", "admin"],
                             format_func=lambda x: {"director": "Giám Đốc (Phê duyệt)", "user": "Nhân viên (Tác nghiệp)", "admin": "Quản trị viên"}[x])

        if st.form_submit_button("Tạo Tài Khoản", type="primary"):
            clean_u = new_u.strip().lower()
            if not clean_u or not new_name.strip():
                st.error("Vui lòng điền đủ tên tài khoản và họ tên!")
            elif clean_u in st.session_state.users_db:
                st.error("Tài khoản này đã tồn tại!")
            else:
                r_labels = {"director": "Giám Đốc (CEO / CMO)", "user": "Nhân viên (Media Buyer)", "admin": "Quản trị hệ thống (Admin)"}
                st.session_state.users_db[clean_u] = {
                    "password": new_p,
                    "name": new_name.strip(),
                    "role": new_r,
                    "label": r_labels[new_r],
                }
                st.toast(f"Đã tạo tài khoản '{clean_u}' thành công!", icon="✅")
                st.rerun()

elif selected_menu == "🚀 Khảo Sát Nâng Cấp Hệ Thống":
    st.subheader("Báo Cáo Sức Khỏe & Khảo Sát Nâng Cấp Hệ Thống")
    c1, c2, c3 = st.columns(3)
    c1.metric("Phiên bản", "v4.0.0 Enterprise")
    c2.metric("Tài khoản vận hành", len(st.session_state.users_db))
    c3.metric("Hồ sơ dự án", len(st.session_state.proposals))

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
            st.toast("Đã ghi nhận khảo sát!", icon="🚀")

elif selected_menu == "⚙️ Cài Đặt Ngưỡng Cảnh Báo KPI":
    st.subheader("Thiết Lập Ngưỡng Cảnh Báo KPI")
    with st.form("kpi_config_form_side"):
        t_roas = st.number_input("ROAS Sàn kỳ vọng", min_value=1.0, max_value=20.0, value=float(st.session_state.target_roas), step=0.1)
        t_cpa = st.number_input("CPA Trần tối đa (VNĐ)", min_value=5.0, max_value=200.0, value=float(st.session_state.target_cpa), step=1.0)
        if st.form_submit_button("Lưu Thiết Lập", type="primary"):
            st.session_state.target_roas = t_roas
            st.session_state.target_cpa = t_cpa
            st.success("Đã cập nhật ngưỡng cảnh báo KPI!")
            st.toast("Đã lưu thiết lập KPI!", icon="⚙️")

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

elif selected_menu == "⏱️ Xu Hướng Thời Gian":
    dd = df.dropna(subset=["date"])
    if not dd.empty:
        daily = summarize(dd, "date").reset_index()
        daily["ROAS"] = daily["Tổng doanh thu"] / daily["Tổng chi phí"]
        
        st.write("**Chi phí và doanh thu mỗi ngày:**")
        long = daily.melt("date", value_vars=["Tổng chi phí", "Tổng doanh thu"], var_name="Loại", value_name="Giá trị")
        top = alt.Chart(long).mark_bar().encode(
            x=alt.X("date:T", title="", axis=alt.Axis(format="%d/%m")), y=alt.Y("Giá trị:Q", title=""), xOffset="Loại:N",
            color=alt.Color("Loại:N", scale=alt.Scale(range=["#9aa5b1", "#0b6bcb"])),
            tooltip=["date:T", "Loại", alt.Tooltip("Giá trị:Q", format=",.0f")])
        st.altair_chart(top.properties(height=260), width="stretch")

        st.write("**ROAS mỗi ngày:**")
        line = alt.Chart(daily).mark_line(point=True, color="#ee4d2d").encode(
            x=alt.X("date:T", title="", axis=alt.Axis(format="%d/%m")),
            y=alt.Y("ROAS:Q", scale=alt.Scale(domain=[0, 7])),
            tooltip=["date:T", alt.Tooltip("ROAS:Q", format=".2f")])
        st.altair_chart(line.properties(height=200), width="stretch")

elif selected_menu == "🎛️ Chuyển Ngân Sách What-If":
    st.subheader("Mô Phỏng Chuyển Ngân Sách Tối Ưu")
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
    if log:
        st.subheader("Nhật Ký Kiểm Toán Làm Sạch Dữ Liệu")
        st.dataframe(pd.DataFrame(log, columns=["Hạng mục", "Kết quả"]), width="stretch", hide_index=True)
    st.subheader("Bảng Dữ Liệu Sau Khi Lọc")
    st.dataframe(df.drop(columns=["adset_platform"], errors="ignore"), width="stretch", height=420)