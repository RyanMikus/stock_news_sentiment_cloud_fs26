# Project Specification

## 1. Project Title

Stock News Sentiment Dashboard

## 2. Project Goal

The goal of this project is to design and implement a reactive web application for analyzing company-related financial news articles.

The application helps users understand recent news about companies and stocks by combining:

- recent company news
- stock price data
- sentiment analysis
- entity extraction
- AI-generated summaries
- related stock suggestions
- quantitative stock indicators
- visual dashboards
- data export functionality

The application is implemented in Python and deployed on Google Cloud App Engine.

## 3. Target Users

The target users are:

- stock investors
- traders
- financial analysts
- students
- users interested in company news and market sentiment

The application is not intended to provide financial advice. It is intended as an informational and analytical tool.

## 4. Main Use Case

A user opens the application and sees recent financial news on the homepage. The user can click on a news article or stock ticker to open a stock detail page.

On the stock detail page, the user can view:

- recent news about the selected company
- sentiment scores for the articles
- extracted entities
- stock price charts
- selected quantitative stock metrics
- AI-generated summaries
- related stock suggestions

The user can also search for companies manually and export analyzed data.

## 5. Functional Requirements

### 5.1 Homepage

The application provides a homepage that displays recent financial or company-related news.

Each news item should display:

- article title
- source
- publication date
- short description if available
- detected company name if available
- detected ticker symbol if available
- sentiment indicator if the article has already been analyzed

Clicking a news item or detected ticker opens the corresponding stock detail page.

### 5.2 Company / Stock Search

The user can search for news related to a company using:

- company name
- ticker symbol
- keyword

Example searches:

- Apple
- AAPL
- NVIDIA
- NVDA
- Tesla
- TSLA

The application retrieves recent articles using the Google News RSS feed through the `gnews` Python package.

### 5.3 Article Retrieval

The application uses a multi-step article retrieval and extraction strategy.

First, `gnews` is used to retrieve news metadata, including:

- article title
- description
- source
- publication date
- article URL

Then, the application attempts to retrieve and extract the full article text from the URL.

The full-text extraction strategy is:

1. Use `newspaper3k` as the primary full-text article extraction library.
2. If `newspaper3k` fails, returns empty text, or returns unusable cookie/consent-page text, use `trafilatura` as an open-source fallback extraction library.
3. If both `newspaper3k` and `trafilatura` fail, use the article title and description from `gnews` as fallback text.
4. Store the extraction status and error reason if available.
5. Continue processing the remaining articles.

Possible extraction statuses:

- `success`
- `partial`
- `blocked`
- `failed`

The application does not try to bypass paywalls, protected content, login pages, or access restrictions. It only tries alternative open-source text extraction methods and then falls back to available metadata.

### 5.4 Cookie Pages, Paywalls, and Blocked Articles

Some news websites may block automatic article extraction because of:

- cookie consent pages
- paywalls
- bot protection
- JavaScript-rendered content
- unavailable or redirected article URLs

The application should not fail when this happens.

The application uses the following fallback strategy:

- first try to extract the full article text with `newspaper3k`
- if `newspaper3k` fails or returns cookie/consent-page text, try `trafilatura`
- if `trafilatura` also fails, use the title and description from `gnews`
- mark the article with an extraction status such as `blocked`, `partial`, or `failed`
- store the original URL
- store the reason for the extraction problem if available
- continue processing the remaining articles

The first implementation will use:

- `gnews` for news metadata and URLs
- `newspaper3k` for primary article extraction
- `trafilatura` for open-source fallback extraction
- `gnews` title and description as final fallback text

### 5.5 Sentiment Analysis

The application analyzes article text using the Google Cloud Natural Language API.

For each article, the application stores:

- overall sentiment score
- sentiment magnitude
- sentence-level sentiment if available

Sentiment interpretation:

- score greater than 0: positive
- score less than 0: negative
- score close to 0: neutral
- high magnitude: strong emotional content

### 5.6 Entity Extraction

The application extracts named entities from article text using the Google Cloud Natural Language API.

Important entity types include:

- organizations
- persons
- locations
- events
- dates
- products
- industries
- company names
- ticker symbols if detected or inferred

Entities are stored together with the analyzed article.

### 5.7 Advanced Gemini Feature

The application implements the optional advanced AI feature using Gemini in Vertex AI.

Gemini is used for:

- summarizing one article
- summarizing multiple recent articles about a stock
- extracting advanced financial entities
- inferring ticker symbols when they are not explicitly mentioned
- identifying related companies
- suggesting related stocks
- explaining why a news event may be relevant to a company

The Google Cloud Natural Language API remains the main service for structured sentiment analysis and standard entity extraction.

Gemini is used as an advanced extension for natural-language summaries and deeper interpretation.

### 5.8 Stock Detail Page

Each stock has a detail page.

The stock detail page displays:

- company name
- ticker symbol
- latest available stock price
- stock price chart
- selected quantitative metrics
- recent related news
- article sentiment results
- aggregated sentiment for the stock
- extracted entities
- Gemini-generated stock news summary
- related stock suggestions

### 5.9 Stock Price Chart

The application displays stock price data for the selected company.

The user can select different time ranges, for example:

- 1 day
- 5 days
- 1 month
- 6 months
- 1 year

The chart should show the stock price development over time.

The first implementation may use `yfinance` for retrieving stock price data.

The chart can be implemented using Plotly.

### 5.10 Quantitative Stock Metrics

The application displays selected quantitative stock metrics.

Possible metrics include:

- current price
- previous close
- day high
- day low
- opening price
- trading volume
- market capitalization
- 52-week high
- 52-week low
- price-to-earnings ratio if available
- dividend yield if available
- beta if available
- sector
- industry
- exchange

The availability of metrics depends on the selected data source.

### 5.11 Related Stock Suggestions

The application suggests related stocks for the selected company.

Related stocks can be determined using one or more of the following methods:

- same sector
- same industry
- companies mentioned in the same articles
- organizations extracted from the same news article
- competitors identified by Gemini
- manually defined mappings for well-known companies

For each related stock suggestion, the application should display:

- ticker symbol
- company name if available
- reason for suggestion
- relation type

Example relation types:

- competitor
- same industry
- co-mentioned company
- supplier
- customer
- market peer

### 5.12 Data Storage

The application stores analyzed article data in Firestore in Datastore mode.

Stored data includes:

- article metadata
- full article text if available
- fallback text if full article extraction failed
- article extraction status
- article extraction error reason if available
- sentiment results
- extracted entities
- Gemini summary if available
- related ticker symbols
- timestamps

The stored data can be queried later by the application.

### 5.13 Querying Stored Data

The application supports querying stored data with filters.

Possible filters:

- company name
- ticker symbol
- industry
- sentiment score threshold
- publication date range
- source
- entity name
- article extraction status

Example queries:

- show all articles about NVIDIA
- show articles with negative sentiment
- show articles published in the last 7 days
- show articles mentioning Microsoft and OpenAI
- show technology-sector articles with positive sentiment
- show articles where full text extraction failed

### 5.14 Visualizations

The application provides visualizations for analysis results.

Possible visualizations:

- stock price line chart
- sentiment over time
- average sentiment per stock
- positive / neutral / negative article distribution
- most frequently mentioned entities
- sentiment comparison between related stocks
- article count per source
- article count per day
- article extraction success/failure distribution

Visualizations are created using Streamlit charts, Plotly, or Dash components.

### 5.15 Data Export

The application allows users to export query results.

Supported export formats:

- CSV
- JSON
- Excel

The first implementation will support at least CSV export.

Exported data may include:

- article title
- article URL
- source
- publication date
- company name
- ticker symbol
- sentiment score
- sentiment magnitude
- extracted entities
- Gemini summary
- related stocks
- article extraction status
- article extraction error reason

## 6. Non-Functional Requirements

### 6.1 Usability

The user interface should be clear and simple.

The application should provide:

- a homepage
- a search input
- stock detail pages
- readable article cards
- clear charts
- visible error messages
- export buttons

### 6.2 Reliability

The application should continue running even if:

- no news articles are found
- an article URL is unreachable
- article text extraction fails
- an article is blocked by a cookie page
- an article is behind a paywall
- a stock ticker cannot be detected
- stock price data is unavailable
- an API request fails

### 6.3 Performance

The application should avoid unnecessary API calls.

Possible optimization strategies:

- cache recent stock price data
- store analyzed articles in Datastore
- reuse stored analysis results
- only call Gemini when needed
- limit the number of articles processed per request
- avoid repeated extraction attempts for known blocked articles

### 6.4 Security

The application must not store secrets in Git.

The following files must not be committed:

- service account JSON keys
- `.env` files
- local credential files
- virtual environments

Google Cloud credentials should be handled through environment variables.

The application will not attempt to bypass paywalls or access protected content.

### 6.5 Deployment

The application is deployed on Google Cloud App Engine using Python 3.12.

The project includes:

- `app.yaml`
- `requirements.txt`
- Python source files
- documentation
- `.gitignore`

## 7. Technology Stack

### Programming Language

- Python 3.12

### Web Framework

Preferred:

- Streamlit

Alternative:

- Dash

### Cloud Platform

- Google Cloud Platform
- Google App Engine
- Firestore in Datastore mode
- Google Cloud Natural Language API
- Gemini in Vertex AI

### News and Article Extraction Libraries

- `gnews`: retrieves news metadata and URLs from Google News RSS
- `newspaper3k`: primary full-text article extraction library
- `trafilatura`: open-source fallback library for robust web text extraction

### Financial Data Libraries

- `yfinance`: retrieves stock price data and selected quantitative stock metrics

### Data Processing Libraries

- `pandas`

### Visualization Libraries

- Plotly
- Streamlit chart components

### Storage

- Firestore in Datastore mode

## 8. Proposed Project Structure

```text
26FS_CloudComputing/
├── app.py
├── config.py
├── requirements.txt
├── requirements-lock.txt
├── app.yaml
├── README.md
├── .gitignore
├── docs/
│   └── project_specification.md
├── services/
│   ├── news_service.py
│   ├── article_service.py
│   ├── sentiment_service.py
│   ├── entity_service.py
│   ├── gemini_service.py
│   ├── stock_service.py
│   └── datastore_service.py
├── pages/
│   ├── home.py
│   ├── stock_detail.py
│   ├── search.py
│   └── stored_data.py
└── utils/
    ├── ticker_utils.py
    ├── formatting.py
    └── error_handling.py
```

## 9. Data Model

### 9.1 Article Entity

Kind: `Article`

Properties:

- `article_id`
- `title`
- `url`
- `source`
- `published_at`
- `description`
- `company_keyword`
- `detected_company_name`
- `detected_ticker`
- `full_text`
- `fallback_text`
- `text_extraction_status`
- `extraction_error_reason`
- `sentiment_score`
- `sentiment_magnitude`
- `entities`
- `gemini_summary`
- `related_tickers`
- `created_at`
- `updated_at`

Possible values for `text_extraction_status`:

- `success`
- `partial`
- `blocked`
- `failed`

### 9.2 Stock Entity

Kind: `Stock`

Properties:

- `ticker`
- `company_name`
- `sector`
- `industry`
- `exchange`
- `currency`
- `last_price`
- `previous_close`
- `open`
- `day_high`
- `day_low`
- `volume`
- `market_cap`
- `pe_ratio`
- `dividend_yield`
- `beta`
- `fifty_two_week_high`
- `fifty_two_week_low`
- `last_updated`

### 9.3 StockPrice Entity

Kind: `StockPrice`

Properties:

- `ticker`
- `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `interval`
- `range`
- `created_at`

### 9.4 RelatedStock Entity

Kind: `RelatedStock`

Properties:

- `ticker`
- `related_ticker`
- `related_company_name`
- `relation_type`
- `reason`
- `confidence`
- `source`
- `created_at`

### 9.5 AnalysisRun Entity

Kind: `AnalysisRun`

Properties:

- `run_id`
- `query`
- `ticker`
- `started_at`
- `finished_at`
- `number_of_articles_found`
- `number_of_articles_analyzed`
- `number_of_failed_articles`
- `number_of_blocked_articles`
- `status`
- `error_message`

## 10. User Interface Pages

### 10.1 Homepage

Purpose:

Display recent financial news and guide the user toward company or stock pages.

Components:

- page title
- recent news section
- search bar
- news cards
- detected ticker links
- quick links to popular stocks
- optional sentiment indicators

### 10.2 Stock Detail Page

Purpose:

Display all relevant information for one selected stock.

Components:

- stock header
- current price
- stock price chart
- time range selector
- key quantitative metrics
- recent news articles
- sentiment results
- Gemini summary
- related stocks
- export button

### 10.3 Search Page

Purpose:

Allow users to search for company-related news manually.

Components:

- company or ticker search input
- number of articles selector
- date range selector if available
- search button
- results table
- analyze button
- save results button

### 10.4 Stored Data Page

Purpose:

Allow users to query previously stored results.

Components:

- ticker filter
- company filter
- sentiment filter
- date filter
- source filter
- extraction status filter
- results table
- visualizations
- export button

## 11. Main Application Workflow

### 11.1 Homepage Workflow

1. Application loads recent business news.
2. Application displays article titles and descriptions.
3. Application detects possible company names or ticker symbols.
4. User clicks a ticker or article.
5. Application opens the stock detail page.

### 11.2 Search and Analysis Workflow

1. User enters a company name or ticker.
2. Application fetches related news using `gnews`.
3. Application extracts article text using `newspaper3k`.
4. If `newspaper3k` fails, the application tries `trafilatura`.
5. If article extraction still fails, the application uses title and description from `gnews` as fallback text.
6. Application analyzes sentiment using the Natural Language API.
7. Application extracts entities using the Natural Language API.
8. Application optionally calls Gemini for summary and advanced extraction.
9. Application stores the result in Datastore.
10. Application displays the results in the UI.

### 11.3 Stock Detail Workflow

1. User opens a stock page.
2. Application loads stock price data.
3. Application loads quantitative metrics.
4. Application loads stored or newly retrieved news.
5. Application displays article sentiment.
6. Application generates or loads a Gemini summary.
7. Application suggests related stocks.
8. User can export the data.

## 12. Error Handling

The application handles the following errors:

### 12.1 No News Found

If no news is found, the application displays a message and allows the user to try another keyword.

### 12.2 Article Extraction Failed

If full article extraction fails with `newspaper3k`, the application tries `trafilatura`.

If both extraction methods fail, the application uses the title and description from `gnews` as fallback text.

The article is marked with an extraction status such as `partial` or `failed`.

### 12.3 Article Blocked by Cookie Page or Paywall

If the article content appears to be a cookie page, consent page, paywall, or bot-protection page, the application does not crash.

Instead, it:

- stores the article metadata
- stores the original URL
- tries `trafilatura` if `newspaper3k` failed
- uses title and description as fallback text if full extraction is not possible
- marks the extraction status as `blocked`
- stores an extraction error reason if possible
- continues with the next article

### 12.4 Natural Language API Error

If sentiment analysis or entity extraction fails, the application stores the article with an error status.

### 12.5 Gemini Error

If Gemini summarization fails, the application continues without the AI summary.

### 12.6 Stock Data Unavailable

If stock price data is unavailable, the application still displays news and sentiment analysis.

### 12.7 Datastore Error

If storing data fails, the application displays an error message and does not crash.

## 13. Implementation Phases

### Phase 1: Core Required Project

Goal:

Build the required base application.

Tasks:

- create Streamlit or Dash application
- implement company news search
- fetch news metadata and URLs using `gnews`
- extract article text using `newspaper3k`
- add `trafilatura` as fallback extraction method
- implement fallback to `gnews` title and description
- analyze sentiment with Google Cloud Natural Language API
- extract entities
- store analyzed articles in Datastore
- display basic results
- export results as CSV

### Phase 2: Stock Detail Pages

Goal:

Add stock-centered functionality.

Tasks:

- detect or infer ticker symbols
- create stock detail page
- fetch stock price data using `yfinance`
- display stock price chart
- display basic stock metrics
- link articles to stock pages

### Phase 3: Homepage

Goal:

Create a useful starting page.

Tasks:

- display recent financial news
- show detected tickers
- link news items to stock pages
- add quick search functionality

### Phase 4: Advanced Gemini Features

Goal:

Implement the optional advanced AI functionality.

Tasks:

- summarize individual articles
- summarize multiple articles for one stock
- infer missing ticker symbols
- extract related companies
- generate explanation of news relevance
- suggest related stocks

### Phase 5: Visualizations and Export

Goal:

Improve analysis quality and usability.

Tasks:

- add sentiment-over-time chart
- add article distribution chart
- add entity frequency chart
- add extraction success/failure chart
- add stock comparison view if time allows
- implement CSV export
- optionally implement JSON or Excel export

### Phase 6: Deployment and Documentation

Goal:

Prepare final submission.

Tasks:

- configure `app.yaml`
- verify `requirements.txt`
- test local execution
- deploy to Google App Engine
- write short documentation
- prepare presentation

## 14. Minimum Viable Product

The minimum working version must include:

- company news search
- news metadata and URL retrieval with `gnews`
- article text extraction with `newspaper3k`
- fallback extraction with `trafilatura`
- fallback to `gnews` title and description if extraction fails
- sentiment analysis
- entity extraction
- Datastore storage
- basic result display
- basic visualization
- CSV data export

## 15. Extended Version

The extended version should include:

- homepage with recent news
- stock detail pages
- stock price charts
- quantitative stock metrics
- related stock suggestions
- Gemini summaries
- advanced entity extraction
- improved dashboards
- optional JSON or Excel export

## 16. Risks and Mitigation

### Risk: Scope too large

Mitigation:

Implement the required base functionality first, then add extensions step by step.

### Risk: Article extraction fails for some websites

Mitigation:

Use `newspaper3k` first, then try `trafilatura`, then use title and description from `gnews` as fallback text.

### Risk: Cookie pages, paywalls, or bot protection block article extraction

Mitigation:

Do not bypass protected content. Mark the article as blocked and continue with fallback text.

### Risk: API costs or quotas

Mitigation:

Limit the number of articles per search and reuse stored results.

### Risk: Stock data source limitations

Mitigation:

Use stock data only for visualization and prototype purposes.

### Risk: Gemini integration takes too much time

Mitigation:

Keep Gemini as an extension after the Natural Language API workflow works.

## 17. Success Criteria

The project is successful if:

- the application runs locally
- the application can be deployed to Google App Engine
- users can search company news
- news metadata and URLs are retrieved with `gnews`
- article extraction uses `newspaper3k`
- failed article extraction is handled with `trafilatura` or fallback metadata
- blocked or failed article extraction is handled gracefully
- sentiment scores are displayed
- entities are extracted
- analyzed data is stored in Datastore
- stored data can be queried
- results can be visualized
- results can be exported as CSV
- at least one Gemini-based advanced feature is implemented

## 18. Possible Future Extensions

Possible future improvements:

- user accounts
- watchlist functionality
- alert system for negative news
- comparison of multiple stocks
- portfolio sentiment overview
- more advanced financial indicators
- integration with additional news APIs
- better ticker/company matching
- scheduled daily news analysis
- more robust article extraction using additional libraries