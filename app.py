import streamlit as st
import pandas as pd
import yfinance as yf
import fitz  # PyMuPDF for PDF parsing
import re

def extract_transactions(pdf_file):
    transactions = []
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text")
            lines = text.split("\n")
            for line in lines:
                match = re.search(r'(\d{4}/\d{2}/\d{2})\s+(.+?)\s+₪\s?([\d,.]+)', line)  # Hebrew format
                match_usd = re.search(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$\s?([\d,.]+)', line)  # US format
                
                if match:
                    date, merchant, amount = match.groups()
                    currency = "₪"
                elif match_usd:
                    date, merchant, amount = match_usd.groups()
                    currency = "$"
                else:
                    continue
                
                amount = float(amount.replace(',', ''))  # Remove thousands separator
                transactions.append({"Date": date, "Merchant": merchant.strip(), "Amount": amount, "Currency": currency})
    
    return pd.DataFrame(transactions)

def get_stock_ticker(merchant):
    company_map = {
        "Amazon": "AMZN",
        "Apple": "AAPL",
    }
    return company_map.get(merchant, None)

st.title("Smart Expense to Investment Tracker")

uploaded_file = st.file_uploader("Upload a PDF expense report", type=["pdf"])

if uploaded_file:
    transactions_df = extract_transactions(uploaded_file)
    if transactions_df.empty:
        st.error("No valid transactions found in the PDF.")
    else:
        transactions_df["Ticker"] = transactions_df["Merchant"].apply(get_stock_ticker)
        transactions_df = transactions_df.dropna(subset=["Ticker"])
        
        st.subheader("Extracted Transactions")
        st.dataframe(transactions_df)
        
        stock_data = {}
        for _, row in transactions_df.iterrows():
            ticker = row["Ticker"]
            stock = yf.Ticker(ticker)
            history = stock.history(period="6mo")  # Fetch last 6 months of data
            stock_data[ticker] = history
        
        st.subheader("Stock Performance")
        for ticker, history in stock_data.items():
            st.line_chart(history["Close"], use_container_width=True)
