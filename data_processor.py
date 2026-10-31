import pandas as pd
import numpy as np


def validate_data(price_df: pd.DataFrame) -> pd.DataFrame:

    if not isinstance(price_df, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")

    if price_df.empty:
        raise ValueError("Price data is empty.")

    if "Date" not in price_df.columns:
        raise ValueError("Missing required column: Date")

    if "Close" not in price_df.columns:
        raise ValueError("Missing required column: Close")

    # Work on a copy of the input DataFrame
    price_df = price_df.copy()

    # Convert Date to datetime
    price_df["Date"] = pd.to_datetime(
        price_df["Date"],
        errors="coerce"
    )

    # Convert Close to numeric
    price_df["Close"] = pd.to_numeric(
        price_df["Close"],
        errors="coerce"
    )

    # Check invalid dates
    if price_df["Date"].isna().any():
        raise ValueError("Invalid or missing Date values.")

    # Check invalid prices
    if price_df["Close"].isna().any():
        raise ValueError("Invalid or missing Close values.")

    # Check non-positive prices
    if (price_df["Close"] <= 0).any():
        raise ValueError("Close prices must be greater than zero.")

    # Check infinite prices
    if not np.isfinite(price_df["Close"]).all():
        raise ValueError("Close prices must be finite numbers.")

    
    # Check duplicate dates
    if price_df["Date"].duplicated().any():
        raise ValueError("Duplicate dates found in price data.")
    
    # Sort by date
    price_df = price_df.sort_values(by="Date")

    # Reset row index
    price_df = price_df.reset_index(drop=True)

    return price_df


def filter_data(price_df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:

    # Convert and validate input dates
    try:
        start_date = pd.to_datetime(
            start_date,
            format="%Y-%m-%d",
            exact=True
        )

        end_date = pd.to_datetime(
            end_date,
            format="%Y-%m-%d",
            exact=True
        )

    except (ValueError, TypeError):
        raise ValueError(
            "Dates must be valid and use YYYY-MM-DD format."
        )
    
    if pd.isna(start_date) or pd.isna(end_date):
        raise ValueError(
             "Dates must be valid and use YYYY-MM-DD format."
             )

    # Check date range
    if start_date > end_date:
        raise ValueError("Start date cannot be after end date.")

    # Filter data
    # Use the trading day after or before weekends and holidays
    selected_data = price_df[
        (price_df["Date"] >= start_date) &
        (price_df["Date"] <= end_date)
    ]

    # Check empty result
    if selected_data.empty:
        raise ValueError("No price data found in the selected date range.")

    return selected_data.reset_index(drop=True)


def buy_and_hold(price_df: pd.DataFrame, initial_capital: float) -> pd.DataFrame:

    result = price_df.copy()

    if initial_capital <= 0:
        raise ValueError("Initial capital must be positive.")
    
    #first day trade
    purchase_price = result["Close"].iloc[0]

    # Calculate the number of shares
    shares = initial_capital / purchase_price

    cash = 0.0

    result["Shares"] = shares
    result["Cash"] = cash
    result["Cumulative_Invested"] = initial_capital

    result["Portfolio_Value"] = (
        result["Shares"] * result["Close"] + result["Cash"]
    )

    return result

def dca(price_df: pd.DataFrame, monthly_investment: float) -> pd.DataFrame:

    result = price_df.copy()

    if monthly_investment <= 0:
        raise ValueError("Monthly investment must be positive.")

    shares = 0.0
    cumulative_invested = 0.0
    last_month = None

    shares_history = []
    cash_history = []
    invested_history = []
    portfolio_history = []

    for i in range(len(result)):

        current_date = result["Date"].iloc[i]
        current_price = result["Close"].iloc[i]

        current_month = current_date.to_period("M")

        if current_month != last_month:

            shares_bought = monthly_investment / current_price

            shares = shares + shares_bought

            cumulative_invested = (
                cumulative_invested + monthly_investment
            )

            last_month = current_month

        cash = 0.0

        portfolio_value = shares * current_price + cash

        shares_history.append(shares)
        cash_history.append(cash)
        invested_history.append(cumulative_invested)
        portfolio_history.append(portfolio_value)

    result["Shares"] = shares_history
    result["Cash"] = cash_history
    result["Cumulative_Invested"] = invested_history
    result["Portfolio_Value"] = portfolio_history

    return result


def calculate_performance(result_df: pd.DataFrame) -> dict:

    if result_df.empty:
        raise ValueError("Result DataFrame cannot be empty.")

    final_value = result_df["Portfolio_Value"].iloc[-1]
    total_invested = result_df["Cumulative_Invested"].iloc[-1]

    if total_invested <= 0:
        raise ValueError("Total invested must be positive.")

    profit = final_value - total_invested
    simple_return = profit / total_invested

    index_df = build_return_index(result_df)
    max_drawdown = calculate_max_drawdown(index_df)

    return {
        "Final_Value": float(final_value),
        "Total_Invested": float(total_invested),
        "Profit": float(profit),
        "Simple_Return": float(simple_return),
        "Max_Drawdown": float(max_drawdown)
    }


def calculate_daily_returns(result_df: pd.DataFrame) -> pd.DataFrame:
    
    if result_df.empty:
        raise ValueError("Result DataFrame cannot be empty.")
    
    # Reset index to ensure consistent positional indexing
    daily_df = result_df.copy().reset_index(drop=True)
    
    daily_df["Daily_Investment"] = (
        daily_df["Cumulative_Invested"].diff().fillna(
            daily_df["Cumulative_Invested"].iloc[0]
        )
    )
    
    daily_df["Daily_Return"] = 0.0
    
    for i in range(1, len(daily_df)):
        
        previous_value = daily_df["Portfolio_Value"].iloc[i - 1]

        current_value = daily_df["Portfolio_Value"].iloc[i]

        new_investment = daily_df["Daily_Investment"].iloc[i]

        if previous_value <= 0:
            raise ValueError("Previous portfolio value must be positive.")
        
        daily_return = (
            (current_value - new_investment) / previous_value - 1
        )

        daily_df.loc[i, "Daily_Return"] = daily_return
        
    return daily_df


def build_return_index(result_df: pd.DataFrame) -> pd.DataFrame:

    index_df = calculate_daily_returns(result_df)

    index_df["Return_Index"] = 100.0

    for i in range(1, len(index_df)):

        previous_index = index_df["Return_Index"].iloc[i - 1]

        daily_return = index_df["Daily_Return"].iloc[i]

        current_index = previous_index * (1 + daily_return)

        index_df.loc[i, "Return_Index"] = current_index

    return index_df

def calculate_max_drawdown(index_df: pd.DataFrame) -> float:

    if index_df.empty:
        raise ValueError("Return Index DataFrame cannot be empty.")
    
    historical_peak = index_df["Return_Index"].cummax()
    drawdown = (
        index_df["Return_Index"] - historical_peak
    ) / historical_peak

    max_drawdown = drawdown.min()

    return float(max_drawdown)

def combine_results(results: dict) -> pd.DataFrame:

    # Check the number of assets
    if not 1 <= len(results) <= 3:
        raise ValueError("Select between 1 and 3 assets.")

    combined_df = None

    for ticker, result_df in results.items():

        # Check empty DataFrame
        if result_df.empty:
            raise ValueError(f"{ticker} result cannot be empty.")

        # Select required columns
        asset_df = result_df[
            ["Date", "Portfolio_Value", "Cumulative_Invested"]
        ].copy()

        # Rename columns to identify each asset
        asset_df = asset_df.rename(columns={
            "Portfolio_Value": f"{ticker}_Value",
            "Cumulative_Invested": f"{ticker}_Invested"
        })

        # Merge all dates
        if combined_df is None:
            combined_df = asset_df
        else:
            combined_df = pd.merge(
                combined_df,
                asset_df,
                on="Date",
                how="outer"
            )

    # Sort dates and reset index
    combined_df = combined_df.sort_values("Date").reset_index(drop=True)

    # Fill missing dates using previous available values
    combined_df = combined_df.ffill()

    # Fill values before an asset's first investment with zero
    combined_df = combined_df.fillna(0)

    # Calculate total portfolio value
    value_columns = []
    
    for ticker in results:
        value_columns.append(f"{ticker}_Value")
    
    combined_df["Portfolio_Value"] = combined_df[value_columns].sum(axis=1)

    # Calculate total cumulative investment
    invested_columns = []
    
    for ticker in results:
        invested_columns.append(f"{ticker}_Invested")
    
    combined_df["Cumulative_Invested"] = combined_df[invested_columns].sum(axis=1)
    
    # Keep only the required columns
    combined_df = combined_df[
        ["Date", "Portfolio_Value", "Cumulative_Invested"]
        ]

    return combined_df