import streamlit as st
import requests
import feedparser
from datetime import datetime
import pytz
import ssl
import urllib.request

st.set_page_config(page_title="Gold Tracker", layout="wide")

# Shift entire layout upward
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Constants
USD_TO_TWD_FALLBACK = 33.07
DISCOUNT_MIN = 0.49
DISCOUNT_MAX = 1.16
DISCOUNT_DEFAULT = 0.66

# Wrapped metric (custom metric with wrapping and styling)
def wrapped_metric(label, value, delta=None):
    st.markdown(f"""
    <div style="
        background-color: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 8px;
        color: white;
        font-size: 13px;
        line-height: 1.4;
        min-height: 78px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    ">
        <div style="font-size: 13px; font-weight: bold;">{label}</div>
        <div style="font-size: 15px;">{value}</div>
        {f'<div>{delta}</div>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)

# Exchange rate
def get_usd_to_twd():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "rates" in data and "TWD" in data["rates"]:
            return data["rates"]["TWD"]
    except:
        st.warning("⚠️ Using fallback exchange rate 33.07")
    return USD_TO_TWD_FALLBACK

# Gold price in USD/oz
def get_gold_price_usd_per_oz(api_key):
    url = "https://api.gold-api.com/price/XAU"
    headers = {
        "x-access-token": api_key,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if "price" in data:
            return data["price"]
        else:
            st.error("❌ Failed to fetch gold price.")
    except Exception as e:
        st.error(f"❌ Error fetching gold price: {e}")
    return 0

# Convert USD/oz → TWD/g
def convert_usd_oz_to_twd_gram(usd_per_oz, usd_to_twd):
    return (usd_per_oz * usd_to_twd) / 31.1035

# Calculate profit/loss
def calculate_profit(buy_price, weight, sell_price):
    absolute = (sell_price - buy_price) * weight
    percent = ((sell_price - buy_price) / buy_price) * 100
    return round(absolute, 2), round(percent, 2)

# Taiwan time
def get_taiwan_time():
    taipei = pytz.timezone("Asia/Taipei")
    return datetime.now(taipei).strftime("%Y-%m-%d %H:%M:%S")

# Layout
col1, col2, col3 = st.columns([1.7, 1.5, 1])

# ----- Column 1: Input + Results -----
with col1:
    st.markdown("<h4 style='margin-bottom: 0;'>💰 Gold Price Tracker</h4><hr style='margin-top: 6px;'>", unsafe_allow_html=True)

    api_key = "YOUR_GOLD_API_KEY_HERE"
    buy_price = st.number_input("💵 Your Buy Price (TWD per gram)", value=3254.0)
    weight = st.number_input("⚖️ Weight (grams)", value=308.0)
    discount_percent = st.slider("📉 Choose Bank Buy Discount (%)",
                                 min_value=DISCOUNT_MIN,
                                 max_value=DISCOUNT_MAX,
                                 value=DISCOUNT_DEFAULT,
                                 step=0.01)

    if "usd_per_oz" not in st.session_state:
        st.session_state.usd_per_oz = 0
    if "usd_to_twd" not in st.session_state:
        st.session_state.usd_to_twd = USD_TO_TWD_FALLBACK

    if st.button("📈 Show Profit / Loss"):
        st.session_state.usd_per_oz = get_gold_price_usd_per_oz(api_key)
        st.session_state.usd_to_twd = get_usd_to_twd()
        st.session_state.timestamp = get_taiwan_time()

    if st.session_state.usd_per_oz > 0:
        usd_oz = st.session_state.usd_per_oz
        twd_rate = st.session_state.usd_to_twd
        spot_price = convert_usd_oz_to_twd_gram(usd_oz, twd_rate)
        simulated_sell_price = spot_price * (1 - discount_percent / 100)
        total_value = round(simulated_sell_price * weight, 2)
        original_value = round(buy_price * weight, 2)
        profit, percent = calculate_profit(buy_price, weight, simulated_sell_price)

        min_sell = spot_price * (1 - DISCOUNT_MAX / 100)
        max_sell = spot_price * (1 - DISCOUNT_MIN / 100)
        min_total = round(min_sell * weight, 2)
        max_total = round(max_sell * weight, 2)
        min_profit, _ = calculate_profit(buy_price, weight, min_sell)
        max_profit, _ = calculate_profit(buy_price, weight, max_sell)

        st.markdown(f"🕒 Last Updated (Taiwan Time): **{st.session_state.timestamp}**")

        wrapped_metric("📍 Spot Price (USD/oz)", f"{usd_oz:.2f}")
        wrapped_metric("📍 Spot Price (TWD/g)", f"{spot_price:.2f}")
        wrapped_metric("🧮 Discount Used", f"{discount_percent:.2f}%")

        col4, col5 = st.columns(2)
        with col4:
            wrapped_metric("🟢 Simulated Sell Price", f"{simulated_sell_price:.2f} TWD/g")
        with col5:
            wrapped_metric("🟢 Sell Price Range", f"[{min_sell:.2f} TWD/g] ~ [{max_sell:.2f} TWD/g]")

        col6, col7 = st.columns(2)
        with col6:
            arrow = "▲" if percent > 0 else "🔻"
            color = "lightgreen" if percent > 0 else "salmon"
            delta_text = f"<span style='color:{color};'>{arrow} {percent:.2f}%</span>"
            wrapped_metric("📈 Profit / Loss", f"{profit:,.2f} TWD", delta_text)
        with col7:
            wrapped_metric("📈 Profit Range", f"[{min_profit:,.2f} TWD] ~ [{max_profit:,.2f} TWD]")

        col8, col9 = st.columns(2)
        with col8:
            wrapped_metric("💰 Total Market Value", f"{total_value:,.2f} TWD")
        with col9:
            wrapped_metric("💰 Value Range", f"[{min_total:,.2f} TWD] ~ [{max_total:,.2f} TWD]")

        wrapped_metric("💼 Original Investment", f"{original_value:,.2f} TWD")

        decision = "Decision: Hold" if total_value < original_value else "Decision: Consider Sell"
        bg_color = "#b00020" if decision == "Decision: Hold" else "#006400"

        st.markdown(f"""
        <div style="
            background-color: {bg_color};
            border-radius: 10px;
            padding: 14px;
            margin-top: 10px;
            color: white;
            font-size: 16px;
            text-align: center;
            font-weight: bold;
        ">
            {decision}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Click '📈 Show Profit / Loss' to fetch the latest gold and FX prices.")

# ----- Column 2: Chart -----
with col2:
    st.markdown("<h4 style='margin-bottom: 0;'>📊 Live Gold Price Chart</h4><hr style='margin-top: 6px;'>", unsafe_allow_html=True)

    chart_height = 1020 if st.session_state.usd_per_oz > 0 else 420

    st.components.v1.html(f"""
        <div style="
            position: relative;
            height: {chart_height + 40}px;
            width: 100%;
            border: 2px solid white;
            border-radius: 12px;
            overflow: hidden;
            background-color: white;  /* Clean white background */
        ">
            <div id="embed" style="
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: calc(100% - 40px);  /* More room at the bottom */
            "></div>
        </div>

        <script type="text/javascript" src="https://www.bullionvault.com/chart/bullionvaultchart.js"></script>
        <script type="text/javascript">
            var options = {{
                bullion: 'gold',
                currency: 'USD',
                timeframe: '1w',
                chartType: 'line',
                miniChartMode: false,
                miniChartModeAxis: 'oz',
                containerDefinedSize: true,
                displayLatestPriceLine: true,
                switchBullion: true,
                switchCurrency: true,
                switchTimeframe: true,
                switchChartType: true,
                exportButton: false
            }};
            var chartBV = new BullionVaultChart(options, 'embed');
        </script>
    """, height=chart_height + 45)

# ----- Column 3: News -----
with col3:
    st.markdown("<h4 style='margin-bottom: 0;'>📰 Gold News</h4><hr style='margin-top: 6px;'>", unsafe_allow_html=True)

    rss_url = "https://rss.app/feeds/tGMxva9Hvwh5AyAx.xml"

    try:
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(rss_url, context=context) as response:
            raw_data = response.read()
        feed = feedparser.parse(raw_data)

        if not feed.entries:
            st.warning("⚠️ No news available.")
        else:
            shown = 0
            for entry in feed.entries:
                if shown >= 13:
                    break

                title = entry.get("title", "No title")
                link = entry.get("link", "#")
                pub_date = entry.get("published", "No date")
                image_url = ""

                # Get the image URL if available
                if "media_content" in entry and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get("url", "")

                # Skip if image_url is missing or unreachable
                if not image_url:
                    continue

                try:
                    img_check = requests.head(image_url, timeout=5)
                    if img_check.status_code != 200:
                        continue  # Broken image
                except:
                    continue  # Error checking image

                # Render the news block
                st.markdown(
                    f"""
                    <div style="display: flex; margin-bottom: 15px;">
                        <div style="flex-shrink: 0;">
                            <a href="{link}" target="_blank">
                                <img src="{image_url}" alt="news image" width="100" style="border-radius: 6px; object-fit: cover;" />
                            </a>
                        </div>
                        <div style="margin-left: 12px;">
                            <a href="{link}" target="_blank" style="text-decoration: none;">
                                <div style="font-size: 15px; font-weight: 600; color: white;">{title}</div>
                            </a>
                            <div style="font-size: 12px; color: lightgray;">🗓️ {pub_date}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                shown += 1

            if shown == 0:
                st.warning("⚠️ No news with valid thumbnails found.")
    except Exception as e:
        st.error(f"❌ Failed to fetch news feed: {e}")
