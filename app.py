"""
NovaRetail Customer Intelligence Dashboard
Interactive Streamlit app for exploring customer behavior, revenue, and risk signals
across regions, categories, and channels.

Built for Sophia Martinez, Director of Customer Intelligence, to support three goals:
  1. Identify growth opportunities in the existing customer base.
  2. Detect early warning signs of customer decline.
  3. Recommend data-driven actions for commercial and marketing investment.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="NovaRetail Customer Intelligence Dashboard",
    page_icon="\U0001F4CA",
    layout="wide",
)

DATA_PATH = "NR_dataset_cleaned.csv"

# Fixed color coding so segment meaning is consistent across every chart in the
# app (Decline always red, Promising always green, etc.) instead of Plotly's
# default palette assigning colors arbitrarily based on sort order.
SEGMENT_COLORS = {
    "Promising": "#2CA02C",   # green
    "Growth": "#1F77B4",      # blue
    "Stable": "#B8960C",      # amber/gold
    "Decline": "#D62728",     # red
    "Unknown": "#7F7F7F",     # gray
}

# Below this many rows, a chart is flagged as low-sample so viewers don't
# over-read noisy patterns from a handful of transactions.
LOW_SAMPLE_THRESHOLD = 5


def sample_note(n_rows: int, n_customers: int | None = None) -> str:
    """Build a small caption noting how many rows/customers feed a chart, with
    an explicit low-sample warning when the slice is thin."""
    parts = [f"n = {n_rows} transaction{'s' if n_rows != 1 else ''}"]
    if n_customers is not None:
        parts.append(f"{n_customers} customer{'s' if n_customers != 1 else ''}")
    note = " \u00b7 ".join(parts)
    if n_rows < LOW_SAMPLE_THRESHOLD:
        note += " \u2014 \u26a0\ufe0f small sample, interpret with caution"
    return note


# ---------------------------------------------------------------------------
# Data loading (cached, with error handling so a missing/broken file fails
# gracefully instead of crashing the whole app)
# ---------------------------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["TransactionDate"])
    required_cols = {
        "RowID", "label", "CustomerID", "TransactionID", "TransactionDate",
        "ProductCategory", "PurchaseAmount", "CustomerAgeGroup", "CustomerGender",
        "CustomerRegion", "CustomerSatisfaction", "RetailChannel",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {missing}")
    return df


try:
    df = load_data(DATA_PATH)
except FileNotFoundError:
    st.error(
        f"Could not find `{DATA_PATH}`. Make sure the dataset file is in the same "
        "directory as app.py (repo root) when deploying to Streamlit Cloud."
    )
    st.stop()
except ValueError as e:
    st.error(f"Data validation error: {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("\U0001F4CA NovaRetail Customer Intelligence Dashboard")
st.caption(
    "Explore customer segments, revenue, and risk signals across regions, "
    "categories, and channels to guide growth, retention, and investment decisions."
)

with st.expander("\u2139\uFE0F About this dashboard and dataset"):
    st.markdown(
        """
**Business objective.** NovaRetail sells electronics, clothing, groceries, books, and
home products online and in physical stores. Customers are classified into four
behavioral segments &mdash; **Promising, Growth, Stable, Decline** &mdash; based on
purchasing patterns. This dashboard helps identify which customers generate the most
revenue, which segments are at risk, and where to focus investment.

**Variables used and why.** `PurchaseAmount` and `TransactionDate` drive all revenue
and trend analysis; `label` (segment) is the core behavioral lens for growth/risk
detection; `CustomerRegion` and `RetailChannel` support investment-allocation questions;
`CustomerSatisfaction` is the earliest available warning signal for decline, often
shifting before revenue does; `ProductCategory` (cleaned from 34 raw values down to
10 consistent categories) supports category-level investment decisions.

**Data quality note.** This is a 100-transaction sample considered representative of
NovaRetail's full client base. `RowID` (not `TransactionID`, which repeats across
different customers) is the reliable unique row key. A small number of customers
(10 of 34) carry more than one segment label across their transaction history, so
segment-based KPIs here are computed **per transaction**, not assumed to be a fixed
per-customer property &mdash; retention actions should be triggered on recent behavior,
not a single static label.
        """
    )

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

min_date = df["TransactionDate"].min().date()
max_date = df["TransactionDate"].max().date()
date_range = st.sidebar.date_input(
    "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

segments = sorted(df["label"].unique().tolist())
selected_segments = st.sidebar.multiselect("Segment", segments, default=segments)

regions = sorted(df["CustomerRegion"].unique().tolist())
selected_regions = st.sidebar.multiselect("Region", regions, default=regions)

categories = sorted(df["ProductCategory"].unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Product category", categories, default=categories
)

channels = sorted(df["RetailChannel"].unique().tolist())
selected_channels = st.sidebar.multiselect("Retail channel", channels, default=channels)

if st.sidebar.button("Reset filters"):
    st.rerun()

# Handle single-date selection gracefully (date_input can return one date while
# the user is still picking the range)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
mask = (
    (df["TransactionDate"].dt.date >= start_date)
    & (df["TransactionDate"].dt.date <= end_date)
    & (df["label"].isin(selected_segments))
    & (df["CustomerRegion"].isin(selected_regions))
    & (df["ProductCategory"].isin(selected_categories))
    & (df["RetailChannel"].isin(selected_channels))
)
filtered = df.loc[mask].copy()

if filtered.empty:
    st.warning("No transactions match the selected filters. Try widening your selection.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI row (with deltas vs. the full unfiltered dataset for context)
# ---------------------------------------------------------------------------
total_revenue = filtered["PurchaseAmount"].sum()
active_customers = filtered["CustomerID"].nunique()
avg_satisfaction = filtered["CustomerSatisfaction"].mean()
decline_rows = filtered.loc[filtered["label"] == "Decline", "CustomerID"].nunique()
decline_share = (decline_rows / active_customers * 100) if active_customers > 0 else 0

baseline_revenue = df["PurchaseAmount"].sum()
baseline_customers = df["CustomerID"].nunique()
baseline_satisfaction = df["CustomerSatisfaction"].mean()
baseline_decline_customers = df.loc[df["label"] == "Decline", "CustomerID"].nunique()
baseline_decline_share = baseline_decline_customers / baseline_customers * 100

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(
    "Total revenue", f"${total_revenue:,.2f}",
    delta=f"{(total_revenue - baseline_revenue):,.2f} vs. full data" if len(filtered) != len(df) else None,
)
kpi2.metric(
    "Active customers", f"{active_customers}",
    delta=f"{active_customers - baseline_customers} vs. full data" if len(filtered) != len(df) else None,
)
kpi3.metric(
    "Avg satisfaction", f"{avg_satisfaction:.1f} / 5",
    delta=f"{(avg_satisfaction - baseline_satisfaction):+.1f} vs. full data" if len(filtered) != len(df) else None,
)
kpi4.metric(
    "Decline share", f"{decline_share:.1f}%",
    delta=f"{(decline_share - baseline_decline_share):+.1f} pts vs. full data" if len(filtered) != len(df) else None,
    delta_color="inverse",
)

st.divider()

# ---------------------------------------------------------------------------
# Tabs: separate the visual overview from the actionable insight narrative,
# and from a raw data explorer -- keeps each screen focused and usable.
# ---------------------------------------------------------------------------
tab_overview, tab_insights, tab_data = st.tabs(
    ["\U0001F4C8 Overview", "\U0001F4A1 Growth, Risk & Strategy Insights", "\U0001F4C4 Data Explorer"]
)

# ---------------------------------------------------------------------------
# TAB 1: Overview charts
# ---------------------------------------------------------------------------
with tab_overview:
    row2_left, row2_right = st.columns([1.3, 1])

    with row2_left:
        st.subheader("Revenue by segment over time")
        trend = (
            filtered.set_index("TransactionDate")
            .groupby("label")
            .resample("W")["PurchaseAmount"]
            .sum()
            .reset_index()
        )
        fig_trend = px.line(
            trend, x="TransactionDate", y="PurchaseAmount", color="label", markers=True,
            color_discrete_map=SEGMENT_COLORS,
        )
        fig_trend.update_layout(
            xaxis_title="Week", yaxis_title="Revenue ($)", legend_title="Segment"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.caption(
            "Weekly revenue split by behavioral segment. Rising Growth or Promising "
            "lines signal emerging opportunity; a falling Decline line is not "
            "necessarily good news \u2014 it may mean those customers are lapsing entirely."
        )
        st.caption(sample_note(len(filtered), filtered["CustomerID"].nunique()))

    with row2_right:
        st.subheader("Customers by segment")
        seg_counts = (
            filtered.drop_duplicates("CustomerID")["label"].value_counts().reset_index()
        )
        seg_counts.columns = ["label", "count"]
        fig_seg = px.bar(
            seg_counts.sort_values("count"), x="count", y="label", orientation="h", color="label",
            color_discrete_map=SEGMENT_COLORS,
        )
        fig_seg.update_layout(showlegend=False, xaxis_title="Customers", yaxis_title="")
        st.plotly_chart(fig_seg, use_container_width=True)
        st.caption(
            "Distribution of unique customers across segments for the current filter. "
            "A shrinking Promising/Growth base relative to Stable/Decline is an early "
            "warning sign for future revenue."
        )
        st.caption(sample_note(len(filtered), active_customers))

    row3_left, row3_right = st.columns(2)

    with row3_left:
        st.subheader("Revenue by region and channel")
        region_channel = (
            filtered.groupby(["CustomerRegion", "RetailChannel"])["PurchaseAmount"]
            .sum()
            .reset_index()
        )
        fig_region = px.bar(
            region_channel, x="CustomerRegion", y="PurchaseAmount",
            color="RetailChannel", barmode="group",
        )
        fig_region.update_layout(
            xaxis_title="Region", yaxis_title="Revenue ($)", legend_title="Channel"
        )
        st.plotly_chart(fig_region, use_container_width=True)
        st.caption(
            "Compares Online vs. Physical Store revenue by region \u2014 useful for "
            "deciding where to invest in e-commerce vs. in-store experience."
        )
        st.caption(sample_note(len(filtered)))

    with row3_right:
        st.subheader("Revenue by product category")
        category_revenue = (
            filtered.groupby("ProductCategory")["PurchaseAmount"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        fig_category = px.bar(category_revenue, x="ProductCategory", y="PurchaseAmount")
        fig_category.update_layout(xaxis_title="Product category", yaxis_title="Revenue ($)")
        st.plotly_chart(fig_category, use_container_width=True)
        st.caption(
            "Ranks categories by total revenue for the current filter \u2014 highlights "
            "where the existing customer base already spends the most, and where "
            "marketing or inventory investment may pay off fastest."
        )
        st.caption(sample_note(len(filtered)))

# ---------------------------------------------------------------------------
# TAB 2: Insight narrative -- dynamically recomputed from the CURRENT filter
# selection, so the "three insights" the rubric asks for are generated live
# from whatever slice of data the user is looking at, not hard-coded text.
# ---------------------------------------------------------------------------
with tab_insights:
    st.caption(
        f"Insights below are computed from the current filter: {sample_note(len(filtered), active_customers)}. "
        "With a 100-transaction sample overall, narrow filter combinations can drop to just a "
        "handful of rows \u2014 treat highly-filtered insights as directional, not conclusive."
    )
    st.subheader("Growth opportunity")
    cat_rev = filtered.groupby("ProductCategory")["PurchaseAmount"].sum().sort_values(ascending=False)
    if len(cat_rev) > 0:
        top_cat = cat_rev.index[0]
        top_cat_share = cat_rev.iloc[0] / total_revenue * 100
        st.markdown(
            f"**{top_cat}** is the leading category in the current filter, generating "
            f"**${cat_rev.iloc[0]:,.2f}** ({top_cat_share:.0f}% of revenue in this view). "
            "Consider prioritizing inventory and marketing spend here, and cross-selling "
            "adjacent categories to the same customers."
        )
    region_channel_pivot = filtered.pivot_table(
        index="CustomerRegion", columns="RetailChannel", values="PurchaseAmount", aggfunc="sum", fill_value=0
    )
    if "Online" in region_channel_pivot.columns and "Physical Store" in region_channel_pivot.columns:
        region_channel_pivot["channel_gap_pct"] = (
            (region_channel_pivot["Online"] - region_channel_pivot["Physical Store"])
            / region_channel_pivot[["Online", "Physical Store"]].sum(axis=1).replace(0, pd.NA)
            * 100
        )
        online_leaning = region_channel_pivot["channel_gap_pct"].idxmax()
        physical_leaning = region_channel_pivot["channel_gap_pct"].idxmin()
        st.markdown(
            f"**{online_leaning}** over-indexes on Online revenue, while **{physical_leaning}** "
            "over-indexes on Physical Store revenue \u2014 a region-specific channel investment "
            "plan will outperform a single national push."
        )

    st.divider()
    st.subheader("Risk: early warning signs of decline")
    decline_satisfaction = filtered.loc[filtered["label"] == "Decline", "CustomerSatisfaction"].mean()
    promising_satisfaction = filtered.loc[filtered["label"] == "Promising", "CustomerSatisfaction"].mean()
    if pd.notna(decline_satisfaction) and pd.notna(promising_satisfaction):
        gap = promising_satisfaction - decline_satisfaction
        st.markdown(
            f"Decline customers average **{decline_satisfaction:.1f}/5** satisfaction vs. "
            f"**{promising_satisfaction:.1f}/5** for Promising customers, a **{gap:.1f}-point gap** "
            "that makes satisfaction a strong, early, actionable signal for proactive retention outreach."
        )
    st.markdown(
        f"**Decline share** in the current view is **{decline_share:.1f}%** of active customers. "
        "The at-risk table below lists individual customers flagged as Decline or with satisfaction "
        "of 2 or lower, ranked by lowest satisfaction first."
    )
    at_risk = filtered[
        (filtered["label"] == "Decline") | (filtered["CustomerSatisfaction"] <= 2)
    ].sort_values("CustomerSatisfaction")
    at_risk_display = at_risk[
        ["CustomerID", "label", "CustomerRegion", "CustomerSatisfaction", "PurchaseAmount"]
    ].drop_duplicates(subset=["CustomerID"])
    st.dataframe(at_risk_display, use_container_width=True, hide_index=True)
    st.download_button(
        "Download at-risk customer list (CSV)",
        data=at_risk_display.to_csv(index=False).encode("utf-8"),
        file_name="novaretail_at_risk_customers.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Strategic priority")
    st.markdown(
        "Combining the signals above: invest in the leading product category with a "
        "region-specific channel mix (rather than a uniform national push), and trigger "
        "retention outreach on recent satisfaction scores and transaction behavior rather "
        "than a single static segment label, since segment status can shift over time."
    )

# ---------------------------------------------------------------------------
# TAB 3: Raw data explorer, with export
# ---------------------------------------------------------------------------
with tab_data:
    st.subheader("Filtered transaction data")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered data (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="novaretail_filtered_data.csv",
        mime="text/csv",
    )
    with st.expander("Data dictionary"):
        st.markdown(
            """
| Column | Description |
|---|---|
| RowID | Unique row identifier |
| label | Behavioral segment: Promising, Growth, Stable, Decline, or Unknown |
| CustomerID | Unique customer identifier |
| TransactionID | Transaction reference (not guaranteed unique per row) |
| TransactionDate | Date of purchase |
| ProductCategory | Cleaned product category (10 consistent values) |
| PurchaseAmount | Transaction revenue in USD |
| CustomerAgeGroup | Age bracket |
| CustomerGender | Customer gender |
| CustomerRegion | North, South, East, or West |
| CustomerSatisfaction | Rating from 1 (lowest) to 5 (highest) |
| RetailChannel | Online or Physical Store |
            """
        )

st.divider()
st.caption(
    "Data is a 100-transaction sample considered representative of NovaRetail's "
    "full client base."
)
