# Stock News Sentiment Dashboard

A web application for analyzing sentiment and entities in company-related news articles, built for stock traders and investors who want data-driven insight into market sentiment, without having decisions made for them.

## Purpose

Traders and investors need to stay on top of news around companies in their portfolio or watchlist. This dashboard helps by:

- Fetching recent news articles via Google News for any company, ticker, or keyword
- Extracting the full article text and running sentiment analysis (score, magnitude) using Google Cloud Natural Language API
- Extracting named entities (organizations, people, events, locations, etc.) from each article
- Classifying article content into topics (e.g. Finance, Technology, Business) using NLP
- Storing analyzed articles in a persistent database for future reference
- Allowing users to query their article database with flexible filters and export results

The underlying philosophy is **transparency and user control**: the app surfaces as much information as possible (how many articles were fetched, how many failed extraction, sentiment scores per article and per sentence, extracted entities with salience scores) so that the trader can draw their own conclusions rather than relying on a black-box summary.

## Who It Is For

Stock traders and investors who:

- Monitor news sentiment around specific companies or sectors
- Want to build up a personal database of relevant articles over time
- Prefer to see the raw data and decide for themselves, rather than receive an opinionated signal

## Features

### Search Web
Search Google News in two modes:

**Keyword mode** — search by company name, ticker, or any keyword. Configure:
- Country edition (US, UK, CH, AU, CA, SG)
- Time period (1d, 7d, 30d)
- Sort order (relevance or newest first)
- Target number of articles to extract

**Topic mode** — browse Google News by category: WORLD, NATION, BUSINESS, TECHNOLOGY, ENTERTAINMENT, SPORTS, SCIENCE, HEALTH.

For each article the app shows:
- Sentiment score (−1.0 negative to +1.0 positive) and magnitude
- Sentence-level sentiment breakdown
- Extracted named entities with type and salience score
- Content categories (e.g. `/Finance/Investing`) via NLP classification
- How many articles passed or failed text extraction, and why

Analyzed articles can be selectively saved to the database using per-article checkboxes.

### Search Database
Query the stored article database with filters:
- Company or keyword (matched against extracted entity names)
- Sentiment score range
- Publication date range

Results can be exported as **CSV**, **JSON**, or **Excel**. Individual articles can be selected and deleted from the database.

### Overview Tab
For any set of articles (live search or database query), the Overview tab shows:
- Average sentiment across articles
- Sentiment distribution chart
- Top extracted entities
- AI-generated summary and company/ticker detection via Gemini (Vertex AI)

### Charts Tab
Stock price charts for companies detected by Gemini in the current article set, ranked by entity salience across articles.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| Hosting | Google App Engine (Flexible) |
| News Feed | Google News RSS via `gnews` |
| Article Extraction | `newspaper3k` |
| Sentiment, Entity & Classification | Google Cloud Natural Language API |
| AI Summary & Ticker Detection | Gemini 2.5 Flash via Vertex AI |
| Database | Firestore in Datastore mode |
| Stock Charts | yFinance + Plotly |

## Local Development

**Prerequisites:** Python 3.12, a Google Cloud project with the following APIs enabled:
- Cloud Natural Language API
- Cloud Datastore API
- Vertex AI API

**Setup:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Place your Google Cloud service account key at `credentials/google-cloud-key.json`.

**Run:**

```bash
streamlit run app.py
```

## Deployment

Deployed to Google App Engine Flexible using a custom Docker runtime:

```bash
gcloud app deploy
```

The app runs on port 8080 as required by App Engine.
