"""Run with python gui.py; handle user interaction and reuse the existing engine."""
import json
import math
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import tkinter as tk
from tkinter import messagebox, ttk

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
# The __main__ guard in main.py prevents imports from starting the CLI.
from main import run_backtest, save_history

HISTORY_PATH = Path(__file__).resolve().parent / "data" / "history.json"
ETFS = {"SPY": "S&P 500", "QQQ": "Nasdaq-100", "TQQQ": "3x Leveraged Nasdaq-100",
        "GLD": "Gold", "IEF": "US Treasury Bonds"}
STRATEGIES = {"Buy and Hold": "buy_and_hold", "DCA": "dca"}
STRATEGY_NAMES = {value: key for key, value in STRATEGIES.items()}
METRICS = (
    ("Final_Value", "Final Portfolio Value", "currency"),
    ("Total_Invested", "Total Invested", "currency"),
    ("Profit", "Profit / Loss", "currency"),
    ("Simple_Return", "Simple Return", "percent"),
    ("Max_Drawdown", "Maximum Drawdown", "percent"),
)


def build_config(
    asset_inputs: list[tuple[str, str, str | int | float]],
    start_text: str,
    end_text: str,
) -> dict:
    """Validate (ticker, strategy_code, amount_text) rows and build a config.

    Amounts are strings from form entries or numbers from saved history.
    This function does not access widgets and raises ValueError for invalid input.
    """
    if not 1 <= len(asset_inputs) <= 3:
        raise ValueError("Select between 1 and 3 assets.")
    dates = []
    for label, text in (("Start Date", start_text), ("End Date", end_text)):
        text = text.strip()
        try:
            date = datetime.strptime(text, "%Y-%m-%d")
        except ValueError as error:
            raise ValueError(f"{label} must be a valid date in YYYY-MM-DD format.") from error
        # strptime accepts 2020-1-1, so format it back to enforce YYYY-MM-DD.
        if date.strftime("%Y-%m-%d") != text:
            raise ValueError(f"{label} must use YYYY-MM-DD format.")
        dates.append(date)
    if dates[0] > dates[1]:
        raise ValueError("Start Date cannot be after End Date.")
    assets = []
    selected = set()
    for ticker, strategy, amount_text in asset_inputs:
        if ticker not in ETFS:
            raise ValueError("Choose a supported ETF for each asset.")
        if ticker in selected:
            raise ValueError(f"{ticker} is selected more than once.")
        if strategy not in STRATEGY_NAMES:
            raise ValueError("Choose Buy and Hold or DCA for each asset.")
        try:
            amount = float(amount_text)
        except (ValueError, TypeError) as error:
            raise ValueError(f"Enter a numeric investment amount for {ticker}.") from error
        # NaN and infinity are floats, but neither is a valid investment amount.
        if not math.isfinite(amount) or amount < 500:
            raise ValueError(f"Investment for {ticker} must be at least USD 500 and finite.")
        selected.add(ticker)
        assets.append({"ticker": ticker, "strategy": strategy, "amount": amount})
    return {"assets": assets, "start_date": dates[0].strftime("%Y-%m-%d"),
            "end_date": dates[1].strftime("%Y-%m-%d")}


def configuration_text(config: dict) -> str:
    """Build a shared configuration summary for confirmation, results and history."""
    lines = [f"Period: {config['start_date']} to {config['end_date']}"]
    for asset in config["assets"]:
        strategy = asset["strategy"]
        label = "Initial capital" if strategy == "buy_and_hold" else "Monthly investment"
        lines.append(f"{asset['ticker']} - {STRATEGY_NAMES[strategy]} - "
                     f"{label}: USD {asset['amount']:,.2f}")
    return "\n".join(lines)


def format_metric(value: float, kind: str) -> str:
    """Format currency or decimal returns, such as 0.12 as 12.00%."""
    return f"{value:,.2%}" if kind == "percent" else f"USD {value:,.2f}"


def read_history(path: Path = HISTORY_PATH) -> list[dict]:
    """Read and validate history without deleting records or overwriting bad data."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    # Treat a blank placeholder file as an empty history.
    if not text.strip():
        return []
    records = json.loads(text)
    if not isinstance(records, list):
        raise ValueError("History must contain a JSON list.")
    for number, record in enumerate(records, start=1):
        try:
            if not isinstance(record["timestamp"], str):
                raise ValueError("Timestamp must be text.")
            config = record["config"]
            for asset in config["assets"]:
                amount = asset["amount"]
                if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                    raise ValueError("Investment amount must be numeric.")
            build_config(
                [(a["ticker"], a["strategy"], a["amount"]) for a in config["assets"]],
                config["start_date"], config["end_date"])
            for key, _, _ in METRICS:
                value = record["performance"][key]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"{key} must be numeric.")
                if not math.isfinite(value):
                    raise ValueError(f"{key} must be finite.")
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise ValueError(f"Invalid history record {number}: {error}") from error
    return records


class BacktestApp:
    """Manage four pages in one window, storing widgets and runtime state."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.busy = False
        self.messages = Queue()
        self.history_records = []
        self.chart_canvas = None
        root.title("Investment Strategy Backtesting Simulator")
        root.geometry("1050x800")
        root.minsize(940, 720)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.pages = {name: ttk.Frame(root, padding=24)
                      for name in ("menu", "config", "results", "history")}
        style = ttk.Style(root)
        style.configure("Heading.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Value.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Positive.TLabel", foreground="#14734b", font=("Segoe UI", 15, "bold"))
        style.configure("Negative.TLabel", foreground="#b42318", font=("Segoe UI", 15, "bold"))
        self.create_menu()
        self.create_config_page()
        self.create_results_page()
        self.create_history_page()
        self.show_page("menu")

    def show_page(self, name: str) -> None:
        """Hide pages without destroying them so configuration inputs are preserved."""
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

    def create_menu(self) -> None:
        content = ttk.Frame(self.pages["menu"])
        content.pack(expand=True)
        ttk.Label(content, text="Investment Strategy Backtesting Simulator",
                  style="Heading.TLabel").pack(pady=(0, 12))
        ttk.Label(content, text="Historical Portfolio Analysis").pack(pady=(0, 30))
        ttk.Button(content, text="New Backtest", width=28,
                   command=lambda: self.show_page("config")).pack(pady=8)
        ttk.Button(content, text="Backtest History", width=28,
                   command=self.open_history).pack(pady=8)
        ttk.Button(content, text="Exit", width=28, command=self.close).pack(pady=8)

    def create_config_page(self) -> None:
        # Allow scrolling when three asset rows exceed the available window height.
        container = self.pages["config"]
        self.config_canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.config_canvas.yview)
        self.config_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.config_canvas.pack(side="left", fill="both", expand=True)
        page = ttk.Frame(self.config_canvas, padding=(0, 0, 12, 8))
        content_id = self.config_canvas.create_window((0, 0), window=page, anchor="nw")
        page.bind("<Configure>", lambda event: self.config_canvas.configure(
            scrollregion=self.config_canvas.bbox("all")))
        self.config_canvas.bind("<Configure>", lambda event: self.config_canvas.itemconfigure(
            content_id, width=event.width))
        self.root.bind("<MouseWheel>", self.scroll_config)
        ttk.Label(page, text="New Backtest", style="Heading.TLabel").pack(anchor="w")
        count_bar = ttk.Frame(page)
        count_bar.pack(fill="x", pady=16)
        ttk.Label(count_bar, text="Number of assets:").pack(side="left", padx=(0, 12))
        self.asset_count = tk.StringVar(value="1")
        count_box = ttk.Combobox(count_bar, textvariable=self.asset_count,
                                 values=("1", "2", "3"), state="readonly", width=5)
        count_box.pack(side="left")
        count_box.bind("<<ComboboxSelected>>", self.update_asset_rows)
        self.asset_rows = []
        for index, ticker in enumerate(("SPY", "QQQ", "GLD")):
            frame = ttk.LabelFrame(page, text=f"Asset {index + 1}", padding=12)
            row = {
                "frame": frame, "ticker": tk.StringVar(value=ticker),
                "strategy": tk.StringVar(value="Buy and Hold"),
                "amount": tk.StringVar(value="1000"),
                "description": tk.StringVar(value=ETFS[ticker]),
                "amount_label": tk.StringVar(value="Initial Capital (USD)"),
            }
            ttk.Label(frame, text="ETF").grid(row=0, column=0, sticky="w")
            ticker_box = ttk.Combobox(frame, textvariable=row["ticker"],
                                      values=tuple(ETFS), state="readonly", width=10)
            ticker_box.grid(row=1, column=0, sticky="w", padx=(0, 20), pady=4)
            ttk.Label(frame, text="Strategy").grid(row=0, column=1, sticky="w")
            strategy_box = ttk.Combobox(frame, textvariable=row["strategy"],
                                        values=tuple(STRATEGIES), state="readonly", width=20)
            strategy_box.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=4)
            ttk.Label(frame, textvariable=row["amount_label"]).grid(row=0, column=2, sticky="w")
            ttk.Entry(frame, textvariable=row["amount"], width=20).grid(row=1, column=2, sticky="w")
            ttk.Label(frame, text="Minimum investment: USD 500", foreground="#666666").grid(
                row=2, column=2, sticky="w", pady=(2, 0))
            ttk.Label(frame, textvariable=row["description"]).grid(
                row=2, column=0, columnspan=2, sticky="w")
            self.asset_rows.append(row)
            # Capture the current index so each callback updates its own asset row.
            ticker_box.bind("<<ComboboxSelected>>", lambda event, i=index: self.update_asset_labels(i))
            strategy_box.bind("<<ComboboxSelected>>", lambda event, i=index: self.update_asset_labels(i))

        self.config_footer = ttk.Frame(page)
        self.config_footer.pack(fill="x", pady=(12, 0))
        self.start_date = tk.StringVar(value="2020-01-01")
        self.end_date = tk.StringVar(value="2025-01-01")
        dates = ttk.LabelFrame(self.config_footer, text="Backtesting Period", padding=12)
        dates.pack(fill="x")
        for column, (label, variable) in enumerate((
            ("Start Date (YYYY-MM-DD)", self.start_date),
            ("End Date (YYYY-MM-DD)", self.end_date),
        )):
            ttk.Label(dates, text=label).grid(row=0, column=column, sticky="w", padx=(0, 24))
            ttk.Entry(dates, textvariable=variable, width=24).grid(
                row=1, column=column, sticky="w", padx=(0, 24), pady=6)
        ttk.Label(self.config_footer,
                  text="Minimum per asset: USD 500. DCA amounts are monthly contributions.").pack(anchor="w", pady=8)
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self.config_footer, textvariable=self.status, wraplength=850).pack(anchor="w", pady=4)
        self.progress = ttk.Progressbar(self.config_footer, mode="indeterminate")
        self.progress.pack(fill="x", pady=8)
        actions = ttk.Frame(self.config_footer)
        actions.pack(fill="x")
        self.run_button = ttk.Button(actions, text="Run Backtest", command=self.start_backtest)
        self.run_button.pack(side="left", padx=(0, 12))
        self.config_back = ttk.Button(actions, text="Back to Main Menu",
                                      command=lambda: self.show_page("menu"))
        self.config_back.pack(side="left")
        self.update_asset_rows()

    def scroll_config(self, event: tk.Event) -> None:
        """Handle Windows mouse-wheel scrolling only when the form overflows."""
        if self.pages["config"].winfo_ismapped():
            top, bottom = self.config_canvas.yview()
            if bottom - top < 1:
                self.config_canvas.yview_scroll(-int(event.delta / 120), "units")

    def update_asset_rows(self, event: tk.Event | None = None) -> None:
        count = int(self.asset_count.get())
        for index, row in enumerate(self.asset_rows):
            row["frame"].pack_forget()
            if index < count:
                row["frame"].pack(fill="x", pady=5, before=self.config_footer)

    def update_asset_labels(self, index: int) -> None:
        row = self.asset_rows[index]
        row["description"].set(ETFS[row["ticker"].get()])
        row["amount_label"].set("Initial Capital (USD)"
                                if row["strategy"].get() == "Buy and Hold"
                                else "Monthly Investment (USD)")

    def start_backtest(self) -> None:
        """Validate inputs on the main thread, then run the backtest in a worker."""
        if self.busy:
            return
        try:
            inputs = [
                (row["ticker"].get(), STRATEGIES[row["strategy"].get()], row["amount"].get())
                for row in self.asset_rows[:int(self.asset_count.get())]
            ]
            config = build_config(inputs, self.start_date.get(), self.end_date.get())
        except (ValueError, KeyError) as error:
            messagebox.showerror("Invalid Configuration", str(error), parent=self.root)
            return
        if not messagebox.askokcancel("Confirm Backtest", configuration_text(config), parent=self.root):
            return
        self.busy = True
        self.run_button.configure(state="disabled")
        self.config_back.configure(state="disabled")
        self.status.set("Running backtest... Downloading prices or using local CSV backup.")
        self.progress.start(12)
        # This config is a snapshot; later form edits cannot change the running test.
        Thread(target=self.backtest_worker, args=(config,), daemon=True).start()
        self.root.after(100, self.poll_backtest)

    def backtest_worker(self, config: dict) -> None:
        """Queue results for the main thread and retain results if saving fails."""
        try:
            portfolio, performance = run_backtest(config)
        except Exception as error:
            self.messages.put(("error", str(error)))
            return
        save_warning = None
        try:
            # save_history requires valid JSON. After a successful backtest, initialize
            # only blank files as []; never overwrite existing records or invalid JSON.
            if HISTORY_PATH.exists() and not HISTORY_PATH.read_text(encoding="utf-8").strip():
                HISTORY_PATH.write_text("[]", encoding="utf-8")
            save_history(config, performance)
        except Exception as error:
            save_warning = str(error)
        self.messages.put(("success", (config, portfolio, performance, save_warning)))

    def poll_backtest(self) -> None:
        """Poll with after so the window remains responsive while the worker runs."""
        try:
            outcome, payload = self.messages.get_nowait()
        except Empty:
            self.root.after(100, self.poll_backtest)
            return
        self.busy = False
        self.progress.stop()
        self.run_button.configure(state="normal")
        self.config_back.configure(state="normal")
        if outcome == "error":
            self.status.set("Backtest failed. Check the configuration and data availability.")
            messagebox.showerror("Backtest Failed", payload, parent=self.root)
            return
        config, portfolio, performance, save_warning = payload
        self.status.set("Backtest completed.")
        self.display_results(config, portfolio, performance, save_warning)

    def create_results_page(self) -> None:
        page = self.pages["results"]
        ttk.Label(page, text="Backtest Results", style="Heading.TLabel").pack(anchor="w")
        self.result_config = tk.StringVar()
        ttk.Label(page, textvariable=self.result_config, wraplength=880).pack(anchor="w", pady=10)
        metrics_frame = ttk.Frame(page)
        metrics_frame.pack(fill="x")
        self.metric_labels = {}
        for index, (key, title, _) in enumerate(METRICS):
            card = ttk.LabelFrame(metrics_frame, text=title, padding=10)
            card.grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
            metrics_frame.columnconfigure(index % 3, weight=1)
            label = ttk.Label(card, text="—", style="Value.TLabel")
            label.pack(anchor="w")
            self.metric_labels[key] = label
        self.save_status = tk.StringVar()
        ttk.Label(page, textvariable=self.save_status, wraplength=880).pack(anchor="w", pady=6)
        actions = ttk.Frame(page)
        actions.pack(fill="x", pady=6)
        ttk.Button(actions, text="Edit Configuration",
                   command=lambda: self.show_page("config")).pack(side="left")
        ttk.Button(actions, text="Backtest History", command=self.open_history).pack(side="left", padx=12)
        ttk.Button(actions, text="Back to Main Menu",
                   command=lambda: self.show_page("menu")).pack(side="left")
        self.chart_frame = ttk.Frame(page)
        self.chart_frame.pack(fill="both", expand=True)

    def display_results(
        self,
        config: dict,
        portfolio: pd.DataFrame,
        performance: dict,
        save_warning: str | None,
    ) -> None:
        self.result_config.set(configuration_text(config))
        for key, _, kind in METRICS:
            value = performance[key]
            style = "Value.TLabel"
            if key in ("Profit", "Simple_Return", "Max_Drawdown"):
                if value < 0:
                    style = "Negative.TLabel"
                elif value > 0:
                    style = "Positive.TLabel"
            self.metric_labels[key].configure(text=format_metric(value, kind), style=style)
        self.save_status.set("History not saved: " + save_warning if save_warning
                             else "Backtest history saved successfully.")
        self.show_page("results")
        # Remove the previous canvas and toolbar instead of stacking repeated charts.
        if self.chart_canvas is not None:
            # clear updates the linked toolbar, so call it before destroying widgets.
            self.chart_canvas.figure.clear()
            self.chart_canvas = None
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        try:
            figure = Figure(figsize=(8, 3.4), dpi=100, constrained_layout=True)
            axes = figure.add_subplot(111)
            axes.plot(portfolio["Date"], portfolio["Portfolio_Value"],
                      label="Portfolio Value", color="#2457a7")
            axes.plot(portfolio["Date"], portfolio["Cumulative_Invested"],
                      label="Cumulative Invested", linestyle="--", color="#c56c16")
            axes.set(title="Portfolio Backtest Performance", xlabel="Date", ylabel="Value (USD)")
            axes.grid(alpha=0.25)
            axes.legend()
            self.chart_canvas = FigureCanvasTkAgg(figure, master=self.chart_frame)
            toolbar = NavigationToolbar2Tk(self.chart_canvas, self.chart_frame, pack_toolbar=False)
            toolbar.update()
            toolbar.pack(side="bottom", fill="x")
            self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)
            self.chart_canvas.draw()
        except Exception as error:
            messagebox.showwarning("Chart Unavailable",
                                   f"Results are available, but the chart failed:\n{error}", parent=self.root)
        if save_warning:
            messagebox.showwarning("History Not Saved", save_warning, parent=self.root)

    def create_history_page(self) -> None:
        page = self.pages["history"]
        ttk.Label(page, text="Backtest History", style="Heading.TLabel").pack(anchor="w")
        actions = ttk.Frame(page)
        actions.pack(fill="x", pady=12)
        ttk.Button(actions, text="Refresh", command=self.open_history).pack(side="left")
        ttk.Button(actions, text="Back to Main Menu",
                   command=lambda: self.show_page("menu")).pack(side="left", padx=12)
        self.history_status = tk.StringVar()
        ttk.Label(page, textvariable=self.history_status, wraplength=870).pack(anchor="w", pady=6)
        table_frame = ttk.Frame(page)
        table_frame.pack(fill="x")
        columns = ("timestamp", "assets", "period", "final_value")
        self.history_table = ttk.Treeview(table_frame, columns=columns, show="headings",
                                          height=6, selectmode="browse")
        for column, title, width in (
            ("timestamp", "Timestamp", 175), ("assets", "ETFs", 140),
            ("period", "Period", 245), ("final_value", "Final Value (USD)", 160),
        ):
            self.history_table.heading(column, text=title)
            self.history_table.column(column, width=width, minwidth=80)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_table.yview)
        self.history_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.history_table.pack(side="left", fill="x", expand=True)
        self.history_table.bind("<<TreeviewSelect>>", self.show_history_details)
        ttk.Label(page, text="Selected Backtest Details").pack(anchor="w", pady=(18, 8))
        details_frame = ttk.Frame(page)
        details_frame.pack(fill="both", expand=True)
        self.history_details = tk.Text(details_frame, wrap="word", height=14,
                                       state="disabled", padx=12, pady=12)
        details_scroll = ttk.Scrollbar(details_frame, orient="vertical", command=self.history_details.yview)
        self.history_details.configure(yscrollcommand=details_scroll.set)
        details_scroll.pack(side="right", fill="y")
        self.history_details.pack(side="left", fill="both", expand=True)

    def set_history_details(self, text: str) -> None:
        # Temporarily enable programmatic updates, keeping history read-only for users.
        self.history_details.configure(state="normal")
        self.history_details.delete("1.0", "end")
        self.history_details.insert("1.0", text)
        self.history_details.configure(state="disabled")

    def open_history(self) -> None:
        self.show_page("history")
        for item in self.history_table.get_children():
            self.history_table.delete(item)
        self.history_records = []
        self.set_history_details("")
        try:
            self.history_records = list(reversed(read_history()))
        except (OSError, ValueError, UnicodeError) as error:
            self.history_status.set(f"Could not read history: {error}")
            self.set_history_details("The history file has not been changed. Check data/history.json before retrying.")
            return
        if not self.history_records:
            self.history_status.set("No backtest history found.")
            return
        self.history_status.set(f"{len(self.history_records)} saved backtest(s), newest first. Select a row for details.")
        for index, record in enumerate(self.history_records):
            config = record["config"]
            self.history_table.insert("", "end", iid=str(index), values=(
                record["timestamp"], ", ".join(a["ticker"] for a in config["assets"]),
                f"{config['start_date']} to {config['end_date']}",
                format_metric(record["performance"]["Final_Value"], "currency"),
            ))
        self.history_table.selection_set("0")
        self.show_history_details()

    def show_history_details(self, event: tk.Event | None = None) -> None:
        selection = self.history_table.selection()
        if not selection:
            return
        record = self.history_records[int(selection[0])]
        lines = [f"Timestamp: {record['timestamp']}", "", configuration_text(record["config"]), ""]
        for key, title, kind in METRICS:
            lines.append(f"{title}: {format_metric(record['performance'][key], kind)}")
        self.set_history_details("\n".join(lines))

    def close(self) -> None:
        # Do not exit during a backtest or save, which could interrupt history writes.
        if self.busy:
            messagebox.showinfo("Backtest Running",
                                "Please wait for the current backtest to finish before exiting.", parent=self.root)
            return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    BacktestApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
