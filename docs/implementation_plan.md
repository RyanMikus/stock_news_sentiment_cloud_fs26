
# Implementation Plan

## Phase 1: Local Base App

- Create Streamlit app
- Add homepage layout
- Add search input
- Display mock news data first
- Add basic navigation structure

## Phase 2: News Fetching

- Implement news service using gnews
- Search by company name or ticker
- Display article title, source, date, and URL

## Phase 3: Article Extraction

- Implement article text extraction using newspaper3k
- Add fallback if extraction fails
- Store extraction status

## Phase 4: Sentiment and Entity Analysis

- Connect Google Cloud Natural Language API
- Analyze sentiment
- Extract entities
- Display results in UI

## Phase 5: Datastore Storage

- Connect Firestore in Datastore mode
- Store analyzed articles
- Query stored articles
- Display stored results

## Phase 6: Stock Features

- Add yfinance stock price lookup
- Add stock detail page
- Add stock price chart
- Add quantitative metrics

## Phase 7: Gemini Extension

- Add Gemini article summary
- Add multi-article stock summary
- Add related stock suggestions

## Phase 8: Export and Polish

- Add CSV export
- Add charts
- Improve error handling
- Prepare deployment