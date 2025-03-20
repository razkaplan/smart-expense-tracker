import streamlit as st
import pandas as pd
import yfinance as yf
import pdfplumber  # For PDF parsing
import re
from rapidfuzz import process, fuzz
import unicodedata
from bidi.algorithm import get_display
from arabic_reshaper import reshape
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords', quiet=True)
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import traceback
import sys
from parse_credit_card import is_probably_english, extract_transactions
import plotly.express as px
import plotly.graph_objects as go
import os
import pytz
import pymupdf
from io import BytesIO
import numpy as np

# Constants for company information
INTERNATIONAL_COMPANIES = [
    {'name': 'Netflix', 'ticker': 'NFLX', 'exchange': 'NASDAQ', 'aliases': ['netflix', 'netflix.com']},
    {'name': 'Google', 'ticker': 'GOOGL', 'exchange': 'NASDAQ', 'aliases': ['google', 'youtube', 'alphabet', 'google*']},
    {'name': 'Alibaba', 'ticker': 'BABA', 'exchange': 'NYSE', 'aliases': ['ali', 'aliexpress', 'alibaba']},
    {'name': 'Amazon', 'ticker': 'AMZN', 'exchange': 'NASDAQ', 'aliases': ['amazon', 'aws', 'kindle', 'amazon prime']},
    {'name': 'Apple', 'ticker': 'AAPL', 'exchange': 'NASDAQ', 'aliases': ['apple', 'itunes', 'apple store', 'icloud']},
    {'name': 'Microsoft', 'ticker': 'MSFT', 'exchange': 'NASDAQ', 'aliases': ['microsoft', 'xbox', 'ms', 'msft', 'azure']},
    {'name': 'Meta', 'ticker': 'META', 'exchange': 'NASDAQ', 'aliases': ['meta', 'facebook', 'instagram', 'fb', 'whatsapp']},
    {'name': 'Tesla', 'ticker': 'TSLA', 'exchange': 'NASDAQ', 'aliases': ['tesla', 'tsla']},
    {'name': 'Disney', 'ticker': 'DIS', 'exchange': 'NYSE', 'aliases': ['disney', 'disney+', 'disneyplus']},
    {'name': 'PayPal', 'ticker': 'PYPL', 'exchange': 'NASDAQ', 'aliases': ['paypal', 'pay pal']},
    {'name': 'Uber', 'ticker': 'UBER', 'exchange': 'NYSE', 'aliases': ['uber', 'uber eats']},
    {'name': 'Spotify', 'ticker': 'SPOT', 'exchange': 'NYSE', 'aliases': ['spotify', 'spot']}
]

ISRAELI_COMPANIES = [
    {'name': 'Partner', 'ticker': 'PTNR.TA', 'aliases': ['פרטנר', 'partner', 'פרטנר תקשורת']},
    {'name': 'Cellcom', 'ticker': 'CEL.TA', 'aliases': ['סלקום', 'cellcom', 'סלקום ישראל']},
    {'name': 'Menora', 'ticker': 'MMHD.TA', 'aliases': ['מנורה', 'menora', 'מבטחים', 'מנורה מבטחים']},
    {'name': 'Bank Leumi', 'ticker': 'LUMI.TA', 'aliases': ['לאומי', 'leumi', 'בנק לאומי']},
    {'name': 'Bank Hapoalim', 'ticker': 'POLI.TA', 'aliases': ['פועלים', 'hapoalim', 'בנק הפועלים']},
    {'name': 'Bank Discount', 'ticker': 'DSCT.TA', 'aliases': ['דיסקונט', 'discount', 'בנק דיסקונט']},
    {'name': 'Strauss', 'ticker': 'STRS.TA', 'aliases': ['שטראוס', 'strauss', 'שטראוס גרופ']},
    {'name': 'Meitav', 'ticker': 'MTDS.TA', 'aliases': ['מיטב', 'meitav', 'מיטב דש', 'מיטב-דש']},
    {'name': 'El Al', 'ticker': 'ELAL.TA', 'aliases': ['אל על', 'elal', 'el al', 'אל-על']},
    {'name': 'Yohananof', 'ticker': 'YHNF.TA', 'aliases': ['יוחננוף', 'yohananof', 'יוחננוף ובניו']}
]

# Enable debug mode
DEBUG_MODE = True

def debug_print(*args, **kwargs):
    """Print debug information if DEBUG_MODE is True"""
    if DEBUG_MODE:
        print("DEBUG:", *args, **kwargs)
        sys.stdout.flush()  # Ensure output is immediately visible

# Wrap potentially problematic functions to catch unhashable type errors
def safe_hash(obj):
    """Safely get a hash for an object or return a string representation if unhashable"""
    try:
        return hash(obj)
    except TypeError as e:
        debug_print(f"Unhashable object: {type(obj)}, value: {obj}, error: {e}")
        # Convert to a hashable type (string representation)
        return hash(str(obj))

# List of known company names and their common variations
company_names = [
    "Apple", "Microsoft", "Amazon", "Google", "Samsung", "Toyota", "Coca-Cola", "Mercedes-Benz",
    "McDonald's", "BMW", "Louis Vuitton", "Tesla", "Cisco", "Nike", "Instagram", "Disney", "Adobe",
    "Oracle", "IBM", "SAP", "Facebook", "Hermès", "Chanel", "YouTube", "J.P. Morgan", "Pepsi",
    "Gucci", "Ford", "L'Oréal", "AXA", "Lexus", "HSBC", "Mastercard", "Citi", "Nissan", "Audi",
    "T-Mobile", "Daimler", "Barclays", "Johnson & Johnson", "Tiffany & Co.", "Cartier",
    "Jack Daniel's", "Moët & Chandon", "Credit Suisse", "Shell", "Visa", "Pizza Hut", "Gap", "Corona", "UBS", "Nivea", "Smirnoff",
    "Walmart", "Kellogg's", "Heineken", "Colgate", "Prada", "Chrysler", "Kia", "Porsche", "Subaru", "Lindt", "H&M", "Kraft Heinz",
    "DHL", "Barclays", "Unilever", "Nestlé", "Procter & Gamble", "PepsiCo", "Sony", "Gucci", "IKEA", "Honda", "Volvo", "Accenture",
    "Rolex", "Chanel", "Netflix", "Lululemon", "Under Armour", "Whole Foods Market", "Sephora", "Dell", "Sony", "Pinterest",
    "Skype", "Uber", "Airbnb", "Spotify", "PayPal", "Alibaba", "Tencent", "Boeing", "Mastercard", "Target",
    "AliExpress", "Booking.com", "Ebay", "Starbucks", "Zara", "Adidas", "Expedia", "Etsy", "Shopify", "Lyft",
    "Dropbox", "Twitter", "LinkedIn", "Zoom", "DocuSign", "Slack", "Twilio", "Snap", "Pinterest", "Fiverr"
]

# Enhanced payment methods list - these should be ignored
PAYMENT_METHODS = [
    'visa', 'mastercard', 'amex', 'american express', 'discover',
    'paypal', 'debit', 'credit', 'card', 'payment', 'bank',
    'transfer', 'transaction', 'direct debit', 'wire', 'online',
    'banking', 'mobile', 'pay', 'fee', 'service', 'charge',
    'purchase', 'payment method', 'venmo', 'chase', 'zelle',
    'google pay', 'apple pay', 'samsung pay', 'gpay', 'contactless',
]

# Company mappings
COMPANY_TO_TICKER = {
    'Netflix': {'ticker': 'NFLX', 'exchange': 'NASDAQ', 'name': 'Netflix Inc'},
    'NETFLIX.COM': {'ticker': 'NFLX', 'exchange': 'NASDAQ', 'name': 'Netflix Inc'},
    'Google': {'ticker': 'GOOGL', 'exchange': 'NASDAQ', 'name': 'Alphabet Inc'},
    'YouTube': {'ticker': 'GOOGL', 'exchange': 'NASDAQ', 'name': 'Alphabet Inc'},
    'GOOGLE*': {'ticker': 'GOOGL', 'exchange': 'NASDAQ', 'name': 'Alphabet Inc'},
    'Alphabet': {'ticker': 'GOOGL', 'exchange': 'NASDAQ', 'name': 'Alphabet Inc'},
    'Alibaba': {'ticker': 'BABA', 'exchange': 'NYSE', 'name': 'Alibaba Group'},
    'aliexpress': {'ticker': 'BABA', 'exchange': 'NYSE', 'name': 'Alibaba Group'},
    'ali': {'ticker': 'BABA', 'exchange': 'NYSE', 'name': 'Alibaba Group'},
    'Amazon': {'ticker': 'AMZN', 'exchange': 'NASDAQ', 'name': 'Amazon.com Inc'},
    'AMZN': {'ticker': 'AMZN', 'exchange': 'NASDAQ', 'name': 'Amazon.com Inc'},
    'Apple': {'ticker': 'AAPL', 'exchange': 'NASDAQ', 'name': 'Apple Inc'},
    'Microsoft': {'ticker': 'MSFT', 'exchange': 'NASDAQ', 'name': 'Microsoft Corporation'},
    'Meta': {'ticker': 'META', 'exchange': 'NASDAQ', 'name': 'Meta Platforms Inc'},
    'Facebook': {'ticker': 'META', 'exchange': 'NASDAQ', 'name': 'Meta Platforms Inc'},
    'Instagram': {'ticker': 'META', 'exchange': 'NASDAQ', 'name': 'Meta Platforms Inc'},
}

# Hebrew company mappings
HEBREW_COMPANY_TO_TICKER = {
    'פרטנר': {'ticker': 'PTNR', 'exchange': 'NASDAQ', 'name': 'Partner Communications'},
    'סלקום': {'ticker': 'CEL', 'exchange': 'NYSE', 'name': 'Cellcom Israel'},
    'בזק': {'ticker': 'BZQIY', 'exchange': 'OTC', 'name': 'Bezeq'},
    'טבע': {'ticker': 'TEVA', 'exchange': 'NYSE', 'name': 'Teva Pharmaceutical'},
    'כיל': {'ticker': 'ICL', 'exchange': 'NYSE', 'name': 'ICL Group'},
    'לאומי': {'ticker': 'LUMI.TA', 'exchange': 'TASE', 'name': 'Bank Leumi'},
    'פועלים': {'ticker': 'POLI.TA', 'exchange': 'TASE', 'name': 'Bank Hapoalim'},
    'דיסקונט': {'ticker': 'DSCT.TA', 'exchange': 'TASE', 'name': 'Israel Discount Bank'},
}

def extract_english_segments(text):
    """Extract segments that are likely English words or phrases"""
    # Enhanced pattern to catch more company names including Netflix
    patterns = [
        r'(?:^|[^\w])([A-Za-z][A-Za-z\s\.]+)(?:[^\w]|$)',  # Standard pattern
        r'netflix',  # Special case for Netflix
        r'amzn',     # Special case for Amazon
        r'google',   # Special case for Google
        r'apple',    # Special case for Apple
        r'spotify',  # Special case for Spotify
        r'ali',      # Special case for Alibaba
        r'baba',     # Special case for Alibaba ticker
        r'aliexpress', # Special case for Aliexpress
        r'youtube',   # Special case for YouTube
        r'youtubepremium', # Special case for YouTube Premium
        # Add Israeli companies
        r'מגדל',      # Migdal (Hebrew)
        r'סופרשוק',   # Supermarket (Hebrew)
        r'יוחננוף'    # Yohananof (Hebrew)
    ]
    
    matches = []
    for pattern in patterns:
        # Get the pattern as string for debugging
        pattern_str = pattern
        if not isinstance(pattern, str):
            pattern_str = pattern.pattern
            
        if re.search(pattern, text, re.IGNORECASE):
            found_matches = re.findall(pattern, text, re.IGNORECASE)
            if found_matches:
                debug_print(f"Found match with pattern '{pattern_str}': {found_matches}")
                matches.extend(found_matches)
            else:
                debug_print(f"Pattern '{pattern_str}' matched but no captures returned")
                # If the pattern doesn't have captures but matches, add the matching text
                matches.append(str(re.search(pattern, text, re.IGNORECASE).group(0)))
    
    # Filter short segments and common non-merchant terms
    filtered_matches = []
    
    for match in matches:
        match = match.strip()
        if len(match) >= 3 and match.lower() not in PAYMENT_METHODS:
            filtered_matches.append(match)
        else:
            debug_print(f"Filtered out match: '{match}' (too short or payment method)")
    
    debug_print(f"Extracted segments: {filtered_matches}")
    return filtered_matches

def is_payment_method(text):
    """Check if text is likely a payment method rather than a merchant"""
    text = text.lower().strip()
    
    # Check for exact matches first
    if text in PAYMENT_METHODS:
        debug_print(f"Payment method detected (exact match): {text}")
        return True
    
    # Check for payment methods as part of text
    for method in PAYMENT_METHODS:
        if method in text or text in method:
            debug_print(f"Payment method detected (partial match): {text} contains or is contained in {method}")
            return True
    
    # Special cases
    if 'google pay' in text or 'pay' in text and 'google' in text:
        debug_print(f"Payment method detected (special case): {text} is related to Google Pay")
        return True
        
    return False

def clean_merchant_name(name):
    """Clean and normalize merchant names"""
    # Remove stopwords and payment indicators
    words = [word for word in name.lower().split() 
             if word not in PAYMENT_METHODS]
    return ' '.join(words)

def get_stock_ticker(merchant_name):
    """Get stock ticker symbol for a merchant name"""
    if not merchant_name:
        return None
    
    # Clean merchant name
    clean_name = merchant_name.lower().strip()
    
    # Check in direct mapping first
    for company, ticker in COMPANY_TO_TICKER.items():
        if company.lower() in clean_name or clean_name in company.lower():
            debug_print(f"Direct mapping found: {merchant_name} -> {ticker}")
            return [ticker]
    
    # Special case for Alibaba/AliExpress
    if 'ali' in clean_name or 'baba' in clean_name:
        debug_print(f"Special case for Alibaba: {merchant_name} -> BABA")
        return ['BABA']
    
    # Special case for YouTube/Google
    if 'youtube' in clean_name:
        debug_print(f"Special case for YouTube: {merchant_name} -> GOOGL")
        return ['GOOGL']
    
    # Special case for Israeli companies
    if re.search(r'[א-ת]', merchant_name):  # Contains Hebrew characters
        # Check for Migdal
        if 'מגדל' in merchant_name:
            debug_print(f"Found Israeli company Migdal: {merchant_name} -> MGDL.TA")
            return ['MGDL.TA']
        
        # Check for Yohananof
        if 'יוחננוף' in merchant_name or 'סופר שוק' in merchant_name:
            debug_print(f"Found Israeli company Yohananof: {merchant_name} -> YHNF.TA")
            return ['YHNF.TA']
    
    # If we couldn't find a stock ticker directly, try a fuzzy match
    try:
        fuzzy_threshold = 80  # minimum similarity score (0-100)
        
        best_match = None
        best_score = 0
        
        for company, ticker in COMPANY_TO_TICKER.items():
            # Skip Hebrew companies for fuzzy matching
            if re.search(r'[א-ת]', company):
                continue
                
            # Calculate similarity score
            score = fuzz.partial_ratio(clean_name, company.lower())
            
            if score > fuzzy_threshold and score > best_score:
                best_match = ticker
                best_score = score
        
        if best_match:
            debug_print(f"Fuzzy match found: {merchant_name} -> {best_match} (score: {best_score})")
            return [best_match]
        
    except Exception as e:
        debug_print(f"Error in fuzzy matching: {e}")
    
    # If we still don't have a match, return None
    return None

def search_tickers_via_yfinance(query):
    """Search for tickers matching a query using yahoo finance"""
    try:
        # Try to directly match a common ticker pattern first (3-5 uppercase letters)
        if re.match(r'^[A-Z]{3,5}$', query):
            return [query]
        
        # Prepare the query
        query = query.strip().lower()
        
        # Skip common invalid queries
        if len(query) < 3 or query in ['www', 'com', 'org', 'net']:
            return []
        
        # Check for direct matches in our mapping
        for company, ticker in COMPANY_TO_TICKER.items():
            if company in query or query in company:
                # Validate ticker exists
                try:
                    ticker_info = yf.Ticker(ticker).info
                    if 'regularMarketPrice' in ticker_info:
                        return [ticker]
                except:
                    pass
        
        # Use yfinance search - handle potential failures
        try:
            search_result = yf.Tickers(query.upper())
            if hasattr(search_result, 'tickers'):
                valid_tickers = []
                for ticker in list(search_result.tickers.keys())[:3]:  # Check top 3 matches
                    try:
                        info = yf.Ticker(ticker).info
                        if 'regularMarketPrice' in info:
                            valid_tickers.append(ticker)
                    except:
                        continue
                return valid_tickers
        except:
            pass
        
        return []
    except Exception as e:
        debug_print(f"Error in ticker search: {e}")
        return []

def is_latin(text):
    """Check if text contains Latin characters"""
    # Normalize text and remove non-alphabetic characters
    if text is None:
        return False
        
    # Convert to string if not already
    text = str(text)
    
    # Keep only alphabetic characters
    text = ''.join(char for char in text if char.isalpha() or char.isspace())
    
    # Check if any Latin characters are present
    latin_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    
    # Use string comparison instead of set operations
    for char in text:
        if char in latin_chars:
            return True
    return False

def extract_transactions(pdf_file):
    transactions = []
    raw_text = ""
    english_merchants = []
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text(
                    x_tolerance=1,
                    y_tolerance=1,
                    layout=True,
                    x_density=7.25,
                    y_density=13
                )
                raw_text += text + "\n"
                debug_print(f"Raw text from page: {text}")
                
                # Split into lines and process each line
                lines = text.split('\n')
                
                for line in lines:
                    # Skip header/footer lines
                    if any(skip in line for skip in ['ךותמ', 'רושיאל', 'תויביר']):
                        continue
                        
                    # Pattern for standard transaction line in Israeli credit card statement
                    # Format: Amount Amount Type Description Date
                    match = re.search(r'([₪€$])\s+([\d,\.]+)\s+\1\s+([\d,\.]+)\s*(.*?)\s+(\d{2}/\d{2}/\d{4})', line)
                    
                    if match:
                        try:
                            currency = match.group(1)
                            amount_str = match.group(2).replace(',', '')
                            description = match.group(4).strip()
                            date = match.group(5)
                            
                            # Skip if it's a payment method or empty description
                            if not description or is_payment_method(description):
                                continue
                                
                            # Handle special cases - expand detection patterns
                            if 'GOOGLE' in description.upper() or 'YOUTUBE' in description.upper():
                                english_merchants.append('Google')
                            elif 'NETFLIX' in description.upper():
                                english_merchants.append('Netflix')
                            elif 'ALI' in description.upper() or 'BABA' in description.upper():
                                english_merchants.append('Alibaba')
                            elif 'AMAZON' in description.upper():
                                english_merchants.append('Amazon')
                            elif 'APPLE' in description.upper() or 'ICLOUD' in description.upper():
                                english_merchants.append('Apple')
                            elif 'MICROSOFT' in description.upper() or 'MSFT' in description.upper():
                                english_merchants.append('Microsoft')
                            elif 'META' in description.upper() or 'FACEBOOK' in description.upper() or 'INSTAGRAM' in description.upper():
                                english_merchants.append('Meta')
                            
                            # Check for Israeli companies
                            if 'פרטנר' in description or 'PARTNER' in description.upper():
                                english_merchants.append('Partner')
                            elif 'סלקום' in description or 'CELLCOM' in description.upper():
                                english_merchants.append('Cellcom')
                            elif 'מנורה' in description or 'MENORA' in description.upper():
                                english_merchants.append('Menora')
                            
                            # Also check company mappings
                            for company_name in COMPANY_TO_TICKER.keys():
                                if isinstance(company_name, str) and len(company_name) > 2 and company_name.lower() in description.lower():
                                    debug_print(f"Found company: {company_name} in {description}")
                                    english_merchants.append(company_name)
                            
                            transaction = {
                                "Date": fix_date_direction(date),
                                "Merchant": description,
                                "Amount": float(amount_str),
                                "Currency": currency,
                                "HasEnglishCompany": bool(re.search(r'[a-zA-Z]', description))
                            }
                            transactions.append(transaction)
                            debug_print(f"Added transaction: {transaction}")
                            
                        except Exception as e:
                            debug_print(f"Error processing line match: {e}")
                            continue
                    
        debug_print(f"Total transactions extracted: {len(transactions)}")
        debug_print(f"English merchants found: {list(set(english_merchants))}")  # Remove duplicates
        
        if not transactions:
            debug_print("No transactions were extracted!")
            
        return pd.DataFrame(transactions), english_merchants
        
    except Exception as e:
        debug_print(f"Error extracting transactions: {e}")
        traceback.print_exc()
        return pd.DataFrame(), []

def fix_date_direction(date):
    """Convert date to YYYY-MM-DD format for consistency."""
    if isinstance(date, str):
        parts = date.split('/')
        if len(parts) == 3:
            day, month, year = parts[0], parts[1], parts[2]
            # Check date format and convert
            if len(year) == 4:  # DD/MM/YYYY format
                return f"{year}-{month}-{day}"
            else:  # Possibly MM/DD/YY format
                # Assuming year is the last part
                return f"20{year}-{month}-{day}" if len(year) == 2 else date
    return date

def get_stock_performance(ticker, date, amount):
    """Calculate stock performance for a given transaction."""
    try:
        debug_print(f"Calculating performance for {ticker} from {date} with amount {amount} ₪")
        
        # Convert amount from ILS to USD if needed
        if '.TA' in ticker:
            # TASE stocks are already in ILS
            currency_amount = amount
            debug_print(f"TASE stock detected, keeping amount in ILS: {currency_amount:.2f} ILS")
        else:
            # International stocks need USD conversion
            currency_amount = amount * 0.28  # Using a fixed rate for now
            debug_print(f"Converting {amount} ILS to {currency_amount:.2f} USD using rate 0.28")
        
        # Handle date format conversion
        if '-' in str(date):
            # Convert from YYYY-MM-DD to DD/MM/YYYY
            date_parts = str(date).split('-')
            date = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
            debug_print(f"Converted date format from YYYY-MM-DD to DD/MM/YYYY: {date}")
        
        # Parse the date
        try:
            transaction_date = datetime.strptime(date, '%d/%m/%Y')
        except ValueError:
            try:
                # Try alternative format YYYY/MM/DD
                transaction_date = datetime.strptime(date, '%Y/%m/%d')
            except ValueError:
                debug_print(f"Error parsing date {date} with any known format")
                return None, None
        
        # Skip future dates
        if transaction_date > datetime.now():
            debug_print(f"Skipping future date: {date}")
            return None, None
            
        # Normalize date to YYYY-MM-DD for yfinance
        normalized_date = transaction_date.strftime('%Y-%m-%d')
        debug_print(f"Normalized date: {normalized_date}")
        
        # Get historical data
        stock = yf.Ticker(ticker)
        hist = stock.history(start=normalized_date, end=(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
        
        if hist.empty:
            debug_print(f"No historical data found for {ticker}")
            return None, None
            
        # Get the first available price after the transaction date
        first_price = hist.iloc[0]['Close']
        debug_print(f"Found historical price: ${first_price:.2f} on {hist.index[0].strftime('%Y-%m-%d')}")
        
        # Get current price
        current_price = stock.info.get('regularMarketPrice')
        if not current_price:
            debug_print(f"Could not get current price for {ticker}")
            return None, None
        debug_print(f"Current price for {ticker}: ${current_price:.2f}")
        
        # Calculate performance
        shares = currency_amount / first_price
        value_change = shares * (current_price - first_price)
        percent_change = ((current_price - first_price) / first_price) * 100
        
        debug_print(f"Performance calculation: {shares:.4f} shares, value change: ${value_change:.2f}, percent change: {percent_change:.2f}%")
        debug_print(f"  Performance calculated: {percent_change:.2f}%, {value_change:.2f} ₪")
        
        return percent_change, value_change
        
    except Exception as e:
        debug_print(f"Error calculating performance for {ticker}: {str(e)}")
        return None, None

def find_company_transactions(df, company_name, aliases=None):
    """
    Find transactions related to a specific company.
    
    Args:
        df (DataFrame): DataFrame containing transactions
        company_name (str): Name of the company to search for
        aliases (list, optional): List of alternative names for the company
        
    Returns:
        DataFrame: Transactions related to the company
    """
    if df is None or df.empty:
        debug_print(f"No transactions provided for company: {company_name}")
        return pd.DataFrame()
    
    # Prepare search terms - company name and any aliases
    search_terms = [company_name.lower()]
    if aliases:
        search_terms.extend([alias.lower() for alias in aliases])
    
    # Create a mask to match any of the terms
    mask = pd.Series(False, index=df.index)
    for term in search_terms:
        # Check for exact match, contains match, or fuzzy match
        term_mask = df['Merchant'].str.lower().str.contains(term, case=False, na=False, regex=True)
        
        # For shorter terms (3 characters or less), require more strict matching to avoid false positives
        if len(term) <= 3:
            # For very short terms, require them to be standalone words or with punctuation boundaries
            term_mask = df['Merchant'].str.lower().str.contains(r'\b' + term + r'\b|^' + term + r'|' + term + r'$', 
                                                              case=False, na=False, regex=True)
        
        mask = mask | term_mask
    
    # Special case for google - it might appear as "GOOGLE*" in transactions
    if company_name.lower() == 'google':
        mask = mask | df['Merchant'].str.lower().str.contains('google[*]', case=False, na=False, regex=True)
    
    # Special case for netflix - might appear with .com or without spaces
    if company_name.lower() == 'netflix':
        mask = mask | df['Merchant'].str.lower().str.contains('netflix\.com', case=False, na=False, regex=True)
    
    # Special case for amazon - might appear with various suffixes
    if company_name.lower() == 'amazon':
        amazon_patterns = ['amazon\.', 'amzn', 'prime']
        for pattern in amazon_patterns:
            mask = mask | df['Merchant'].str.lower().str.contains(pattern, case=False, na=False, regex=True)
    
    # Special case for payment processors like PayPal that might be connected to various merchants
    if company_name.lower() in ['paypal', 'bit', 'פייפאל']:
        mask = mask | df['Merchant'].str.lower().str.contains(r'\bpaypal\b|\bפייפאל\b|\bביט\b|\bbit\b', 
                                                            case=False, na=False, regex=True)
    
    # Check for hebrew company names (handle RTL issues)
    hebrew_company_mappings = {
        'partner': ['פרטנר', 'רנטרפ'],
        'cellcom': ['סלקום', 'םוקלס'],
        'menora': ['מנורה', 'הרונמ', 'מבטחים', 'םיחטבמ'],
        'discount': ['דיסקונט', 'טנוקסיד'],
        'leumi': ['לאומי', 'ימואל'],
        'hapoalim': ['הפועלים', 'םילעופה'],
        'strauss': ['שטראוס', 'סוארטש'],
        'el al': ['אל על', 'לע לא'],
    }
    
    # Check for possible Hebrew names
    lower_company = company_name.lower()
    if lower_company in hebrew_company_mappings:
        for hebrew_name in hebrew_company_mappings[lower_company]:
            mask = mask | df['Merchant'].str.contains(hebrew_name, case=False, na=False, regex=False)
    
    results = df[mask].copy()
    debug_print(f"Found {len(results)} transactions for {company_name}")
    
    # Log what was found for debugging
    for _, row in results.iterrows():
        debug_print(f"Found transaction matching {company_name}: {row['Merchant']}")
    
    return results

def get_companies_with_transactions(transactions_df):
    """Get a DataFrame of companies and their transactions."""
    companies_data = []
    
    debug_print(f"Transaction dataframe has {len(transactions_df)} rows with columns: {transactions_df.columns.tolist()}")
    
    # Process international companies
    for company_info in INTERNATIONAL_COMPANIES:
        company_name = company_info['name']
        ticker = company_info['ticker']
        exchange = company_info['exchange']
        aliases = company_info.get('aliases', [])
        
        try:
            transactions = find_company_transactions(transactions_df, company_name, aliases)
            
            if not transactions.empty:
                for _, trans in transactions.iterrows():
                    companies_data.append({
                        'Company': company_name,
                        'Ticker': ticker,
                        'Exchange': exchange,
                        'Transaction': trans
                    })
                debug_print(f"Found {len(transactions)} transactions for {company_name} ({ticker})")
        except Exception as e:
            debug_print(f"Error processing {company_name}: {e}")
            debug_print(traceback.format_exc())
    
    # Process Israeli companies - improved detection
    for company_info in ISRAELI_COMPANIES:
        company_name = company_info['name']
        ticker = company_info['ticker']
        exchange = 'TASE'  # Tel Aviv Stock Exchange
        aliases = company_info.get('aliases', [])
        
        try:
            # Enhanced debugging for TASE companies
            debug_print(f"Searching for TASE company: {company_name} with aliases: {aliases}")
            
            # Look specifically for Hebrew text in the transaction description
            transactions = find_company_transactions(transactions_df, company_name, aliases)
            
            # For Partner Communications - specific handling for "רנטרפ" appearing in statements
            if company_name == 'Partner' and transactions.empty:
                debug_print("Force processing special company: Partner with ticker PTNR.TA")
                # Look for partner in any transaction with תקשורת (communications in Hebrew)
                partner_mask = transactions_df['Merchant'].str.contains('תקשורת') & transactions_df['Merchant'].str.contains('פרטנר|רנטרפ|partner', case=False, regex=True)
                transactions = transactions_df[partner_mask].copy()
            
            # For Cellcom - specific handling
            if company_name == 'Cellcom' and transactions.empty:
                debug_print("Force processing special company: Cellcom with ticker CEL.TA")
                # Look for cellcom in any transaction with תקשורת שירות or סלקום
                cellcom_mask = (transactions_df['Merchant'].str.contains('תקשורת שירות') | 
                               transactions_df['Merchant'].str.contains('סלקום|םוקלס|cellcom', case=False, regex=True))
                transactions = transactions_df[cellcom_mask].copy()
            
            # For Menora - specific handling
            if company_name == 'Menora' and transactions.empty:
                debug_print("Force processing special company: Menora with ticker MMHD.TA")
                # Look for menora in any transaction with מבטחים
                menora_mask = transactions_df['Merchant'].str.contains('מבטחים|םיחטבמ|מנורה|הרונמ|menora', case=False, regex=True)
                transactions = transactions_df[menora_mask].copy()
                
            # For Yohananof - specific handling
            if company_name == 'Yohananof' and transactions.empty:
                debug_print("Force processing special company: Yohananof with ticker YHNF.TA")
                # Look for Yohananof in any transaction with supermarket-related terms
                yohananof_mask = (transactions_df['Merchant'].str.contains('יוחננוף|ףוננחוי', case=False, regex=True) | 
                                 transactions_df['Merchant'].str.contains('סופר שוק|סופרמרקט|קוש רפוס', case=False, regex=True))
                transactions = transactions_df[yohananof_mask].copy()
            
            if not transactions.empty:
                for _, trans in transactions.iterrows():
                    companies_data.append({
                        'Company': company_name,
                        'Ticker': ticker,
                        'Exchange': exchange,
                        'Transaction': trans
                    })
                debug_print(f"Found {len(transactions)} transactions for {company_name} ({ticker}) [TASE]")
        except Exception as e:
            debug_print(f"Error processing TASE company {company_name}: {e}")
            debug_print(traceback.format_exc())
    
    # Create DataFrame from companies_data
    if companies_data:
        companies_df = pd.DataFrame(companies_data)
        return companies_df
    else:
        debug_print("No companies with transactions found")
        return pd.DataFrame(columns=['Company', 'Ticker', 'Exchange', 'Transaction'])

def calculate_investment_performance(companies_df):
    """Calculate investment performance for companies based on transaction data."""
    if companies_df is None or companies_df.empty:
        debug_print("No companies with transactions data provided")
        return pd.DataFrame()
    
    results = []
    
    for _, row in companies_df.iterrows():
        company_name = row['Company']
        ticker = row['Ticker']
        exchange = row['Exchange']
        transaction = row['Transaction']
        
        try:
            # Extract transaction date and amount
            transaction_date = transaction['Date']
            transaction_amount = transaction['Amount']
            
            debug_print(f"\nProcessing {company_name} ({ticker}) on {exchange}:")
            debug_print(f"  Transaction date: {transaction_date}")
            debug_print(f"  Transaction amount: {transaction_amount} ₪")
            
            # Calculate performance
            percent_change, value_change = get_stock_performance(ticker, transaction_date, transaction_amount)
            debug_print(f"  Performance calculated: {percent_change:.2f}%, {value_change:.2f} ₪")
            
            # Add to results
            results.append({
                'Company': company_name,
                'Ticker': ticker,
                'Exchange': exchange,
                'Transaction Date': transaction_date,
                'Amount (₪)': transaction_amount,
                'Value Change (₪)': value_change,
                'Percent Change': percent_change
            })
        except Exception as e:
            debug_print(f"Error calculating performance for {company_name}: {e}")
            debug_print(traceback.format_exc())
    
    if not results:
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=[
            'Company', 'Ticker', 'Exchange', 'Transaction Date', 'Amount (₪)', 
            'Value Change (₪)', 'Percent Change'
        ])
    
    # Convert results to DataFrame
    return pd.DataFrame(results)

def main():
    st.set_page_config(
        page_title="Smart Expense Tracker",
        page_icon="💰",
        layout="wide"
    )

    # Custom CSS for better mobile responsiveness and UI
    st.markdown("""
        <style>
        .main {
            padding: 0rem 1rem;
        }
        .title {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 2rem;
        }
        .tagline {
            font-size: 1.2rem;
            color: #666;
            margin-bottom: 2rem;
        }
        .info-box {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='title'>Smart Expense Tracker 💰</h1>", unsafe_allow_html=True)
    st.markdown("<p class='tagline'>Put your Money where your mouth is</p>", unsafe_allow_html=True)

    # Information section
    with st.expander("ℹ️ How it works", expanded=True):
        st.markdown("""
        This tool helps you understand your spending habits and their potential impact on the market:
        1. **Upload your credit card statement** (PDF format)
        2. **See which public companies you're supporting** through your purchases
        3. **Track your market influence** by seeing how much you've contributed to each company
        4. **Learn about financial impact** and make informed decisions about your spending
        """)

    uploaded_file = st.file_uploader("Upload your credit card statement (PDF)", type="pdf")
    if uploaded_file is not None:
        try:
            with st.spinner('Processing your statement...'):
                # Get transactions from the PDF
                transactions_result = extract_transactions(uploaded_file)
                if isinstance(transactions_result, tuple):
                    transactions_df, debug_info = transactions_result
                else:
                    transactions_df = transactions_result
                    debug_info = None

            if transactions_df is None or len(transactions_df) == 0:
                st.error("No transactions found in the PDF. Please make sure you uploaded a valid credit card statement.")
                return

            # Update date parsing logic to handle both formats (YYYY-MM-DD and DD/MM/YYYY)
            try:
                # First try parsing with format detection
                transactions_df['Date'] = pd.to_datetime(transactions_df['Date'], format='mixed', dayfirst=True, errors='coerce')
                # Then convert all to a standard format
                transactions_df['Date'] = transactions_df['Date'].dt.strftime('%Y-%m-%d')
                debug_print("Successfully parsed dates with mixed format")
            except Exception as e:
                debug_print(f"Error in date parsing: {e}")
                # Fallback method - handle each format separately
                def parse_date(date_str):
                    if pd.isna(date_str):
                        return date_str
                    date_str = str(date_str)
                    try:
                        if '-' in date_str:  # YYYY-MM-DD
                            return date_str
                        elif '/' in date_str:
                            parts = date_str.split('/')
                            if len(parts[0]) == 4:  # YYYY/MM/DD
                                return date_str.replace('/', '-')
                            else:  # DD/MM/YYYY
                                return f"{parts[2]}-{parts[1]}-{parts[0]}"
                        return date_str
                    except Exception:
                        return date_str
                
                transactions_df['Date'] = transactions_df['Date'].apply(parse_date)
                debug_print("Used fallback date parsing method")

            # Get companies and their transactions
            companies_with_transactions = get_companies_with_transactions(transactions_df)
            
            if not companies_with_transactions.empty:
                # Calculate performance for each company
                performance_data = calculate_investment_performance(companies_with_transactions)

                if not performance_data.empty:
                    # Add Current Value column
                    performance_data['Current Value (₪)'] = performance_data['Amount (₪)'] + performance_data['Value Change (₪)']
                    
                    # Display summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_invested = performance_data['Amount (₪)'].sum()
                        st.metric("Total Invested", f"₪{total_invested:,.2f}")
                    
                    with col2:
                        total_current = performance_data['Current Value (₪)'].sum()
                        st.metric("Total Current Value", f"₪{total_current:,.2f}")
                    
                    with col3:
                        weighted_return = (performance_data['Percent Change'] * performance_data['Amount (₪)']).sum() / total_invested if total_invested > 0 else 0
                        st.metric("Weighted Return", f"{weighted_return:.2f}%")
                    
                    # Display performance data
                    st.subheader("Investment Performance")
                    
                    # Group by company
                    company_performance = performance_data.groupby(['Company', 'Ticker', 'Exchange']).agg({
                        'Amount (₪)': 'sum',
                        'Value Change (₪)': 'sum',
                        'Current Value (₪)': 'sum',
                        'Percent Change': lambda x: (x * performance_data.loc[x.index, 'Amount (₪)']).sum() / performance_data.loc[x.index, 'Amount (₪)'].sum()
                    }).reset_index()
                    
                    # Configure the DataFrame display
                    st.dataframe(
                        company_performance,
                        column_config={
                            "Company": st.column_config.TextColumn("Company"),
                            "Ticker": st.column_config.TextColumn("Ticker"),
                            "Exchange": st.column_config.TextColumn("Exchange"),
                            "Amount (₪)": st.column_config.NumberColumn("Amount (₪)", format="₪%.2f"),
                            "Value Change (₪)": st.column_config.NumberColumn("Value Change (₪)", format="₪%.2f"),
                            "Current Value (₪)": st.column_config.NumberColumn("Current Value (₪)", format="₪%.2f"),
                            "Percent Change": st.column_config.NumberColumn("Percent Change", format="%.2f%%"),
                        },
                        hide_index=True,
                    )
                    
                    # Add an expander for the transaction-level details
                    with st.expander("Transaction-level Details"):
                        st.dataframe(
                            performance_data,
                            column_config={
                                "Company": st.column_config.TextColumn("Company"),
                                "Ticker": st.column_config.TextColumn("Ticker"), 
                                "Exchange": st.column_config.TextColumn("Exchange"),
                                "Transaction Date": st.column_config.DateColumn("Transaction Date", format="DD/MM/YYYY"),
                                "Amount (₪)": st.column_config.NumberColumn("Amount (₪)", format="₪%.2f"),
                                "Value Change (₪)": st.column_config.NumberColumn("Value Change (₪)", format="₪%.2f"),
                                "Current Value (₪)": st.column_config.NumberColumn("Current Value (₪)", format="₪%.2f"),
                                "Percent Change": st.column_config.NumberColumn("Percent Change", format="%.2f%%"),
                            },
                            hide_index=True,
                        )

                    # Display all transactions
                    st.subheader("All Transactions")
                    
                    # Format date and amount columns - handle dates gently to avoid errors
                    try:
                        transactions_df['Date'] = pd.to_datetime(transactions_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
                    except Exception as e:
                        debug_print(f"Error formatting dates for display: {e}")
                        # If datetime conversion fails, leave as is
                        pass
                        
                    if 'Amount (₪)' in transactions_df.columns:
                        transactions_df['Amount (₪)'] = transactions_df['Amount (₪)'].apply(lambda x: f"₪{x:,.2f}")
                    
                    st.dataframe(transactions_df, use_container_width=True)

            else:
                st.warning("No public companies found in your transactions. We're continuously improving our company detection!")

        except Exception as e:
            st.error(f"An error occurred while processing your statement: {str(e)}")
            debug_print(f"Error processing uploaded file: {e}")

if __name__ == "__main__":
    main()

# Footer
st.markdown('<hr style="border: 0; height: 1px; background: #ccc; margin: 20px 0;">', unsafe_allow_html=True)
st.markdown("<div style='text-align: center;'>Vibe coded with ❤️ by <a href='https://razkaplan.github.io/gtm/' "
"target='_blank'>Raz Kaplan</a> | <a href='https://www.linkedin.com/in/razkaplan/' target='_blank'>LinkedIn</a></div>", unsafe_allow_html=True)