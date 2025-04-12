import streamlit as st
import requests
import feedparser
from datetime import datetime
import pytz
import ssl
import urllib.request

# Convert GMT published time string to Taipei time
def convert_gmt_string_to_taipei(gmt_str):
    try:
        gmt_time = datetime.strptime(gmt_str, "%a, %d %b %Y %H:%M:%S %Z")
        gmt_time = pytz.timezone("GMT").localize(gmt_time)
        taipei_time = gmt_time.astimezone(pytz.timezone("Asia/Taipei"))
        return taipei_time.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return gmt_str  # fallback to original if format parsing fails

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
DISCOUNT_MIN = 0.12
DISCOUNT_MAX = 1.16
DISCOUNT_DEFAULT = 0.44

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

# Gold price in USD/oz (no API key required)
def get_gold_price_usd_per_oz():
    url = "https://api.gold-api.com/price/XAU"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            st.error(f"❌ API returned status code {response.status_code}")
            return 0
        data = response.json()
        if "price" in data:
            return data["price"]
        else:
            st.error("❌ 'price' field not found in API response.")
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
col1, col2, col3 = st.columns([1.4, 1.6, 1])

# ----- Column 1: Input + Results -----
with col1:
    st.markdown("<h4 style='margin-bottom: 0;'>💰 Gold Investment Tracker</h4><hr style='margin-top: 6px;'>", unsafe_allow_html=True)

    buy_price = st.number_input("💵 Your Buy Price (TWD per gram)", value=3254.0)
    weight = st.number_input("⚖️ Weight (grams)", value=308.0)
    discount_percent = st.slider("📉 Choose Bank Buy Discount (%)",
                                 min_value=DISCOUNT_MIN,
                                 max_value=DISCOUNT_MAX,
                                 value=DISCOUNT_DEFAULT,
                                 step=0.01)
    
    col_left, col_center, col_right = st.columns([1.5, 2, 1.5])
    with col_left:
        st.markdown("<span style='font-size: 12px; color: lightgray;'>Market Less Volatile</span>", unsafe_allow_html=True)
    with col_right:
        st.markdown("<span style='font-size: 12px; color: lightgray; float: right;'>Market More volatile</span>", unsafe_allow_html=True)

    # Initialize session state
    if "usd_per_oz" not in st.session_state:
        st.session_state.usd_per_oz = 0
    if "usd_to_twd" not in st.session_state:
        st.session_state.usd_to_twd = USD_TO_TWD_FALLBACK
    if "mode" not in st.session_state:
        st.session_state.mode = None

    # Buttons for live/manual input
    col_btn1, col_btn2 = st.columns([1, 1.2])

    with col_btn1:
        st.markdown("✍️ Spot Price (USD/oz, Live)", unsafe_allow_html=True)
        if st.button("📈 Show Profit / Loss (live)"):
            st.session_state.usd_per_oz = get_gold_price_usd_per_oz()
            st.session_state.usd_to_twd = get_usd_to_twd()
            st.session_state.timestamp = get_taiwan_time()
            st.session_state.mode = "live"

    with col_btn2:
        manual_input = st.number_input("✍️ Spot Price (USD/oz, Manual)", value= 3063.48, format="%.2f")
        if st.button("📝 Show Profit / Loss (manual input)"):
            st.session_state.usd_per_oz = manual_input
            st.session_state.usd_to_twd = get_usd_to_twd()
            st.session_state.timestamp = get_taiwan_time()
            st.session_state.mode = "manual"

    # Display results
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

        mode_label = "🛰️ Live" if st.session_state.mode == "live" else "✍️ Manual"
        st.markdown(f"🕒 Last Updated (Taiwan Time): **{st.session_state.timestamp}** &nbsp;&nbsp;&nbsp; 🔄 Conversion Rate: **1 USD = {st.session_state.usd_to_twd:.4f} TWD** &nbsp;&nbsp;&nbsp; 🧭 Mode: **{mode_label}**", unsafe_allow_html=True)

        col_spot1, col_spot2, col_spot3 = st.columns(3)
        with col_spot1:
            wrapped_metric("📍 Spot Price (USD/oz)", f"{usd_oz:.2f}")
        with col_spot2:
            wrapped_metric("📍 Spot Price (TWD/g)", f"{spot_price:.2f}")
        with col_spot3:
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
            padding: 56px; 
            margin-top: 10px;
            color: white;
            font-size: 26px;
            text-align: center;
            font-weight: bold;
        ">
            {decision}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Click a button above to fetch or manually input gold price and FX rate.")

# ----- Column 2: Chart -----
with col2:
    st.markdown("<h4 style='margin-bottom: 0;'>📊 Live Gold Price Chart</h4><hr style='margin-top: 6px;'>", unsafe_allow_html=True)

    chart_height = 420

    st.components.v1.html(f"""
        <div style="
            position: relative;
            height: {chart_height}px;
            width: 100%;
            border: 2px solid white;
            border-radius: 12px;
            overflow: hidden;
            background-color: #00aa00;
        ">
            <div id="embed" style="
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: calc(100% - 8px);
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
                miniChartModeAxis: 'both',
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
    """, height=chart_height)

    # --- Additional Macroeconomic Charts (2x4 grid) ---
    st.markdown("<h5 style='margin-top: 20px;'>📉 Key Macroeconomic Indicators</h5>", unsafe_allow_html=True)

    # First Row
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
    with row1_col1:
        st.markdown("**📊 Financial Stress Index**", unsafe_allow_html=True)
        st.components.v1.html("""
        <iframe src="https://www.tradingview.com/embed-widget/mini-symbol-overview/?symbol=FRED%3ASTLFSI2&locale=en" 
            width="100%" height="220" frameborder="0" allowtransparency="true" scrolling="no">
        </iframe>
        """, height=240)
        
    with row1_col2:
        st.markdown("**📊 US 10-Year Treasury Yield**", unsafe_allow_html=True)
        st.components.v1.html("""
        <iframe src="https://www.tradingview.com/embed-widget/mini-symbol-overview/?symbol=FRED%3ADGS10&locale=en" 
            width="100%" height="220" frameborder="0" allowtransparency="true" scrolling="no">
        </iframe>
        """, height=240)
    
    with row1_col3:
        st.markdown("**🛢️ Crude Oil**", unsafe_allow_html=True)
        st.components.v1.html("""
        <iframe src="https://www.tradingview.com/embed-widget/mini-symbol-overview/?symbol=TVC%3AUSOIL&locale=en" 
            width="100%" height="220" frameborder="0" allowtransparency="true" scrolling="no">
        </iframe>
        """, height=240)
    
    with row1_col4:
        st.markdown("**🏦 M2 Money Supply**", unsafe_allow_html=True)
        st.components.v1.html("""
        <iframe src="https://www.tradingview.com/embed-widget/mini-symbol-overview/?symbol=FRED%3AM2SL&locale=en" 
            width="100%" height="220" frameborder="0" allowtransparency="true" scrolling="no"></iframe>
        """, height=240)


    # Second Row
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
    with row2_col1:
        st.markdown("**🔥 US Consumer Price Index**", unsafe_allow_html=True)
        st.components.v1.html("""
        <iframe src="https://www.tradingview.com/embed-widget/mini-symbol-overview/?symbol=FRED%3ACPIAUCSL&locale=en" 
            width="100%" height="220" frameborder="0" allowtransparency="true" scrolling="no">
        </iframe>
        """, height=240)

    with row2_col2:
        st.markdown("**💵 U.S. Dollar Index**", unsafe_allow_html=True)
        st.components.v1.html("""
        <iframe src="https://www.tradingview.com/embed-widget/mini-symbol-overview/?symbol=FRED%3ADTWEXBGS&locale=en" 
            width="100%" height="220" frameborder="0" allowtransparency="true" scrolling="no">
        </iframe>
        """, height=240)
    
    with row2_col3:
        st.markdown("**🪙 Bitcoin / USD**", unsafe_allow_html=True)
        st.components.v1.html("""
        <iframe src="https://www.tradingview.com/embed-widget/mini-symbol-overview/?symbol=BINANCE%3ABTCUSDT&locale=en" 
            width="100%" height="220" frameborder="0" allowtransparency="true" scrolling="no">
        </iframe>
        """, height=240)
    
    with row2_col4:
        st.markdown("**⚖️ Gold/Silver Ratio**", unsafe_allow_html=True)
        st.components.v1.html("""
        <iframe src="https://www.tradingview.com/embed-widget/mini-symbol-overview/?symbol=TVC%3AGOLDSILVER&locale=en" 
            width="100%" height="220" frameborder="0" allowtransparency="true" scrolling="no"></iframe>
        """, height=240)
        
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
                if shown >= 15:
                    break

                title = entry.get("title", "No title")
                link = entry.get("link", "#")
                pub_date_raw = entry.get("published", "No date")
                pub_date = convert_gmt_string_to_taipei(pub_date_raw)
                image_url = ""

                if "media_content" in entry and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get("url", "")

                if not image_url:
                    continue

                try:
                    img_check = requests.head(image_url, timeout=5)
                    if img_check.status_code != 200:
                        continue
                except:
                    continue

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
                            <div style="font-size: 12px; color: lightgray;">🗓️ {pub_date} (Taipei time)</div>
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
