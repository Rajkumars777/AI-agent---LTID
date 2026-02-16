import requests
import pandas as pd
import os
from pathlib import Path

# Constants
API_URL = "http://localhost:8000/api/web-orchestrator"
NIKKEI_URL = "https://www.google.com/finance/quote/NI225:INDEXNIKKEI" # Using Google Finance as proxy for Nikkei index which is easier to scrape reliably for demo
SELECTOR = ".YMlKec.fxKbKc" # Class for the price on Google Finance
EXCEL_PATH = Path("sales_reports/MarketConditions.xlsx") # Mock path
EXCEL_DIR = Path("sales_reports")

def ensure_excel():
    """Creates the dummy excel file if it doesn't exist."""
    EXCEL_DIR.mkdir(exist_ok=True)
    if not EXCEL_PATH.exists():
        df = pd.DataFrame({"Date": [], "Nikkei Stock Average": []})
        df.to_excel(EXCEL_PATH, index=False)
        print(f"📄 Created dummy Excel: {EXCEL_PATH}")
    else:
        print(f"📄 Found existing Excel: {EXCEL_PATH}")

def get_stock_price():
    """Calls the backend to scrape the price."""
    print(f"🌐 Scraping price from {NIKKEI_URL}...")
    try:
        response = requests.post(API_URL, json={
            "url": NIKKEI_URL,
            "action": "scrape_text",
            "selector": SELECTOR
        })
        response.raise_for_status()
        result = response.json()
        if result.get("data") and "text" in result["data"]:
            price_text = result["data"]["text"]
            # Clean price (remove commas, currency symbols)
            price_clean = float(price_text.replace(",", "").replace("¥", ""))
            print(f"💰 Scraped Price: {price_clean}")
            return price_clean
        else:
            print(f"❌ Failed to scrape: {result.get('status')}")
            return None
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

def write_to_excel(price):
    """Writes the price to the Excel file."""
    try:
        # Load existing
        if EXCEL_PATH.exists():
            df = pd.read_excel(EXCEL_PATH)
        else:
            df = pd.DataFrame({"Date": [], "Nikkei Stock Average": []})
        
        # Add new row
        from datetime import date
        new_row = pd.DataFrame([{"Date": date.today(), "Nikkei Stock Average": round(price, 2)}])
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Save
        df.to_excel(EXCEL_PATH, index=False)
        print(f"✅ Written {price} to {EXCEL_PATH}")
        
    except Exception as e:
        print(f"❌ Excel Error: {e}")

if __name__ == "__main__":
    ensure_excel()
    price = get_stock_price()
    if price:
        write_to_excel(price)
