import streamlit as st
import pandas as pd
import yfinance as yf
import fitz  # PyMuPDF for PDF parsing
import re

# Load global stock market companies
@st.cache_data
def load_global_companies():
    sources = {
        "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "NASDAQ 100": "https://en.wikipedia.org/wiki/NASDAQ-100",
        "FTSE 100": "https://en.wikipedia.org/wiki/FTSE_100_Index",
        "DAX 40": "https://en.wikipedia.org/wiki/DAX",
        "Nikkei 225": "https://en.wikipedia.org/wiki/Nikkei_225"
    }
    company_map = {}
    
    for index, url in sources.items():
        try:
            df = pd.read_html(url)[0]
            if "Security" in df.columns:
                company_map.update(dict(zip(df["Security"].str.lower(), df["Symbol"])))
            elif "Company" in df.columns:
                company_map.update(dict(zip(df["Company"].str.lower(), df["Ticker"])))
        except Exception as e:
            print(f"Failed to load {index}: {e}")
    
    return company_map

global_companies = load_global_companies()

def extract_transactions(pdf_file):
    transactions = []
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text")
            lines = text.split("\n")
            for line in lines:
                match = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2})\s+(.+?)\s+[₪$€£]\s?([\d,.]+)', line)
                if match:
                    date, merchant, amount = match.groups()
                    currency = "₪" if "₪" in line else ("$" if "$" in line else ("€" if "€" in line else "£"))
                    amount = float(amount.replace(',', ''))  # Remove thousands separator
                    transactions.append({"Date": date, "Merchant": merchant.strip(), "Amount": amount, "Currency": currency})
    
    if not transactions:
        print("DEBUG: No transactions extracted. Check PDF structure.")
    
    return pd.DataFrame(transactions)

def get_stock_ticker(merchant):
    merchant_cleaned = merchant.lower()
    return global_companies.get(merchant_cleaned, None)

# Modern UI
title_html = """
    <h1 style='text-align: center; color: #4CAF50;'>💳 Smart Expense to Investment Tracker 📈</h1>
    <p style='text-align: center; font-size: 18px;'>Upload your credit card report and see how your spending connects to stock performance.</p>
    """
st.markdown(title_html, unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 Upload a PDF expense report", type=["pdf"])

if uploaded_file:
    transactions_df = extract_transactions(uploaded_file)
    if transactions_df.empty:
        st.error("⚠️ No valid transactions found. Please check your PDF format.")
    else:
        transactions_df["Ticker"] = transactions_df["Merchant"].apply(get_stock_ticker)
        transactions_df = transactions_df.dropna(subset=["Ticker"])
        
        st.subheader("📜 Extracted Transactions")
        st.dataframe(transactions_df.style.set_properties(**{'text-align': 'center'}))
        
        stock_data = {}
        for _, row in transactions_df.iterrows():
            ticker = row["Ticker"]
            stock = yf.Ticker(ticker)
            history = stock.history(period="6mo")  # Fetch last 6 months of data
            stock_data[ticker] = history
        
        st.subheader("📊 Stock Performance")
        for ticker, history in stock_data.items():
            st.line_chart(history["Close"], use_container_width=True)
