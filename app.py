import streamlit as st
import pandas as pd
import yfinance as yf
import fitz  # PyMuPDF for PDF parsing
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_stock_exchanges_companies():
    """
    Comprehensive function to scrape company lists from multiple stock exchanges
    """
    company_map = {}

    # Helper function to clean and standardize company names
    def clean_name(name):
        # Remove special characters, convert to lowercase
        return re.sub(r'[^\w\s]', '', str(name)).lower().strip()

    # Sources for different stock exchanges
    exchanges = [
        # US Exchanges
        {
            'name': 'S&P 500',
            'url': 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
            'name_col': 'Security',
            'symbol_col': 'Symbol'
        },
        {
            'name': 'NASDAQ 100',
            'url': 'https://en.wikipedia.org/wiki/NASDAQ-100',
            'name_col': 'Company',
            'symbol_col': 'Ticker'
        },
        # Israeli Stock Exchange
        {
            'name': 'Tel Aviv Stock Exchange (TASE)',
            'url': 'https://en.wikipedia.org/wiki/List_of_companies_listed_on_the_Tel_Aviv_Stock_Exchange',
            'name_col': 'Company',
            'symbol_col': 'Symbol'
        },
        # London Stock Exchange
        {
            'name': 'FTSE 100',
            'url': 'https://en.wikipedia.org/wiki/FTSE_100_Index',
            'name_col': 'Company',
            'symbol_col': 'Ticker'
        },
        # European Exchanges
        {
            'name': 'DAX 40',
            'url': 'https://en.wikipedia.org/wiki/DAX',
            'name_col': 'Company',
            'symbol_col': 'Ticker'
        }
    ]

    # Scrape company lists from Wikipedia
    for exchange in exchanges:
        try:
            tables = pd.read_html(exchange['url'])
            for table in tables:
                # Check if required columns exist
                if exchange['name_col'] in table.columns and exchange['symbol_col'] in table.columns:
                    # Clean and map company names to tickers
                    company_map.update(dict(
                        zip(
                            [clean_name(name) for name in table[exchange['name_col']]],
                            table[exchange['symbol_col']]
                        )
                    ))
                    break  # Use first matching table
        except Exception as e:
            st.warning(f"Could not scrape {exchange['name']}: {e}")

    # Additional custom sources
    additional_sources = [
        # Some top global companies not always in Wikipedia lists
        {
            'companies': {
                'apple': 'AAPL',
                'microsoft': 'MSFT',
                'amazon': 'AMZN',
                'google': 'GOOGL',
                'facebook': 'META',
                'tesla': 'TSLA',
                'netflix': 'NFLX',
                'intel': 'INTC',
                'nvidia': 'NVDA',
                'adobe': 'ADBE',
                'paypal': 'PYPL',
                'visa': 'V',
                'mastercard': 'MA'
            }
        }
    ]

    # Add additional sources
    for source in additional_sources:
        company_map.update(source['companies'])

    return company_map

def match_company_to_ticker(merchant_name, company_map):
    """
    Advanced company name matching algorithm
    """
    # Clean merchant name
    cleaned_merchant = re.sub(r'[^\w\s]', '', str(merchant_name)).lower().strip()
    
    # Exact match
    if cleaned_merchant in company_map:
        return company_map[cleaned_merchant]
    
    # Partial match
    for company_name, ticker in company_map.items():
        if company_name in cleaned_merchant or cleaned_merchant in company_name:
            return ticker
    
    return None

# Rest of your existing code remains the same...
def extract_transactions(pdf_file):
    transactions = []
    raw_text = ""
    
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text")
            raw_text += text + "\n"
            
            # Look for the transaction table section
            table_section = text.split("פירוט ענף שם בית העסק תאריך")
            if len(table_section) > 1:
                lines = table_section[1].split("\n")
                
                for line in lines:
                    # Regex to match transaction lines
                    match = re.match(r'^₪\s*([\d,.]+)\s*₪\s*([\d,.]+).*\s*(\d{2}/\d{2}/\d{4})$', line.strip())
                    if match:
                        try:
                            amount = float(match.group(1).replace(',', ''))
                            date_str = match.group(3)
                            
                            # Find merchant name (the text between amount and date)
                            merchant_match = re.search(r'₪\s*[\d,.]+\s*(.+?)\s*₪', line)
                            merchant = merchant_match.group(1).strip() if merchant_match else "Unknown"
                            
                            transactions.append({
                                "Date": pd.to_datetime(date_str, format='%d/%m/%Y'),
                                "Merchant": merchant,
                                "Amount": amount,
                                "Currency": "₪"
                            })
                        except Exception as e:
                            st.warning(f"Could not parse transaction: {line}. Error: {e}")
    
    # Create DataFrame
    if transactions:
        df = pd.DataFrame(transactions)
        return raw_text, df
    else:
        st.error("❌ No transactions could be extracted.")
        return raw_text, pd.DataFrame()

# Load global companies (this will be done when the script runs)
global_companies = get_stock_exchanges_companies()

# The rest of your Streamlit app code remains the same...
# When adding tickers, use:
# transactions_df["Ticker"] = transactions_df["Merchant"].apply(lambda x: match_company_to_ticker(x, global_companies))
