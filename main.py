import pandas as pd
from datetime import datetime
import json
from pathlib import Path
import matplotlib.pyplot as plt
from data_downloader import (
    SUPPORTED_TICKERS,
    get_historical_data
)
from data_processor import (
    validate_data,
    filter_data,
    buy_and_hold,
    dca,
    combine_results,
    calculate_performance
)

def display_welcome():
    print("=" * 48)
    print("Investment Strategy Backtesting Simulator")
    print("=" * 48)

    print("\nAvailable ETFs:")

    etf_descriptions = {
        "SPY": "S&P 500",
        "QQQ": "Nasdaq-100",
        "TQQQ": "3x Leveraged Nasdaq-100",
        "GLD": "Gold",
        "IEF": "US Treasury Bonds"
    }

    for number, ticker in enumerate(SUPPORTED_TICKERS, start=1):
        print(f"{number}. {ticker} - {etf_descriptions[ticker]}")


def get_asset_count():
    while True:
        try:
            count = int(input("\nHow many assets? (1-3): "))

            if 1 <= count <= 3:
                return count
            else:
                print("Please enter a number between 1 and 3.")

        except ValueError:
            print("Invalid input. Please enter an integer.")

def get_selected_assets(count:int) -> list[str]:
    selected_assets = []

    while len(selected_assets) < count:
        number = len(selected_assets) + 1

        ticker = input(f"Select ETF {number}: ").strip().upper()

        if ticker not in SUPPORTED_TICKERS:
            print("Invalid ETF. Please choose from the available list.")

        elif ticker in selected_assets:
            print("This ETF has already been selected.")

        else:
            selected_assets.append(ticker)

    return selected_assets


def get_strategy(ticker: str) -> str:
    # Ask the user to choose an investment strategy
    while True:
        print(f"\nSelect Strategy for {ticker}:")
        print("1. Buy and Hold")
        print("2. DCA")

        choice = input("Choice: ").strip()

        if choice == "1":
            return "buy_and_hold"

        elif choice == "2":
            return "dca"

        else:
            print("Invalid choice. Please enter 1 or 2.")

def get_investment_amount(strategy: str) -> float:
    # Set the minimum investment amount
    min_amount = 500

    # Use different prompts based on the selected strategy
    if strategy == "buy_and_hold":
        prompt = "Initial Capital (USD): "
    else:
        prompt = "Monthly Investment (USD): "

    # Keep asking until a valid positive amount is entered
    while True:
        try:
            amount = float(input(prompt))

            if min_amount <= amount < float("inf"):
                return amount
            else:
                print(f"Amount must be at least ${min_amount:,.2f} USD.")

        except ValueError:
            print("Invalid input. Please enter a number.")


def configure_assets(selected_assets: list[str]) -> list[dict]:
    assets = []

    # Configure each selected ETF separately
    for ticker in selected_assets:
        strategy = get_strategy(ticker)
        amount = get_investment_amount(strategy)

        # Store the configuration of the current ETF
        asset = {
            "ticker": ticker,
            "strategy": strategy,
            "amount": amount
        }

        assets.append(asset)

    return assets


def get_backtest_dates() -> tuple[str, str]:
    # Keep asking until both dates are valid
    while True:
        start_date = input(
            "\nStart Date (YYYY-MM-DD): "
        ).strip()

        end_date = input(
            "End Date (YYYY-MM-DD): "
        ).strip()

        try:
            # Validate date format and actual calendar dates
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            # Require exactly YYYY-MM-DD format
            if (start.strftime("%Y-%m-%d") != start_date or
                    end.strftime("%Y-%m-%d") != end_date):
                print("Dates must use YYYY-MM-DD format.")
                continue

            # Check the chronological order
            if start > end:
                print("Start date cannot be after end date.")
                continue

            # Return the original strings for existing modules
            return start_date, end_date

        except ValueError:
            print("Invalid date. Please use YYYY-MM-DD format.")

def display_configuration(config: dict) -> None:
    # Display the backtest configuration before execution
    print("\n" + "=" * 48)
    print("Backtest Configuration")
    print("=" * 48)

    print(
        f"\nBacktest Period: "
        f"{config['start_date']} to {config['end_date']}"
    )

    print("\nSelected Assets:")

    # Display the investment settings for each ETF
    for number, asset in enumerate(config["assets"], start=1):
        ticker = asset["ticker"]
        strategy = asset["strategy"]
        amount = asset["amount"]

        print(f"\n{number}. {ticker}")

        if strategy == "buy_and_hold":
            print("   Strategy: Buy and Hold")
            print(f"   Initial Capital: ${amount:,.2f} USD")

        elif strategy == "dca":
            print("   Strategy: DCA")
            print(f"   Monthly Investment: ${amount:,.2f} USD")

def run_single_asset(asset: dict, start_date: str, end_date: str) -> pd.DataFrame:
    # Read the selected asset configuration
    ticker = asset["ticker"]
    strategy = asset["strategy"]
    amount = asset["amount"]

    print(f"\nProcessing {ticker}...")

    # Download historical ETF price data
    price_df = get_historical_data(
        ticker,
        start_date,
        end_date
    )

    # Validate and filter historical prices
    price_df = validate_data(price_df)
    price_df = filter_data(price_df, start_date, end_date)

    # Execute the selected investment strategy
    if strategy == "buy_and_hold":
        result_df = buy_and_hold(price_df, amount)

    elif strategy == "dca":
        result_df = dca(price_df, amount)

    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    print(f"{ticker} backtest completed.")

    return result_df



def run_backtest(config: dict) -> tuple[pd.DataFrame, dict]:
    # Store the backtest result of each selected ETF
    results = {}

    start_date = config["start_date"]
    end_date = config["end_date"]

    print("\nRunning backtest...")

    # Step 1: Run the backtest for each selected ETF
    for asset in config["assets"]:
        ticker = asset["ticker"]

        # Get the individual ETF backtest result
        result_df = run_single_asset(
            asset,
            start_date,
            end_date
        )

        # Store the result using the ticker as the key
        results[ticker] = result_df

    print("\nAll asset backtests completed.")

    # Step 2: Combine all ETF results into one portfolio
    portfolio_df = combine_results(results)

    # Step 3: Calculate overall portfolio performance
    performance = calculate_performance(portfolio_df)

    print("Portfolio performance calculated successfully.")

    return portfolio_df, performance


def display_results(performance: dict) -> None:
    # Read the calculated portfolio performance
    final_value = performance["Final_Value"]
    total_invested = performance["Total_Invested"]
    profit = performance["Profit"]
    simple_return = performance["Simple_Return"]
    max_drawdown = performance["Max_Drawdown"]

    # Display portfolio performance
    print("\n" + "=" * 48)
    print("Portfolio Performance")
    print("=" * 48)

    print(f"\nFinal Portfolio Value: ${final_value:,.2f}")
    print(f"Total Invested:         ${total_invested:,.2f}")
    print(f"Profit / Loss:          {profit:+,.2f} USD")
    print(f"Simple Return:          {simple_return:+.2%}")
    print(f"Maximum Drawdown:       {max_drawdown:.2%}")


def plot_results(portfolio_df: pd.DataFrame) -> None:
    # Read dates and portfolio values
    dates = portfolio_df["Date"]
    portfolio_values = portfolio_df["Portfolio_Value"]
    invested = portfolio_df["Cumulative_Invested"]

    # Create the figure
    plt.figure(figsize=(10, 6))

    # Plot the portfolio value
    plt.plot(
        dates,
        portfolio_values,
        label="Portfolio Value",
        color="blue",
        linewidth=2
    )

    # Plot the cumulative invested capital
    plt.plot(
        dates,
        invested,
        label="Cumulative Invested",
        color="orange",
        linestyle="--",
        linewidth=2
    )

    # Add chart title and axis labels
    plt.title("Portfolio Backtest Performance")
    plt.xlabel("Date")
    plt.ylabel("Value (USD)")

    # Add grid and legend
    plt.grid(True, alpha=0.3)
    plt.legend()

    # Adjust layout to prevent overlapping labels
    plt.tight_layout()

    # Display the chart
    plt.show()


def save_history(config: dict, performance: dict) -> None:
    # Define the history file path relative to main.py
    history_path = Path(__file__).resolve().parent / "data" / "history.json"

    # Create the data folder if it does not exist
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing history or create an empty list
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as file:
            history = json.load(file)
        
        # Check that history data has the expected list format
        if not isinstance(history, list):
            raise ValueError("Invalid history file format.")
    else:
        history = []

    # Create a new record for the current backtest
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config": config,
        "performance": performance
    }

    # Add the new backtest record
    history.append(record)

    # Keep only the 5 most recent records
    history = history[-5:]

    # Save the updated history to the JSON file
    with open(history_path, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)


    print("\nBacktest history saved successfully.")


def view_history() -> None:
    # Define the history file path
    history_path = Path(__file__).resolve().parent / "data" / "history.json"

    print("\n" + "=" * 48)
    print("Backtest History")
    print("=" * 48)

    # Check whether the history file exists
    if not history_path.exists():
        print("\nNo backtest history found.")
        return

    # Read saved backtest records
    try:
        with open(history_path, "r", encoding="utf-8") as file:
            history = json.load(file)

    except (OSError, json.JSONDecodeError) as error:
        print(f"\nCould not read history: {error}")
        return

    # Check whether history contains valid records
    if not isinstance(history, list):
        print("\nInvalid history file format.")
        return

    if not history:
        print("\nNo backtest history found.")
        return

    # Display each saved backtest record
    try:
        for number, record in enumerate(history, start=1):
            print(f"\nRecord {number}")
            print(f"Date: {record['timestamp']}")
        
            config = record["config"]
            performance = record["performance"]
        
            print(
                    f"Period: {config['start_date']} "
                    f"to {config['end_date']}"
                )
        
            print("\nAssets:")
        
            # Display asset configurations
            for asset in config["assets"]:
                ticker = asset["ticker"]
                strategy = asset["strategy"]
                amount = asset["amount"]
        
                if strategy == "buy_and_hold":
                    print(f"  {ticker} - Buy and Hold - ${amount:,.2f}")
        
                elif strategy == "dca":
                    print(f"  {ticker} - DCA - ${amount:,.2f}/month")
        
            # Display saved performance
            print(f"\nFinal Value:      ${performance['Final_Value']:,.2f}")
            print(f"Total Invested:   ${performance['Total_Invested']:,.2f}")
            print(f"Profit / Loss:    {performance['Profit']:+,.2f} USD")
            print(f"Simple Return:    {performance['Simple_Return']:+.2%}")
            print(f"Maximum Drawdown: {performance['Max_Drawdown']:.2%}")
        
            print("\n" + "-" * 48)
            
    except (KeyError, TypeError, ValueError) as error:
        print(f"\nInvalid history record: {error}")
        return
    

def run_new_backtest() -> None:
    # Display welcome message
    display_welcome()

    # Step 1: Select ETFs
    count = get_asset_count()
    selected_assets = get_selected_assets(count)

    # Step 2: Configure investment strategies and amounts
    assets = configure_assets(selected_assets)

    # Step 3: Get the backtest period
    start_date, end_date = get_backtest_dates()

    # Step 4: Store all user inputs in one dictionary
    config = {
        "assets": assets,
        "start_date": start_date,
        "end_date": end_date
    }

    # Step 5: Display configuration summary
    display_configuration(config)


    # Step 6: Run the backtest
    try:
        portfolio_df, performance = run_backtest(config)

    except Exception as error:
        # Show a user-friendly message if the backtest fails
        print(f"\nBacktest failed: {error}")
        print("Please check your inputs or historical data availability.")
        return

    # Step 7: Display portfolio performance
    display_results(performance)

    # Step 8: Save successful backtest history
    try:
        save_history(config, performance)

    except (OSError, ValueError, TypeError) as error:
        # History failure should not prevent the chart from displaying
        print(f"\nCould not save backtest history: {error}")
    
    # Step 9: Display portfolio visualization
    try:
        plot_results(portfolio_df)
    except Exception as error:
        # A plotting failure should not invalidate the backtest
        print(f"\nCould not display the chart: {error}")


def main():
    # Keep the program running until the user chooses to exit
    while True:
        print("\n" + "=" * 48)
        print("Investment Strategy Backtesting Simulator")
        print("=" * 48)

        # Display main menu options
        print("\nMain Menu:")
        print("1. Run New Backtest")
        print("2. View Backtest History")
        print("3. Exit")

        choice = input("\nEnter your choice (1-3): ").strip()


        if choice == "1":
            # Start a new backtest
            run_new_backtest()

        elif choice == "2":
            # Display previously saved backtests
            view_history()

        elif choice == "3":
            # Exit the program
            print("\nThank you for using the simulator.")
            break

        else:
            # Ask again if the input is invalid
            print("\nInvalid choice. Please enter 1, 2 or 3.")

if __name__ == "__main__":
    main()