import pandas as pd
import plotly.express as px
import streamlit as st


WEIGHTED_SENTIMENT_BIN_LABELS = [
    "≤ -3.0",
    "-3.0 to -1.0",
    "-1.0 to -0.25",
    "-0.25 to 0.25",
    "0.25 to 1.0",
    "1.0 to 3.0",
    "≥ 3.0",
]

WEIGHTED_SENTIMENT_BINS = [
    float("-inf"),
    -3.0,
    -1.0,
    -0.25,
    0.25,
    1.0,
    3.0,
    float("inf"),
]


def calculate_weighted_sentiment(article: dict) -> float | None:
    weighted_sentiment = article.get("weighted_sentiment")

    if weighted_sentiment is not None:
        return weighted_sentiment

    sentiment_score = article.get("sentiment_score")
    sentiment_magnitude = article.get("sentiment_magnitude")

    if sentiment_score is None or sentiment_magnitude is None:
        return None

    return sentiment_score * sentiment_magnitude


def build_sentiment_dataframe(articles: list[dict]) -> pd.DataFrame:
    rows = []

    for article in articles:
        if article.get("sentiment_analysis_status") != "success":
            continue

        sentiment_score = article.get("sentiment_score")
        sentiment_magnitude = article.get("sentiment_magnitude")
        weighted_sentiment = calculate_weighted_sentiment(article)

        if (
            sentiment_score is None
            or sentiment_magnitude is None
            or weighted_sentiment is None
        ):
            continue

        rows.append(
            {
                "sentiment_score": sentiment_score,
                "sentiment_magnitude": sentiment_magnitude,
                "weighted_sentiment": weighted_sentiment,
            }
        )

    return pd.DataFrame(rows)


def build_weighted_sentiment_distribution(sentiment_df: pd.DataFrame) -> pd.DataFrame:
    if sentiment_df.empty:
        return pd.DataFrame(columns=["weighted_sentiment_range", "article_count"])

    distribution_source_df = sentiment_df.copy()

    distribution_source_df["weighted_sentiment_range"] = pd.cut(
        distribution_source_df["weighted_sentiment"],
        bins=WEIGHTED_SENTIMENT_BINS,
        labels=WEIGHTED_SENTIMENT_BIN_LABELS,
        include_lowest=True,
    )

    distribution_df = (
        distribution_source_df["weighted_sentiment_range"]
        .value_counts(sort=False)
        .reset_index()
    )

    distribution_df.columns = ["weighted_sentiment_range", "article_count"]
    distribution_df["weighted_sentiment_range"] = distribution_df[
        "weighted_sentiment_range"
    ].astype(str)

    return distribution_df


def render_weighted_sentiment_distribution_chart(
    distribution_df: pd.DataFrame,
) -> None:
    if distribution_df.empty:
        return

    st.subheader("Weighted Sentiment Distribution")

    fig = px.bar(
        distribution_df,
        x="weighted_sentiment_range",
        y="article_count",
        labels={
            "weighted_sentiment_range": "Weighted sentiment range",
            "article_count": "Article count",
        },
    )

    fig.update_layout(
        dragmode=False,
        margin={
            "l": 10,
            "r": 10,
            "t": 10,
            "b": 10,
        },
    )

    fig.update_xaxes(
        fixedrange=True,
        tickangle=-30,
    )

    fig.update_yaxes(
        fixedrange=True,
        rangemode="tozero",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": False,
            "displayModeBar": False,
            "staticPlot": False,
        },
    )


def render_sentiment_summary(articles: list[dict]) -> None:
    sentiment_df = build_sentiment_dataframe(articles)

    if sentiment_df.empty:
        st.info(
            "No sentiment results yet. Search and analyze articles to populate this overview."
        )
        return

    median_weighted_sentiment = sentiment_df["weighted_sentiment"].median()
    average_weighted_sentiment = sentiment_df["weighted_sentiment"].mean()
    average_score = sentiment_df["sentiment_score"].mean()
    average_magnitude = sentiment_df["sentiment_magnitude"].mean()

    st.subheader("Sentiment Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Median weighted", f"{median_weighted_sentiment:.3f}")
    col2.metric("Average weighted", f"{average_weighted_sentiment:.3f}")
    col3.metric("Average score", f"{average_score:.3f}")
    col4.metric("Average magnitude", f"{average_magnitude:.3f}")

    distribution_df = build_weighted_sentiment_distribution(sentiment_df)
    render_weighted_sentiment_distribution_chart(distribution_df)

    st.caption(
        "Weighted sentiment is calculated as sentiment score multiplied by sentiment "
        "magnitude. Negative values indicate negative sentiment with emotional strength; "
        "positive values indicate positive sentiment with emotional strength. "
        "The median weighted value is shown because it is less affected by unusually "
        "strong outlier articles than the average."
    )


def build_entity_dataframe(articles: list[dict]) -> pd.DataFrame:
    rows = []

    for article in articles:
        if article.get("entity_extraction_status") != "success":
            continue

        for entity in article.get("entities") or []:
            name = entity.get("name")
            entity_type = entity.get("type")
            salience = entity.get("salience")

            if not name:
                continue

            rows.append(
                {
                    "name": name,
                    "type": entity_type or "UNKNOWN",
                    "salience": salience if salience is not None else 0.0,
                }
            )

    return pd.DataFrame(rows)


def build_entity_summary(
    entity_df: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    if entity_df.empty:
        return pd.DataFrame(
            columns=[
                "name",
                "type",
                "mentions",
                "total_salience",
                "average_salience",
            ]
        )

    summary_df = (
        entity_df.groupby(["name", "type"], as_index=False)
        .agg(
            mentions=("name", "count"),
            total_salience=("salience", "sum"),
            average_salience=("salience", "mean"),
        )
        .sort_values(
            ["total_salience", "mentions", "average_salience"],
            ascending=False,
        )
        .head(top_n)
    )

    summary_df["total_salience"] = summary_df["total_salience"].round(3)
    summary_df["average_salience"] = summary_df["average_salience"].round(3)

    return summary_df


def render_entity_overview(articles: list[dict]) -> None:
    entity_df = build_entity_dataframe(articles)

    if entity_df.empty:
        st.info("No extracted entities yet. Search and analyze articles first.")
        return

    most_important_entities_df = build_entity_summary(
        entity_df=entity_df,
        top_n=10,
    )

    st.subheader("Most Important Entities")

    st.dataframe(
        most_important_entities_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Entities are ranked by total salience first, then by mention count. "
        "Salience measures how important the entity is within the analyzed article text."
    )


def render_overview_tab(articles: list[dict]) -> None:
    if not articles:
        st.info("No search results yet. Use the search configuration in the sidebar.")
        return

    render_sentiment_summary(articles)

    st.divider()

    render_entity_overview(articles)