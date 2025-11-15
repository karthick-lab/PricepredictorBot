import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import requests
from io import BytesIO
from datetime import datetime

# Load Excel from GitHub
@st.cache_data
def load_gold_data():
    url = "https://raw.githubusercontent.com/karthick-lab/NewsReader/main/src/test/resources/Data/GoldData.xlsx"
    response = requests.get(url)
    response.raise_for_status()
    excel_data = BytesIO(response.content)

    df = pd.read_excel(excel_data, engine="openpyxl")
    df.columns = ["Date", "Raw"]
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")
    df[["24K", "22K", "18K"]] = df["Raw"].apply(parse_prices).apply(pd.Series)
    df = df.dropna(subset=["24K", "22K", "18K"]).drop_duplicates(subset=["Date"])
    return df[["Date", "24K", "22K", "18K"]].sort_values("Date")

def parse_prices(text):
    match = re.search(r"₹([\d,]+).*?₹([\d,]+).*?₹([\d,]+)", text)
    if match:
        return [int(p.replace(",", "")) for p in match.groups()]
    return [None, None, None]

def get_mode(start, end):
    delta = (end - start).days
    if delta <= 31:
        return "daily"
    elif delta <= 365:
        return "monthly"
    else:
        return "yearly"

def aggregate(df, mode):
    if mode == "daily":
        return df
    elif mode == "monthly":
        df["Month"] = df["Date"].dt.to_period("M")
        return df.groupby("Month")[["24K", "22K", "18K"]].max().reset_index().rename(columns={"Month": "Date"})
    else:
        df["Year"] = df["Date"].dt.year
        return df.groupby("Year")[["24K", "22K", "18K"]].max().reset_index().rename(columns={"Year": "Date"})

def forecast_price(dates, prices, future_date):
    x = [d.toordinal() for d in dates]
    y = prices
    future_x = future_date.toordinal()
    m, b = np.polyfit(x, y, 1)
    return round(m * future_x + b, 2)

def predict_future(df, start_date, end_date, mode):
    future_dates = pd.date_range(start=start_date, end=end_date)
    if mode == "monthly":
        future_dates = future_dates.to_period("M").drop_duplicates().to_timestamp()
    elif mode == "yearly":
        future_dates = future_dates.to_period("Y").drop_duplicates().to_timestamp()

    predictions = []
    for d in future_dates:
        row = {
            "Date": d,
            "24K": forecast_price(df["Date"], df["24K"], d),
            "22K": forecast_price(df["Date"], df["22K"], d),
            "18K": forecast_price(df["Date"], df["18K"], d),
        }
        predictions.append(row)
    return pd.DataFrame(predictions)

def plot_gold(df, mode):
    fig, ax = plt.subplots(figsize=(10, 6))
    for karat, color in zip(["24K", "22K", "18K"], ["gold", "orange", "brown"]):
        ax.plot(df["Date"].astype(str), df[karat], label=karat, color=color)
    ax.set_title(f"Gold Price Trend ({mode.capitalize()})")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (₹/gram)")
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig)

# Streamlit UI
st.set_page_config(page_title="Gold Price Predictor", layout="wide")
st.title("📈 Gold Price Predictor")
st.markdown("Select a date range (up to 5 years) to view predicted gold prices for 24K, 22K, and 18K.")

start_date = st.date_input("Start Date", value=datetime.today())
end_date = st.date_input("End Date", value=datetime(2025, 1, 31))

if st.button("Submit"):
    if start_date >= end_date:
        st.error("End date must be after start date.")
    elif (end_date - start_date).days > 5 * 365:
        st.error("Date range exceeds 5 years.")
    else:
        df = load_gold_data()
        mode = get_mode(start_date, end_date)
        df_range = df[(df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))]

        if df_range.empty:
            st.warning("No historical data available for selected range. Showing predicted prices.")
            df_predicted = predict_future(df, start_date, end_date, mode)
            st.dataframe(df_predicted, use_container_width=True)
            plot_gold(df_predicted, mode)
        else:
            df_agg = aggregate(df_range, mode)
            st.subheader("📊 Gold Price Table")
            st.dataframe(df_agg, use_container_width=True)
            st.subheader("📉 Gold Price Chart")
            plot_gold(df_agg, mode)