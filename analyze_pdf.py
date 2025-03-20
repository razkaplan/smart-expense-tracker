#!/usr/bin/env python3
import pdfplumber
import re
import pandas as pd

def analyze_pdf(pdf_path):
    """Analyze the structure of a PDF file to understand transaction patterns"""
    results = {
        "text_samples": [],
        "possible_patterns": [],
        "merchant_samples": [],
        "page_stats": []
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"PDF has {len(pdf.pages)} pages")
            
            for i, page in enumerate(pdf.pages):
                print(f"\nAnalyzing Page {i+1}:")
                text = page.extract_text()
                results["text_samples"].append(text[:200] + "..." if len(text) > 200 else text)
                
                # Look for date patterns
                dates = re.findall(r'\d{2}/\d{2}/\d{4}|\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}', text)
                
                # Look for potential merchant entries (lines with amounts)
                amounts = re.findall(r'(?:[$₪€£])\s?([\d,]+\.\d{2}|[\d,]+)', text)
                merchants = re.findall(r'[A-Za-z0-9\s\-\']{3,}(?=\s+(?:[$₪€£])\s?[\d,]+\.\d{2}|[\d,]+)', text)
                
                # Look for English text
                english_words = re.findall(r'[A-Za-z]{3,}', text)
                
                results["page_stats"].append({
                    "page": i+1,
                    "total_chars": len(text),
                    "dates_found": len(dates),
                    "amounts_found": len(amounts),
                    "merchants_found": len(merchants),
                    "english_words": len(english_words)
                })
                
                # Display samples of potential merchant names
                merchant_samples = merchants[:5] if merchants else []
                results["merchant_samples"].extend(merchant_samples)
                
                print(f"  - Dates found: {len(dates)}")
                print(f"  - Amount patterns found: {len(amounts)}")
                print(f"  - Potential merchants found: {len(merchants)}")
                print(f"  - English words found: {len(english_words)}")
                if merchant_samples:
                    print(f"  - Sample merchants: {', '.join(merchant_samples)}")
    
    except Exception as e:
        print(f"Error analyzing PDF: {e}")
    
    return results

if __name__ == "__main__":
    pdf_path = "credit card example.pdf"
    results = analyze_pdf(pdf_path)
    
    print("\n=== ANALYSIS SUMMARY ===")
    print(f"Total pages: {len(results['page_stats'])}")
    print(f"Total potential merchants: {len(results['merchant_samples'])}")
    print("\nSample potential merchants:")
    for merchant in results['merchant_samples'][:10]:
        print(f"  - {merchant}")
