# NovaRetail Customer Intelligence Dashboard

Interactive Streamlit dashboard for exploring customer behavior, revenue, and
retention risk across NovaRetail's regions, product categories, and sales channels.

## Live app
[Add your deployed Streamlit Cloud URL here]

## Files
- `app.py` — the Streamlit application
- `requirements.txt` — pinned (minimum-version) Python dependencies
- `NR_dataset_cleaned.csv` — cleaned transaction dataset (see Data Cleaning below)
- `insight_and_process_note.pdf` — three key insights and a development-process write-up

## Running locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data cleaning summary
The raw dataset had a `ProductCategory` field with 34 near-duplicate values
(e.g. "Grocery" / "Groceries" / "Grocery Items"), an inconsistent age-group bucket
("55-64" vs. "55+"), and one missing segment `label`. These were consolidated into
10 canonical categories, one age bucket, and an explicit "Unknown" label respectively.
`RowID` (renamed from the original `idx`) is used as the unique row key, since
`TransactionID` repeats across different customers and dates.

## Dashboard structure
- **Overview tab** — revenue trend by segment, customer counts by segment, revenue
  by region/channel, and revenue by product category.
- **Growth, Risk & Strategy Insights tab** — dynamically generated insight narrative
  (recomputed from whatever filters are currently applied) covering growth
  opportunities, decline risk signals, and strategic investment priorities, plus a
  downloadable at-risk customer list.
- **Data Explorer tab** — the filtered raw data with a data dictionary and CSV export.

All charts and insights respond to the sidebar filters (date range, segment, region,
category, channel).
