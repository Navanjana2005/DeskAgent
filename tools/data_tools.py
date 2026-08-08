"""
tools/data_tools.py
Data analysis tools: CSV queries, statistics, JSON/CSV conversion, and chart plotting.

Required packages: pip install pandas matplotlib
"""

import os
import json
from langchain_core.tools import tool

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend — saves to file without display
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def _check_pandas():
    if not HAS_PANDAS:
        return "❌ pandas not installed. Run: pip install pandas"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# CSV / DATA TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def query_csv(file_path: str, query: str, max_rows: int = 30) -> str:
    """Queries a CSV file using a pandas query expression.

    Args:
        file_path: Path to the CSV file.
        query: Pandas query string (e.g., 'Age > 30', 'City == "London"', 'Salary >= 50000').
               Use empty string "" to return all rows.
        max_rows: Max rows to show in result (default 30).

    Examples:
        query='Score > 90'
        query='Department == "Engineering" and Salary > 60000'
        query=''   (show all rows)
    """
    err = _check_pandas()
    if err:
        return err
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        df = pd.read_csv(file_path)
        if query.strip():
            result = df.query(query)
        else:
            result = df
        count = len(result)
        if count == 0:
            return f"No rows matched: {query}"
        output = result.head(max_rows).to_string(index=False)
        footer = f"\n... ({count - max_rows} more rows)" if count > max_rows else ""
        return (
            f"📊 CSV Query: {os.path.basename(file_path)}\n"
            f"Filter: '{query}' | Matched: {count} rows\n"
            f"{'─' * 60}\n"
            f"{output}{footer}"
        )
    except Exception as e:
        return f"❌ Error querying CSV: {e}"


@tool
def csv_stats(file_path: str, columns: str = "") -> str:
    """Returns descriptive statistics (mean, min, max, std, count, nulls) for a CSV file.

    Args:
        file_path: Path to the CSV file.
        columns: Comma-separated column names to analyze (leave empty for all numeric columns).
    """
    err = _check_pandas()
    if err:
        return err
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        df = pd.read_csv(file_path)

        if columns.strip():
            col_list = [c.strip() for c in columns.split(",")]
            missing = [c for c in col_list if c not in df.columns]
            if missing:
                return f"❌ Columns not found: {missing}\nAvailable: {list(df.columns)}"
            df = df[col_list]

        numeric_df = df.select_dtypes(include="number")
        if numeric_df.empty:
            return "⚠️  No numeric columns found for statistics."

        stats = numeric_df.describe().round(3)

        # Add null counts
        nulls = numeric_df.isnull().sum()
        stats.loc["nulls"] = nulls

        result = (
            f"📈 CSV Statistics: {os.path.basename(file_path)}\n"
            f"Rows: {len(df)} | Columns analyzed: {len(numeric_df.columns)}\n"
            f"{'─' * 60}\n"
            f"{stats.to_string()}"
        )
        return result
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def json_to_csv(input_path: str, output_path: str) -> str:
    """Converts a JSON file to CSV format (or CSV to JSON).

    Args:
        input_path: Path to the source file (.json or .csv).
        output_path: Path for the output file (.csv or .json).
    """
    err = _check_pandas()
    if err:
        return err
    try:
        if not os.path.exists(input_path):
            return f"❌ File not found: {input_path}"

        in_ext = os.path.splitext(input_path)[1].lower()
        out_ext = os.path.splitext(output_path)[1].lower()

        if in_ext == ".json":
            df = pd.read_json(input_path)
            if out_ext == ".csv":
                df.to_csv(output_path, index=False)
                msg = f"✅ JSON → CSV: {len(df)} rows, {len(df.columns)} columns"
            else:
                return "❌ Output must be .csv when input is .json"

        elif in_ext == ".csv":
            df = pd.read_csv(input_path)
            if out_ext == ".json":
                df.to_json(output_path, orient="records", indent=2)
                msg = f"✅ CSV → JSON: {len(df)} records"
            else:
                return "❌ Output must be .json when input is .csv"
        else:
            return f"❌ Unsupported input format: {in_ext}. Use .json or .csv"

        size_kb = os.path.getsize(output_path) / 1024
        return f"{msg}\nSaved: {output_path} ({size_kb:.1f} KB)"
    except Exception as e:
        return f"❌ Error converting: {e}"


@tool
def plot_data(
    file_path: str,
    chart_type: str,
    x_column: str,
    y_column: str,
    output_image: str = "chart.png",
    title: str = "",
) -> str:
    """Generates a chart (bar, line, pie, scatter, histogram) from a CSV file.

    Args:
        file_path: Path to the CSV file.
        chart_type: Chart type: 'bar', 'line', 'pie', 'scatter', or 'histogram'.
        x_column: Column name for the X axis (or category labels for pie chart).
        y_column: Column name for the Y axis (or values for pie chart; ignored for histogram).
        output_image: Path to save the chart image (default 'chart.png').
        title: Chart title (optional — auto-generated if empty).
    """
    if not HAS_PANDAS:
        return "❌ pandas not installed. Run: pip install pandas matplotlib"
    if not HAS_MPL:
        return "❌ matplotlib not installed. Run: pip install matplotlib"
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"

        df = pd.read_csv(file_path)
        chart_type = chart_type.lower()

        if x_column not in df.columns:
            return f"❌ Column '{x_column}' not found. Available: {list(df.columns)}"
        if chart_type != "histogram" and y_column not in df.columns:
            return f"❌ Column '{y_column}' not found. Available: {list(df.columns)}"

        fig, ax = plt.subplots(figsize=(10, 6))
        chart_title = title or f"{chart_type.title()} Chart: {y_column} by {x_column}"

        if chart_type == "bar":
            ax.bar(df[x_column].astype(str), df[y_column], color="#4472C4")
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)
            plt.xticks(rotation=45, ha="right")
        elif chart_type == "line":
            ax.plot(df[x_column].astype(str), df[y_column], marker="o", color="#4472C4", linewidth=2)
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)
            plt.xticks(rotation=45, ha="right")
        elif chart_type == "pie":
            values = df[y_column].head(10)
            labels = df[x_column].head(10).astype(str)
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
            ax.axis("equal")
        elif chart_type == "scatter":
            ax.scatter(df[x_column], df[y_column], alpha=0.7, color="#4472C4")
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)
        elif chart_type == "histogram":
            ax.hist(df[x_column].dropna(), bins=20, color="#4472C4", edgecolor="white")
            ax.set_xlabel(x_column)
            ax.set_ylabel("Frequency")
            chart_title = title or f"Histogram: {x_column}"
        else:
            plt.close()
            return f"❌ Unknown chart type '{chart_type}'. Use: bar, line, pie, scatter, histogram"

        ax.set_title(chart_title, fontsize=14, fontweight="bold", pad=15)
        fig.tight_layout()
        plt.savefig(output_image, dpi=150, bbox_inches="tight")
        plt.close()

        size_kb = os.path.getsize(output_image) / 1024
        return (
            f"✅ Chart saved!\n"
            f"Type:   {chart_type}\n"
            f"Title:  {chart_title}\n"
            f"Saved:  {output_image} ({size_kb:.1f} KB)"
        )
    except Exception as e:
        plt.close()
        return f"❌ Error creating chart: {e}"


@tool
def summarize_json(file_path: str) -> str:
    """Reads and summarizes a JSON file, showing structure, key names, and sample data.

    Args:
        file_path: Path to the JSON file.
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        size_kb = os.path.getsize(file_path) / 1024

        if isinstance(data, list):
            count = len(data)
            sample = data[0] if data else {}
            keys = list(sample.keys()) if isinstance(sample, dict) else []
            summary = (
                f"📋 JSON Array — {count} items\n"
                f"Keys: {', '.join(str(k) for k in keys[:15])}\n"
                f"Sample (first item):\n{json.dumps(sample, indent=2, default=str)[:500]}"
            )
        elif isinstance(data, dict):
            keys = list(data.keys())
            summary = (
                f"📋 JSON Object — {len(keys)} keys\n"
                f"Keys: {', '.join(str(k) for k in keys[:20])}\n"
                f"Preview:\n{json.dumps({k: data[k] for k in keys[:5]}, indent=2, default=str)[:500]}"
            )
        else:
            summary = f"JSON Value: {str(data)[:200]}"

        return f"🗂️  {os.path.basename(file_path)} ({size_kb:.1f} KB)\n{'─' * 50}\n{summary}"
    except json.JSONDecodeError as e:
        return f"❌ Invalid JSON: {e}"
    except Exception as e:
        return f"❌ Error: {e}"
