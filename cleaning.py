"""
Làm sạch file dữ liệu quảng cáo gốc.
Cùng logic với notebook Shopee_5_5_Marketing_Analytics.ipynb, để dashboard có thể
tự làm sạch khi người dùng tải thẳng file gốc lên.
"""
import re

import numpy as np
import pandas as pd

# cột bắt buộc phải có trong file gốc (campaign_id là tùy chọn)
RAW_COLS = ["campaign_name", "platform", "ad_set", "spend", "clicks", "impressions",
            "conversions", "revenue", "date"]
NUM_COLS = ["spend", "clicks", "impressions", "revenue"]
SALE_DAY = pd.Timestamp("2024-05-05")

PLATFORM_MAP = {
    "facebook": "Facebook", "facebookads": "Facebook", "fb": "Facebook",
    "tiktok": "TikTok", "tiktokads": "TikTok", "ttads": "TikTok",
    "google": "Google", "googleads": "Google", "gg": "Google",
    "instagram": "Instagram", "instagramads": "Instagram", "ig": "Instagram", "insta": "Instagram",
    "shopee": "Shopee Ads", "shopeeads": "Shopee Ads", "spads": "Shopee Ads",
}
WORDS = {"ten": 10, "one hundred": 100, "two thousand": 2000, "ten thousand": 10000}
VN_DAY = {"Monday": "Thứ 2", "Tuesday": "Thứ 3", "Wednesday": "Thứ 4", "Thursday": "Thứ 5",
          "Friday": "Thứ 6", "Saturday": "Thứ 7", "Sunday": "Chủ nhật"}
DATE_PATTERNS = [
    (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"), (r"\d{4}/\d{2}/\d{2}", "%Y/%m/%d"),
    (r"\d{4}\.\d{2}\.\d{2}", "%Y.%m.%d"), (r"\d{1,2}-[A-Za-z]{3}-\d{4}", "%d-%b-%Y"),
    (r"[A-Za-z]{3} \d{1,2} \d{4}", "%b %d %Y"),
    (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y"),     # có dấu "/" là ngày/tháng/năm
    (r"\d{2}-\d{2}-\d{4}", "%m-%d-%Y"),     # có dấu "-" và 2 số đầu là tháng-ngày-năm
]
SHOPPING = {"Shopping", "PMAX", "Catalog Sales", "Shop Ads", "Product Boost", "GMV Max"}
VIDEO = {"Video View", "Stories", "Reels", "Live Ads", "Discovery"}


def parse_num(x):
    """'1,035' '1601$' '850usd' '1726đ' '1.2k' '1,8k' '1 210' '1029,00' '1O0' 'ten thousand' -> số."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    if s in WORDS:
        return float(WORDS[s])
    s = re.sub(r"(usd|\$|đ|vnd)", "", s).strip()
    s = re.sub(r"(?<=\d)o|o(?=\d)", "0", s)          # chữ O nằm cạnh số -> số 0
    s = s.replace(" ", "")
    mult = 1
    if s.endswith("k"):                               # 1,8k = 1800
        mult, s = 1000, s[:-1].replace(",", ".")
    elif re.fullmatch(r"-?\d+,\d{2}", s):             # 1029,00 = thập phân kiểu châu Âu
        s = s.replace(",", ".")
    else:                                             # 1,035 = dấu phẩy hàng nghìn
        s = s.replace(",", "")
    try:
        return float(s) * mult
    except ValueError:
        return np.nan


def parse_date(x):
    s = str(x).strip()
    for pattern, fmt in DATE_PATTERNS:
        if re.fullmatch(pattern, s):
            return pd.to_datetime(s, format=fmt, errors="coerce")
    return pd.NaT


def ad_set_group(a):
    a = str(a)
    if "Retargeting" in a:
        return "Retargeting"
    if a.startswith("Lookalike") or a == "Prospecting":
        return "Lookalike / Prospecting"
    if a.startswith("Search") or a == "Keyword Auto":
        return "Search"
    if a in SHOPPING:
        return "Shopping / Catalog"
    if a in VIDEO:
        return "Video / Content"
    if a in {"Influencer", "Creator Post"}:
        return "Influencer / Creator"
    return "Khác"


def phase(d):
    if pd.isna(d):
        return np.nan
    if d < SALE_DAY:
        return "1. Trước sale (28/4–4/5)"
    if d == SALE_DAY:
        return "2. Ngày sale (5/5)"
    return "3. Sau sale (6/5–10/5)"


def n(x):
    return f"{int(x):,}".replace(",", ".")


def clean_raw(raw: pd.DataFrame):
    """Nhận bảng gốc (đọc dạng chữ), trả về (bảng đã làm sạch, báo cáo làm sạch)."""
    log = []
    df = raw.copy()
    dup = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)
    log.append(("Số dòng đọc được", n(len(raw))))
    if dup:
        log.append(("Dòng trùng lặp đã loại", n(dup)))

    # nền tảng: gom về tên chuẩn, tên lạ thì giữ nguyên
    orig = df["platform"].astype(str).str.strip()
    mapped = orig.str.lower().str.replace(r"[^a-z]", "", regex=True).map(PLATFORM_MAP)
    unknown = int((mapped.isna() & df["platform"].notna()).sum())
    df["platform"] = mapped.fillna(orig.where(df["platform"].notna()).str.title())
    log.append(("Tên nền tảng", f"{orig.nunique()} cách viết → {df['platform'].nunique()} nền tảng"))
    if unknown:
        log.append(("Tên nền tảng không nhận ra (giữ nguyên)", f"{n(unknown)} dòng"))

    cn = df["campaign_name"]
    df["campaign_name"] = cn.str.strip().str.title()
    log.append(("Tên chiến dịch", f"{cn.nunique()} cách viết → {df['campaign_name'].nunique()} tên"))

    # các cột số
    changed = lost = 0
    for c in NUM_COLS:
        s = df[c]
        plain = s.dropna().astype(str).str.fullmatch(r"-?\d+(\.\d+)?")
        parsed = s.map(parse_num)
        changed += int((~plain).sum())
        lost += int((s.notna() & parsed.isna()).sum())
        df[c] = parsed
    conv = pd.to_numeric(df["conversions"], errors="coerce")
    lost += int((df["conversions"].notna() & conv.isna()).sum())
    df["conversions"] = conv
    log.append(("Ô số lẫn ký tự đã chuyển về số (k, $, usd, đ, chữ O, số viết bằng chữ...)", n(changed)))
    if lost:
        log.append(("Ô không đọc được thành số (để trống)", n(lost)))

    # giá trị bất thường
    log.append(("Chi phí âm (đổi dấu)", f"{n((df['spend'] < 0).sum())} dòng"))
    df["spend"] = df["spend"].abs()
    log.append(("Chi phí bằng 0 (coi là thiếu)", f"{n((df['spend'] == 0).sum())} dòng"))
    df.loc[df["spend"] == 0, "spend"] = np.nan
    m = df["clicks"] > df["impressions"]
    log.append(("Click nhiều hơn lượt hiển thị (bỏ lượt hiển thị)", f"{n(m.sum())} dòng"))
    df.loc[m, "impressions"] = np.nan
    q1, q3 = df["conversions"].quantile([.25, .75])
    upper = q3 + 3 * (q3 - q1)
    m = (df["conversions"] > df["clicks"]) | (df["conversions"] > upper)
    log.append((f"Số đơn lớn hơn số click hoặc lớn hơn {upper:.0f} (bỏ số đơn)", f"{n(m.sum())} dòng"))
    df.loc[m, "conversions"] = np.nan

    # ngày: nhiều định dạng; ngày không tồn tại hoặc lệch quá xa so với phần còn lại thì để trống
    d = pd.to_datetime(df["date"].map(parse_date))
    med = d.dropna().median()
    if pd.notna(med):
        d = d.where((d - med).abs() <= pd.Timedelta(days=45))
    df["date"] = d
    log.append(("Ngày không hợp lệ (để trống)", f"{n(d.isna().sum())} dòng"))

    # chỉ số marketing và biến mới
    df["CTR"] = df["clicks"] / df["impressions"]
    df["CPC"] = df["spend"] / df["clicks"]
    df["CVR"] = df["conversions"] / df["clicks"]
    df["CPA"] = df["spend"] / df["conversions"]
    df["ROAS"] = df["revenue"] / df["spend"]
    df["ad_set_group"] = df["ad_set"].map(ad_set_group)
    df["AOV"] = df["revenue"] / df["conversions"]
    df["day_of_week"] = df["date"].dt.day_name().map(VN_DAY)
    df["day_type"] = np.where(df["date"].dt.dayofweek >= 5, "Cuối tuần", "Ngày thường")
    df.loc[df["date"].isna(), "day_type"] = np.nan
    df["days_from_start"] = (df["date"] - df["date"].min()).dt.days
    df["phase"] = df["date"].map(phase)
    try:
        df["spend_tier"] = pd.qcut(df["spend"], 3, labels=["Thấp", "Trung bình", "Cao"]).astype(object)
    except ValueError:
        df["spend_tier"] = np.nan

    miss = {c: int(df[c].isna().sum()) for c in ["spend", "clicks", "impressions", "conversions", "revenue"]}
    log.append(("Ô còn thiếu sau làm sạch", ", ".join(f"{k} {v}" for k, v in miss.items())))

    order = ["campaign_id", "campaign_name", "platform", "ad_set", "spend", "clicks", "impressions",
             "conversions", "revenue", "date", "CTR", "CPC", "CVR", "CPA", "ROAS", "ad_set_group",
             "AOV", "day_of_week", "day_type", "days_from_start", "phase", "spend_tier"]
    return df[[c for c in order if c in df.columns]], log
