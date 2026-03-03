"""
Data Retrieval Capability
========================
Fetches real-world data (stock prices, exchange rates, etc.)
and creates Excel files with the results.

Strategy:
  1. PRIMARY: Use yfinance for stock/market data (fast, accurate, no LLM needed)
  2. FALLBACK: Call OpenRouter API directly for other data types
"""

import os
import re
import json
import tempfile
import traceback
import pandas as pd
from datetime import datetime, timedelta


# ── Ticker mapping for common indices/stocks ──
TICKER_MAP = {
    "nikkei": "^N225",
    "nikkei 225": "^N225",
    "nikkei stock average": "^N225",
    "sensex": "^BSESN",
    "bse sensex": "^BSESN",
    "nifty": "^NSEI",
    "nifty 50": "^NSEI",
    "s&p 500": "^GSPC",
    "s&p": "^GSPC",
    "dow jones": "^DJI",
    "dow": "^DJI",
    "nasdaq": "^IXIC",
    "ftse": "^FTSE",
    "hang seng": "^HSI",
    "dax": "^GDAXI",
    "apple": "AAPL",
    "aapl": "AAPL",
    "google": "GOOGL",
    "googl": "GOOGL",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "amazon": "AMZN",
    "amzn": "AMZN",
    "meta": "META",
    "nvidia": "NVDA",
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",
    "gold": "GC=F",
    "silver": "SI=F",
    "crude oil": "CL=F",
    "oil": "CL=F",
}


def retrieve_data_and_create_excel(task: str, file_path: str = "auto") -> str:
    """
    Main entry point. Detects what data is needed and fetches it.
    """
    print(f"[DataRetriever] Task: {task}", flush=True)

    task_lower = task.lower()

    # ── Detect ticker ──
    ticker = _detect_ticker(task_lower)
    if ticker:
        return _fetch_stock_data(ticker, task, task_lower, file_path)

    # ── Fallback: Use LLM via direct OpenRouter call ──
    return _fetch_via_llm(task, file_path)


def _detect_ticker(task_lower: str) -> str:
    """Map natural language to a yfinance ticker symbol."""
    import re
    for name, ticker in TICKER_MAP.items():
        if re.search(r'\b' + re.escape(name) + r'\b', task_lower):
            return ticker
    # Check for explicit ticker like "AAPL" or "^N225"
    ticker_match = re.search(r'\b([A-Z]{1,5}(?:-[A-Z]{3})?)\b', task_lower.upper())
    if ticker_match:
        candidate = ticker_match.group(1)
        if candidate not in {"THE", "AND", "FOR", "NEW", "GET", "DAY", "USD", "INR", "EUR", "CREATE", "INPUT", "FILE", "WITH"}:
            return candidate
    return ""


def _parse_days(task_lower: str) -> int:
    """Extract number of days from task."""
    m = re.search(r'(?:previous|past|last)\s+(\d+)\s*(?:day|trading)', task_lower)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:day|trading)', task_lower)
    if m:
        return int(m.group(1))
    return 10  # default


def _parse_column_name(task_lower: str) -> str:
    """Extract custom column name from task."""
    m = re.search(r'column\s*name\s*(?:of|as|:)?\s*["\']?([^"\',.]+)', task_lower)
    if m:
        return m.group(1).strip().title()
    return "Closing Price"


def _fetch_stock_data(ticker: str, task: str, task_lower: str, file_path: str) -> str:
    """Fetch stock data using yfinance."""
    days = _parse_days(task_lower)
    col_name = _parse_column_name(task_lower)

    print(f"[DataRetriever] Fetching {ticker} for {days} days, column='{col_name}'", flush=True)

    try:
        import yfinance as yf

        # Download extra days to account for weekends/holidays
        period = f"{days + 15}d"
        data = yf.download(ticker, period=period, progress=False)

        if data is None or data.empty:
            print(f"[DataRetriever] yfinance returned empty for {ticker}", flush=True)
            return _fetch_via_llm(task, file_path)

        # Get last N trading days of closing prices
        close_col = "Close"
        if close_col not in data.columns:
            # Handle MultiIndex columns from newer yfinance
            if hasattr(data.columns, 'get_level_values'):
                data.columns = data.columns.get_level_values(0)
            if "Close" not in data.columns:
                close_col = data.columns[0]  # fallback to first column

        df = data[[close_col]].tail(days).copy()
        df = df.reset_index()

        # Rename columns
        df.columns = ["Date", col_name]

        # Format date
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        # Round values
        df[col_name] = df[col_name].round(2)

        print(f"[DataRetriever] Got {len(df)} rows from yfinance", flush=True)

        return _save_and_return(df, file_path, ticker)

    except ImportError:
        print("[DataRetriever] yfinance not available, falling back to LLM", flush=True)
        return _fetch_via_llm(task, file_path)
    except Exception as e:
        print(f"[DataRetriever] yfinance error: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return _fetch_via_llm(task, file_path)


def _fetch_via_llm(task: str, file_path: str) -> str:
    """Fallback: Call OpenRouter API directly (bypass DSPy)."""
    print("[DataRetriever] Using direct OpenRouter API call...", flush=True)

    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "❌ No OPENROUTER_API_KEY found in .env"

        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )

        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{
                "role": "user",
                "content": f"""You are a financial data assistant. Provide the requested data as a JSON array.

REQUEST: {task}

RULES:
- Output ONLY a valid JSON array, no extra text
- Each object should have "Date" and the value field
- Use real, recent data. Approximate if necessary.
- Round numbers to 2 decimal places

Example: [{{"Date": "2026-02-14", "Stock Price": 38456.78}}, {{"Date": "2026-02-13", "Stock Price": 38234.56}}]

JSON:"""
            }],
            temperature=0.0,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content.strip()
        print(f"[DataRetriever] LLM response: {raw[:300]}", flush=True)

        # Clean markdown
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        # Find JSON array
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

        data = json.loads(raw)
        if not isinstance(data, list) or len(data) == 0:
            return f"❌ LLM returned invalid data format.\n\nResponse: {raw[:500]}"

        df = pd.DataFrame(data)

        # Round numeric columns
        for col in df.columns:
            if df[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                df[col] = df[col].round(2)

        return _save_and_return(df, file_path, "LLM Data")

    except Exception as e:
        print(f"[DataRetriever] LLM fallback error: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return f"❌ Data retrieval failed: {e}"


def _save_and_return(df: pd.DataFrame, file_path: str, source: str) -> str:
    """Save DataFrame to Excel, open it, return HTML summary."""
    # Determine output path
    cwd = os.getcwd()
    if not file_path or file_path == "auto" or file_path == "retrieved_data.xlsx":
        output_path = os.path.join(cwd, "retrieved_data.xlsx")
    elif os.path.isabs(file_path):
        output_path = file_path
    else:
        output_path = os.path.join(cwd, file_path)

    # Ensure .xlsx extension
    if not output_path.endswith(('.xlsx', '.xls', '.csv')):
        output_path += '.xlsx'

    # Save
    df.to_excel(output_path, index=False, sheet_name="Data")
    print(f"[DataRetriever] Saved {len(df)} rows to {output_path}", flush=True)

    # Open in Excel
    try:
        os.startfile(output_path)
    except Exception:
        pass

    # Build HTML summary
    html_table = df.to_html(classes='generated-table', index=False)

    return (
        f"✅ **Data Retrieved & Saved to Excel!**\n\n"
        f"📊 **{len(df)} records** from {source}\n\n"
        f"{html_table}\n\n"
        f"📁 File: `{output_path}`"
    )
