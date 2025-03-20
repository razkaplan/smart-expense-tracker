#!/usr/bin/env python3
import pdfplumber
import pandas as pd
import re
import unicodedata
from bidi.algorithm import get_display
from arabic_reshaper import reshape
import streamlit as st

def extract_tables_from_pdf(pdf_path):
    """Extract tables from PDF using pdfplumber"""
    all_tables = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF has {len(pdf.pages)} pages")
        
        for i, page in enumerate(pdf.pages):
            print(f"\nProcessing Page {i+1}:")
            
            # Extract tables with various settings
            tables = page.extract_tables(table_settings={"vertical_strategy": "text", 
                                                        "horizontal_strategy": "text"})
            if tables:
                print(f"  - Found {len(tables)} tables")
                all_tables.extend(tables)
            else:
                print("  - No tables found with standard settings")
                
                # Try with more aggressive settings
                tables = page.extract_tables(table_settings={"vertical_strategy": "lines", 
                                                           "horizontal_strategy": "lines"})
                if tables:
                    print(f"  - Found {len(tables)} tables with alternative settings")
                    all_tables.extend(tables)
                    
            # Extract text
            text = page.extract_text()
            print(f"  - Page text length: {len(text)}")
            
            # Look for specific patterns
            date_amount_patterns = re.findall(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
            print(f"  - Found {len(date_amount_patterns)} date-amount patterns")
            
            # Find English text
            latin_segments = re.findall(r'[A-Za-z][A-Za-z\s]+', text)
            print(f"  - Found {len(latin_segments)} Latin/English segments")
            if latin_segments:
                print(f"  - Sample English segments: {latin_segments[:5]}")
    
    return all_tables

def is_probably_english(text):
    """Check if text is likely English (Latin script)"""
    # Count characters in different scripts
    latin_chars = sum(1 for c in text if c.isalpha() and 'A' <= c.upper() <= 'Z')
    hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF' or '\uFB1D' <= c <= '\uFB4F')
    
    # If string has more Latin than Hebrew characters and at least 3 Latin chars, it's likely English
    return latin_chars > hebrew_chars and latin_chars >= 3

def extract_english_segments(text):
    """Extract segments that are likely English words or phrases"""
    # This pattern looks for sequences of Latin characters surrounded by word boundaries
    pattern = r'(?:^|[^\w])([A-Za-z][A-Za-z\s\.]+)(?:[^\w]|$)'
    matches = re.findall(pattern, text)
    
    # Filter short segments and common non-merchant terms
    filtered_matches = []
    ignore_terms = {'vs', 'bit', 'pay', 'card', 'credit', 'debit', 'visa', 'mastercard', 'amex'}
    
    for match in matches:
        match = match.strip()
        if len(match) >= 4 and match.lower() not in ignore_terms:
            filtered_matches.append(match)
    
    return filtered_matches

def extract_transactions(pdf_path):
    """Extract transactions with focus on English merchant names"""
    all_transactions = []
    english_merchants = []
    raw_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Use more aggressive text extraction settings
            text = page.extract_text(
                x_tolerance=1,
                y_tolerance=1,
                layout=True,
                x_density=7.25,
                y_density=13
            )
            raw_text += text + "\n"
            
            # Extract each line
            lines = text.split('\n')
            
            # First pass: Extract all potential English segments
            for line in lines:
                english_segments = extract_english_segments(line)
                for segment in english_segments:
                    if segment:
                        english_merchants.append(segment)
                        print(f"Found English text: {segment}")
            
            # Normalize text for better processing
            raw_text = unicodedata.normalize('NFKC', raw_text)
            raw_text = ' '.join(raw_text.split())  # Remove extra spaces
            
            # Improved regex pattern for mixed Hebrew/English text
            pattern = r'(\d{2}/\d{2}/\d{4}|\d{4}[-/]\d{2}[-/]\d{2})\s+([\u0590-\u05FF\uFB1D-\uFB4F\w\s\.\,\-]+?)\s+[₪$€£]\s?([\d,.]+)'
            
            # Process each line looking for transaction patterns
            for line in lines:
                # Skip lines that are too short
                if len(line) < 10:
                    continue
                    
                # Look for date patterns followed by transaction info
                date_matches = re.findall(r'(\d{2}/\d{2}/\d{4})', line)
                
                if date_matches:
                    date = date_matches[0]
                    # Split the line into segments by space
                    segments = line.split()
                    date_index = segments.index(date) if date in segments else -1
                    
                    if date_index >= 0 and len(segments) > date_index + 1:
                        # Look for amount pattern (usually at the end)
                        amount_matches = re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', line)
                        if amount_matches:
                            amount = amount_matches[-1]  # Take the last number as amount
                            
                            # Extract merchant name (everything between date and amount)
                            merchant_text = ' '.join(segments[date_index+1:-1])
                            
                            # Check if merchant name contains English
                            for segment in segments[date_index+1:-1]:
                                if is_probably_english(segment) and len(segment) > 2:
                                    english_merchants.append(segment)
                                    print(f"Found English merchant: {segment}")
                                    
                            # Add transaction
                            all_transactions.append({
                                'Date': date,
                                'Merchant': merchant_text,
                                'Amount': amount
                            })
    
    # Print results
    print(f"\nExtracted {len(all_transactions)} transactions")
    print(f"Found {len(english_merchants)} potential English merchant names")
    print("Sample English merchants:")
    
    # Convert list to a set and back to a list to remove duplicates
    english_merchants_list = list(set(english_merchants))
    if english_merchants_list:
        for merchant in english_merchants_list[:10]:
            print(f"  - {merchant}")
    
    return all_transactions, english_merchants_list

if __name__ == '__main__':
    pdf_path = "credit card example.pdf"
    
    print("=== ANALYZING PDF TABLES ===")
    tables = extract_tables_from_pdf(pdf_path)
    
    print("\n=== EXTRACTING TRANSACTIONS ===")
    transactions, english_merchants = extract_transactions(pdf_path)
    
    print("\n=== RESULTS ===")
    if transactions:
        df = pd.DataFrame(transactions)
        print(df.head())
