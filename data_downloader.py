from pathlib import Path
import pandas as pd
import yfinance as yf
from data_processor import validate_data, filter_data
import pandas_market_calendars as mcal

SUPPORTED_TICKERS = ("SPY", "QQQ", "TQQQ", "GLD", "IEF")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
NYSE = mcal.get_calendar("NYSE")


def check_date_coverage(df: pd.DataFrame, start_date: str, end_date: str) -> None:

    trading_days = NYSE.valid_days(
        start_date=start_date,
        end_date=end_date
    ).tz_localize(None)

    if len(trading_days) == 0:
        raise ValueError("No trading days in selected period")

    actual_dates = pd.DatetimeIndex(df["Date"]).normalize()

    missing_days = trading_days.difference(actual_dates)

    if len(missing_days) > 0:
        raise ValueError(
            f"Missing trading data: {missing_days[0].date()}"
        )


def get_historical_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:

    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"Unsupported ticker: {ticker}")

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    if start > end:
        raise ValueError("Start date must not be after end date")

    end_exclusive = (
        end + pd.Timedelta(days=1)
    ).strftime("%Y-%m-%d")

    # Get online data
    try:
        df = yf.download(
            ticker,
            start=start_date,
            end=end_exclusive,
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            raise ValueError("Online download returned empty data")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Close"]].reset_index()
        df = df[["Date", "Close"]]

        df = validate_data(df)
        df = filter_data(df, start_date, end_date)

        if df.empty:
            raise ValueError("No trading data available")

        check_date_coverage(df, start_date, end_date)

        return df

    # Get offline data
    except Exception as error:
        print(f"Online download failed for {ticker}: {error}")
        print("Trying local CSV backup...")

        return load_backup_data(
            ticker,
            start_date,
            end_date
        )


def download_backup_data() -> None:

    start_date = "2016-10-31"
    end_date = "2026-10-30"

    DATA_DIR.mkdir(exist_ok=True)

    for ticker in SUPPORTED_TICKERS:
        print(f"Downloading {ticker}...")

        df = get_historical_data(
            ticker,
            start_date,
            end_date
        )

        csv_path = DATA_DIR / f"{ticker}.csv"

        df.to_csv(csv_path, index=False)

        print(f"Saved {ticker}: {len(df)} rows")


def load_backup_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:

    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"Unsupported ticker: {ticker}")

    csv_path = DATA_DIR / f"{ticker}.csv"

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Backup file not found: {csv_path}"
        )

    try:
        df = pd.read_csv(
            csv_path,
            parse_dates=["Date"]
        )
    except Exception as error:
        raise ValueError(
            f"Cannot read backup file for {ticker}: {error}"
        ) from error

    if df.columns.tolist() != ["Date", "Close"]:
        raise ValueError(
            f"Invalid CSV columns for {ticker}"
        )
    
    df = validate_data(df)

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    if pd.isna(start) or pd.isna(end):
        raise ValueError("Invalid date")

    if start > end:
        raise ValueError("Start date must not be after end date")

    df = filter_data(df, start_date, end_date)

    check_date_coverage(df, start_date, end_date)

    return df