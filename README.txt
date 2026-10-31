# COMP9001 FINAL PROJECT
# Investment Strategy Backtesting Simulator

## 1. Project Overview

Investment Strategy Backtesting Simulator is a Python-based application developed for the COMP9001 Python Foundations final project at the University of Sydney.

The application allows users to simulate investment strategies using historical market data from selected Exchange-Traded Funds (ETFs). Users can configure individual investment strategies, specify investment amounts and historical date ranges, and evaluate the performance of a combined investment portfolio.

The program retrieves historical price data from Yahoo Finance and supports local CSV backups when online data retrieval or validation fails.

Two interfaces are available: the original command-line interface (CLI), launched with `python main.py`, and a Tkinter graphical user interface (GUI), launched with `python gui.py`. Both reuse the same backtesting engine and history format.

This application is designed for educational purposes. It does not execute real trades, manage investment accounts, or provide financial advice.

## 2. Key Features

- **Desktop GUI:** Configure backtests, view results and embedded charts, and browse saved history in one Tkinter window.
- **Multiple Asset Selection:** Select between one and three different ETFs for a portfolio.
- **Investment Strategy Configuration:** Independently configure Buy and Hold or Dollar-Cost Averaging (DCA) for each selected asset.
- **Custom Investment Amounts:** Specify initial capital or monthly investment amounts in USD.
- **Historical Backtesting:** Select a custom start date and end date for historical simulations.
- **Portfolio Analysis:** Combine individual asset results to calculate overall portfolio performance.
- **Performance Metrics:** Calculate profit/loss, simple return and maximum drawdown.
- **Portfolio Visualization:** Display portfolio value and cumulative invested capital over time.
- **Backtest History:** Save and review the five most recent successful backtests.
- **Data Validation and Backup:** Validate downloaded market data and use local CSV backups when necessary.

## 3. Supported Assets

The application currently supports five ETFs:

| Ticker | Asset Description |
|---|---|
| SPY | S&P 500 |
| QQQ | Nasdaq-100 |
| TQQQ | 3x Leveraged Nasdaq-100 |
| GLD | Gold |
| IEF | US Treasury Bonds |

Users can select between one and three unique assets for each backtest.

## 4. Investment Strategies

Each selected asset can use one of the following strategies.

### 4.1 Buy and Hold

- Invest the entire initial capital on the first available trading day.
- Calculate the number of shares purchased based on the initial investment and purchase price.
- Hold the shares throughout the selected backtesting period.
- Calculate portfolio value using historical closing prices.

### 4.2 Dollar-Cost Averaging (DCA)

- Invest a fixed amount of money once per calendar month.
- Make each monthly investment on the first available trading day of that month within the selected backtesting period.
- Calculate the number of shares purchased using the investment amount and corresponding closing price.
- Accumulate shares throughout the investment period.

The number of monthly investments is determined by the number of calendar months covered by the selected date range.

**Investment Requirements:**
- Minimum initial capital for Buy and Hold: USD 500.
- Minimum monthly investment for DCA: USD 500.

The application supports fractional shares in its calculations.

## 5. Portfolio Performance Metrics

After completing the individual asset simulations, the application combines their results into an overall portfolio.

The following performance metrics are calculated:

| Metric | Description |
|---|---|
| Final Portfolio Value | Total portfolio value at the end of the backtesting period. |
| Total Invested | Total capital contributed throughout the investment period. |
| Profit / Loss | Difference between final portfolio value and total invested capital. |
| Simple Return | Profit or loss divided by total invested capital. |
| Maximum Drawdown | Largest percentage decline from a previous peak in the cash-flow-adjusted return index. |

Maximum drawdown is calculated using a return index that adjusts for additional investment contributions. This helps separate investment performance from changes caused by new capital being added to the portfolio.

Simple Return is not an annualised return.

## 6. Portfolio Visualization

The application uses Matplotlib to display a portfolio performance chart.

The chart contains two lines:

- **Portfolio Value:** The total market value of all selected assets over time.
- **Cumulative Invested:** The total amount of capital invested over time.

This visualization allows users to compare portfolio growth against the amount of money contributed.

In the GUI, the chart is embedded in the results page using Matplotlib's TkAgg canvas. Its toolbar supports navigation and saving the chart. The CLI retains its separate Matplotlib chart window.

## 7. Data Source and Management

### 7.1 Data Source

Historical market data is obtained from Yahoo Finance through the `yfinance` Python library.

The application requests adjusted historical prices using automatic price adjustment (`auto_adjust=True`).

The downloaded data is processed into two columns:

- `Date`: Historical trading date.
- `Close`: Adjusted closing price.

### 7.2 Data Validation

The application validates historical price data before performing a backtest.

Validation includes:

- Checking required columns and data types.
- Checking for invalid or missing dates and prices.
- Ensuring closing prices are positive and finite.
- Detecting duplicate dates.
- Sorting records chronologically.
- Checking historical data coverage against the NYSE trading calendar.

The `pandas_market_calendars` library is used to identify expected NYSE trading days and detect missing trading data.

### 7.3 Local CSV Backup

The project includes local CSV backup files for all five supported ETFs.

The backup files are stored in the `data` directory.

If an online download fails or the downloaded data does not pass validation, the application attempts to load the corresponding local CSV file.

Local backup data is also validated and checked against the selected date range and expected trading days before being used.

The backup-generation function is configured to download historical data from 2016-10-31 to 2026-10-30.

The application does not enforce a fixed ten-year limit. Successful backtesting depends on the availability and coverage of online or local historical data.

**Important:** Local CSV backups are not automatically refreshed after successful online downloads. The backup-generation function is separate from the normal backtesting workflow.

### 7.4 Network Requirements

An internet connection is required for online historical data retrieval.

However, local CSV backups allow the application to perform backtests without successfully downloading data online, provided that the selected date range is fully covered by the available backup data.

The availability of online data may be affected by network connectivity, Yahoo Finance service availability and data limitations.

## 8. Backtest History

The application supports saving and reviewing previous backtests.

Successful backtest records are stored in:

`data/history.json`

Each record contains:

- Backtest timestamp.
- Selected assets and investment strategies.
- Investment amounts.
- Backtesting date range.
- Portfolio performance metrics.

The application retains a maximum of five recent backtest records.

In the GUI, choose Backtest History to see the latest records first. Select a row to view its timestamp, assets, strategies, investment amounts, date range and all five performance metrics. Refresh reloads the file.

The GUI handles missing files and empty history without crashing. A blank placeholder file is treated as empty and initialized as a JSON list when a successful backtest is saved. Invalid non-empty JSON or malformed records produce an error message. Existing invalid content is not automatically overwritten. If saving fails, the GUI still displays the calculated results and reports that history was not saved.

## 9. Project Structure

```text
Investment Strategy Backtesting Simulator/
│
├── main.py
├── gui.py
├── data_processor.py
├── data_downloader.py
├── requirements.txt
├── README.txt
│
└── data/
    ├── GLD.csv
    ├── IEF.csv
    ├── QQQ.csv
    ├── SPY.csv
    ├── TQQQ.csv
    └── history.json
```

**Main program modules:**

- `gui.py`: Provides the Tkinter main menu, backtest configuration and validation, background execution, performance results, embedded Matplotlib chart and read-only history viewer. It imports `run_backtest` and `save_history` from `main.py` without starting the CLI.
- `main.py`: Provides the command-line interface, collects user inputs, coordinates backtesting, displays results, generates charts and manages backtest history.
- `data_processor.py`: Handles historical data validation, date filtering, investment strategy simulations, portfolio aggregation and performance calculations.
- `data_downloader.py`: Retrieves historical market data from Yahoo Finance, validates trading-day coverage and manages local CSV backups.

## 10. Requirements and Dependencies

### Software Requirements

- Python 3. GUI verification used Python 3.14.6.
- Internet connection for online historical data retrieval.
- A terminal or command-line environment for installation and startup.
- A local desktop display and a Python installation with Tcl/Tk support for the GUI.

The application is designed to run in a local Python environment outside the University of Sydney Ed environment.

### Third-Party Libraries

The following third-party packages are required:

| Package | Purpose |
|---|---|
| pandas | Historical data processing and DataFrame operations. |
| numpy | Numerical calculations and data validation. |
| matplotlib | Portfolio performance visualization, including the embedded TkAgg chart in the GUI. |
| yfinance | Historical market data retrieval. |
| pandas_market_calendars | Trading calendar and market-day validation. |

The GUI also uses standard-library modules including `tkinter`, `tkinter.ttk`, `tkinter.messagebox`, `threading`, `queue` and `math`, alongside existing modules such as `datetime`, `json` and `pathlib`. These are not pip dependencies.

Tkinter is normally included with the Windows Python installer. Some Python distributions require Tcl/Tk support to be installed separately. Do not add `tkinter` or `tk` to requirements.txt. The GUI adds no new third-party packages beyond the existing dependencies.

## 11. Installation and Execution

### Step 1: Install Python

Install Python 3 if it is not already available. For GUI use, include Tcl/Tk support.

### Step 2: Open the Project Directory

Open a terminal and navigate to the project folder containing `main.py`, the complete `gui.py` implementation and `requirements.txt`.

### Step 3: Install Dependencies

Run the following command:

```bash
python -m pip install -r requirements.txt
```

### Step 4: Check Tkinter Support

Run:

```bash
python -m tkinter
```

A small demonstration window should open. Close it before launching the simulator. If the command fails because Tkinter is unavailable, enable Tcl/Tk support in your Python installation.

### Step 5: Launch the GUI or CLI

To launch the graphical interface:

```bash
python gui.py
```

To launch the original command-line interface:

```bash
python main.py
```

Run these commands from the project directory. The GUI does not launch the CLI menu, and the CLI remains available independently.

### Step 6: Use the GUI

The main menu has three buttons: New Backtest, Backtest History and Exit.

To run a backtest:

1. Choose New Backtest and select one, two or three assets.
2. Choose a different ETF for each asset and select Buy and Hold or DCA.
3. Enter at least USD 500 for each asset. Buy and Hold uses Initial Capital; DCA uses Monthly Investment. A minimum-investment hint appears below each amount field.
4. Enter valid Start Date and End Date values in YYYY-MM-DD format. The start date cannot be later than the end date.
5. Choose Run Backtest and confirm the configuration.
6. Wait for completion. The progress indicator shows activity, not an estimated percentage. Downloads and calculations run in a background thread so the window can remain responsive.
7. Review the five performance metrics and the embedded Portfolio Value / Cumulative Invested chart.
8. Choose Edit Configuration, Backtest History or Back to Main Menu as needed.

The GUI reports invalid inputs and backtest errors in message boxes. It prevents duplicate submissions and exit during an active backtest or save. Configuration inputs are preserved when navigating between pages. On smaller windows, use the configuration scrollbar or mouse wheel to reach the action buttons.

Successful results are saved with the existing save_history function, retaining the five most recent records. A history-save failure does not discard the calculated results.

To use the CLI instead, select Run New Backtest, View Backtest History or Exit from its numbered menu. The asset, strategy, amount and date requirements are the same.

### GUI Troubleshooting

- If python gui.py immediately exits without opening a window, check that gui.py contains the complete implementation and is not an empty placeholder.
- If a required package is missing, install requirements.txt using the same Python interpreter used to launch the application.
- The desktop GUI requires a graphical session; it is not intended for a terminal-only or headless environment.
- Offline backtests depend on the selected dates being covered by the local CSV files.
- If history cannot be read or saved, inspect data/history.json and the displayed error. The GUI does not automatically replace invalid non-empty history files.

## 12. Limitations

- Only the five ETFs listed in this document are supported.
- A maximum of three assets can be included in one portfolio.
- Only Buy and Hold and DCA investment strategies are implemented.
- All investment amounts and portfolio values are expressed in USD.
- The application uses historical adjusted closing prices and does not model transaction fees, taxes, bid-ask spreads or other trading costs.
- Fractional shares are supported in the simulation.
- The application does not execute real transactions or account for real-world order execution.
- Historical data availability depends on Yahoo Finance or the included local CSV backups.
- Local backup coverage may limit the date ranges available for offline backtesting.
- The application uses the NYSE trading calendar for data coverage validation.

## 13. Disclaimer

This project is an educational programming exercise developed for COMP9001.

The backtesting results are based on historical market data and simplified investment assumptions. They do not represent actual trading results or guarantee future investment performance.

This application is not intended to provide financial or investment advice.

## 14. Acknowledgement of AI Use

### AI Tools Used

I used OpenAI ChatGPT and Codex to assist in completing the GUI enhancement and related documentation for this Final Project.

### How AI Was Used

I used these tools to discuss the GUI architecture and explain programming concepts; generate and revise substantial portions of gui.py; implement input validation, background backtest execution, embedded Matplotlib charts and history display; identify and fix errors; and prepare and run verification scripts. AI also assisted with writing and revising this README and the explanatory comments in requirements.txt.

The GUI implementation includes substantial AI-generated code, not only AI-generated suggestions or proofreading. It reuses the existing functions in main.py, data_processor.py and data_downloader.py. Those three source modules were not changed during this GUI enhancement.

### My Involvement and Verification

I specified the requirements, directed revisions and confirmed the initial main-window behavior. AI-assisted automated checks covered input validation, offline CSV backtests, GUI execution, chart replacement and history handling using temporary history files. Live Yahoo Finance downloads were not verified in these checks.

I remain responsible for understanding, reviewing and validating the submitted work and ensuring that my use of AI complies with the unit's assessment requirements. This acknowledgement records the tools and their actual contribution; it does not establish that the extent of AI use is permitted by the assessment rules.
