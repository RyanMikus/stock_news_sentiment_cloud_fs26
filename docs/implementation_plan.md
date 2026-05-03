# Implementation Plan

## Phase 1: Local Base App

- Create Streamlit app
- Add homepage layout
- Add search input
- Display mock news data first
- Add basic navigation structure

## Phase 2: News Fetching

- Implement news service using `gnews`
- Search by company name, ticker, or keyword
- Add country selection
- Use United States as the default country
- Display article title, source, date, description, and Google News URL
- Keep news fetching separated from article extraction

## Phase 3: Article Extraction

- Decode Google News URLs using `googlenewsdecoder`
- Extract full article text using `newspaper3k`
- Store publisher URL, extraction status, and error reason
- Skip failed articles for sentiment analysis

## Phase 4: Sentiment and Entity Analysis

- Connect Google Cloud Natural Language API
- Analyze sentiment only for articles with successfully extracted full text
- Extract entities only for articles with successfully extracted full text
- Display sentiment score and magnitude in the UI
- Display extracted entities in the UI

## Phase 5: Datastore Storage

- Connect Firestore in Datastore mode
- Store analyzed article metadata
- Store original Google News URL
- Store decoded publisher URL
- Store full article text if extraction succeeded
- Store extraction status
- Store extraction error reason if available
- Store sentiment results if analysis succeeded
- Store extracted entities if analysis succeeded
- Query stored articles
- Display stored results

## Phase 6: Stock Features

- Add `yfinance` stock price lookup
- Add stock detail page
- Add stock price chart
- Add selected quantitative stock metrics
- Link articles and search results to stock detail pages where possible

## Phase 7: Gemini Extension

- Add Gemini article summary
- Add multi-article stock summary
- Add related stock suggestions
- Use Gemini for advanced interpretation only after the required Natural Language API workflow works
- Keep Google Cloud Natural Language API as the main tool for structured sentiment and entity analysis

## Phase 8: Export and Polish

- Add CSV export
- Add basic charts
- Add sentiment visualizations
- Add extraction success/failure visualization
- Improve error handling
- Prepare App Engine deployment