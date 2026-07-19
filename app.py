"""
NovaRetail Customer Intelligence Dashboard
Interactive Streamlit app for exploring customer behavior, revenue, and risk signals.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="NovaRetail Customer Intelligence Dashboard", layout="wide")


@st.cache_data
def load_data():
    df = pd.read_csv("NR_dataset_cleaned.csv", parse_dates=["TransactionDate"])
    return df


df = load_data()

st.title("NovaRetail Customer Intelligence Dashboard")
st.caption(
    "Explore customer segments, revenue, and risk signals across regions, "
    "categories, and channels."
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
# KPI row
# ---------------------------------------------------------------------------
total_revenue = filtered["PurchaseAmount"].sum()
active_customers = filtered["CustomerID"].nunique()
avg_satisfaction = filtered["CustomerSatisfaction"].mean()
decline_share = (
    filtered.loc[filtered["label"] == "Decline", "CustomerID"].nunique()
    / active_customers
    * 100
    if active_customers > 0
    else 0
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total revenue", f"${total_revenue:,.2f}")
kpi2.metric("Active customers", f"{active_customers}")
kpi3.metric("Avg satisfaction", f"{avg_satisfaction:.1f} / 5")
kpi4.metric("Decline share", f"{decline_share:.1f}%")

st.divider()

# ---------------------------------------------------------------------------
# Row 2: Revenue trend by segment + customer count by segment
# ---------------------------------------------------------------------------
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
        trend, x="TransactionDate", y="PurchaseAmount", color="label", markers=True
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

with row2_right:
    st.subheader("Customers by segment")
    seg_counts = (
        filtered.drop_duplicates("CustomerID")["label"]
        .value_counts()
        .reset_index()
    )
    seg_counts.columns = ["label", "count"]
    fig_seg = px.bar(
        seg_counts.sort_values("count"),
        x="count",
        y="label",
        orientation="h",
        color="label",
    )
    fig_seg.update_layout(showlegend=False, xaxis_title="Customers", yaxis_title="")
    st.plotly_chart(fig_seg, use_container_width=True)
    st.caption(
        "Distribution of unique customers across segments for the current filter. "
        "A shrinking Promising/Growth base relative to Stable/Decline is an early "
        "warning sign for future revenue."
    )

# ---------------------------------------------------------------------------
# Row 3: Revenue by region x channel + at-risk customer table
# ---------------------------------------------------------------------------
row3_left, row3_right = st.columns(2)

with row3_left:
    st.subheader("Revenue by region and channel")
    region_channel = (
        filtered.groupby(["CustomerRegion", "RetailChannel"])["PurchaseAmount"]
        .sum()
        .reset_index()
    )
    fig_region = px.bar(
        region_channel,
        x="CustomerRegion",
        y="PurchaseAmount",
        color="RetailChannel",
        barmode="group",
    )
    fig_region.update_layout(
        xaxis_title="Region", yaxis_title="Revenue ($)", legend_title="Channel"
    )
    st.plotly_chart(fig_region, use_container_width=True)
    st.caption(
        "Compares Online vs. Physical Store revenue by region \u2014 useful for "
        "deciding where to invest in e-commerce vs. in-store experience."
    )

with row3_right:
    st.subheader("At-risk customers")
    at_risk = filtered[
        (filtered["label"] == "Decline") | (filtered["CustomerSatisfaction"] <= 2)
    ].sort_values("CustomerSatisfaction")
    at_risk_display = at_risk[
        ["CustomerID", "label", "CustomerRegion", "CustomerSatisfaction", "PurchaseAmount"]
    ].drop_duplicates(subset=["CustomerID"])
    st.dataframe(at_risk_display, use_container_width=True, hide_index=True)
    st.caption(
        "Customers flagged as Decline or with satisfaction of 2 or lower \u2014 "
        "candidates for proactive retention outreach."
    )

st.divider()

# ---------------------------------------------------------------------------
# Row 4: Revenue by product category
# ---------------------------------------------------------------------------
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
    "where NovaRetail's existing customer base already spends the most, and "
    "where marketing or inventory investment may pay off fastest."
)

st.divider()
st.caption(
    "Data is a 100-transaction sample considered representative of NovaRetail's "
    "full client base."
)
