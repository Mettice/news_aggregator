import streamlit as st
from elasticsearch import Elasticsearch, NotFoundError
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

# Must be the first Streamlit command
st.set_page_config(
    page_title="News Aggregator",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state if needed
if 'initialized' not in st.session_state:
    st.session_state.initialized = True

# Load environment variables
load_dotenv()

# Initialize Elasticsearch client with better error handling
@st.cache_resource(show_spinner=False)
def init_elasticsearch():
    try:
        # Get cloud configuration from secrets
        elastic_username = st.secrets["elastic_username"]
        elastic_password = st.secrets["elastic_password"]
        
        # Initialize Elasticsearch with Cloud ID
        es = Elasticsearch(
            cloud_id="news_aggregator:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJGU1NzU1MDM3OWM4YTQzZTZiZTRjNzQ3NmIwYTlkNmY0JDU1ZWU4ZDQyNTdkYTRhMmY4ZDE4MGZlY2Q4NzRlZTdl",
            basic_auth=(elastic_username, elastic_password)
        )

        # Test connection
        if not es.ping():
            st.error("⚠️ Could not connect to Elasticsearch. Please check your configuration.")
            st.stop()

        # Ensure index exists
        if not es.indices.exists(index="news"):
            es.indices.create(
                index="news",
                mappings={
                    "properties": {
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "summary": {"type": "text"},
                        "url": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "date": {"type": "date"},
                        "category": {"type": "keyword"},
                        "category_score": {"type": "float"},
                        "author": {"type": "keyword"}
                    }
                }
            )

        return es
    except Exception as e:
        st.error(f"⚠️ Error connecting to Elasticsearch: {str(e)}")
        st.stop()

# Initialize Elasticsearch
es = init_elasticsearch()

# Custom CSS with improved visibility and dark theme compatibility
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .article-card {
        background-color: #1E1E1E;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 1.5rem;
        border: 1px solid #333;
    }
    .article-title {
        color: #00ADB5 !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
        text-decoration: none;
    }
    .article-title:hover {
        color: #00FFF5 !important;
    }
    .article-meta {
        color: #888;
        font-size: 0.9em;
        margin-bottom: 0.5rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid #333;
    }
    .article-summary {
        background-color: #2D2D2D;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        color: #CCC;
        border-left: 3px solid #00ADB5;
    }
    .category-tag {
        background-color: #00ADB5;
        color: #1E1E1E;
        padding: 0.2rem 0.6rem;
        border-radius: 15px;
        font-size: 0.8em;
        font-weight: 500;
    }
    .confidence-score {
        color: #00FF9D;
        font-size: 0.8em;
        margin-left: 0.5rem;
    }
    .stButton button {
        width: 100%;
        background-color: #00ADB5 !important;
        color: white !important;
    }
    .stButton button:hover {
        background-color: #00FFF5 !important;
        color: #1E1E1E !important;
    }
    .article-content {
        color: #CCC;
        line-height: 1.6;
        padding: 1rem 0;
    }
    .read-more {
        color: #00ADB5;
        text-decoration: none;
        font-weight: 500;
    }
    .read-more:hover {
        color: #00FFF5;
    }
    .st-emotion-cache-1y4p8pa {
        padding: 1rem;
    }
    .stExpander {
        border-color: #333 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Header with improved styling
st.title('📰 News Aggregator')
st.caption('Your personalized news feed')

# Sidebar filters
st.sidebar.title("📊 Filters")

# Search
search_query = st.sidebar.text_input("🔍 Search articles")

# Get unique sources and categories from Elasticsearch
def get_unique_values(field):
    try:
        res = es.search(
            index="news",
            body={
                "size": 0,
                "aggs": {
                    "unique_values": {
                        "terms": {"field": f"{field}.keyword", "size": 100}
                    }
                }
            }
        )
        return [bucket["key"] for bucket in res["aggregations"]["unique_values"]["buckets"]]
    except Exception:
        return []

sources = get_unique_values("source")
categories = get_unique_values("category")

# Filters
source_filter = st.sidebar.multiselect(
    "📰 Sources",
    options=sources,
    default=sources
)

category_filter = st.sidebar.multiselect(
    "🏷️ Categories",
    options=categories,
    default=categories
)

# Date range filter
st.sidebar.subheader("📅 Date Range")
try:
    dates = es.search(
        index="news",
        body={
            "size": 0,
            "aggs": {
                "min_date": {"min": {"field": "date"}},
                "max_date": {"max": {"field": "date"}}
            }
        }
    )
    min_date = datetime.fromisoformat(dates["aggregations"]["min_date"]["value_as_string"].replace("Z", "+00:00"))
    max_date = datetime.fromisoformat(dates["aggregations"]["max_date"]["value_as_string"].replace("Z", "+00:00"))
    date_range = st.sidebar.date_input(
        "Select date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date()
    )
except Exception:
    date_range = None

# Sort options
sort_by = st.sidebar.selectbox(
    "🔀 Sort by",
    options=["Newest First", "Oldest First", "Relevance"]
)

def fetch_articles():
    try:
        # Build query
        must_conditions = []
        if search_query:
            must_conditions.append({
                "multi_match": {
                    "query": search_query,
                    "fields": ["title^2", "content", "summary"]
                }
            })
        
        if source_filter:
            must_conditions.append({"terms": {"source.keyword": source_filter}})
        
        if category_filter:
            must_conditions.append({"terms": {"category.keyword": category_filter}})
        
        if date_range:
            must_conditions.append({
                "range": {
                    "date": {
                        "gte": date_range[0].isoformat(),
                        "lte": date_range[1].isoformat()
                    }
                }
            })

        # Sort configuration
        sort_config = [{"date": {"order": "desc"}}]
        if sort_by == "Oldest First":
            sort_config = [{"date": {"order": "asc"}}]
        elif sort_by == "Relevance" and search_query:
            sort_config = ["_score"]

        query = {
            "query": {"bool": {"must": must_conditions}} if must_conditions else {"match_all": {}},
            "sort": sort_config,
            "size": 50
        }

        res = es.search(index="news", body=query)
        return [hit["_source"] for hit in res["hits"]["hits"]]
    except Exception as e:
        st.error(f"Error fetching articles: {str(e)}")
        return []

# Fetch and display articles
articles = fetch_articles()

# For article count
st.text(f"📚 Showing {len(articles)} articles")

# For article display
for article in articles:
    with st.container():
        # Title
        st.subheader(article["title"])
        
        # Metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"📰 {article['source']}")
        with col2:
            st.caption(f"📅 {article['date']}")
        with col3:
            st.caption(f"🏷️ {article.get('category', 'Uncategorized')}")
        
        # Summary
        if 'summary' in article:
            st.info(article["summary"])
        
        # Full article
        with st.expander("📖 Read Full Article"):
            st.write(article["content"])
            if 'url' in article:
                st.link_button("🔗 Read original article", article['url'])
        
        st.divider()

# Footer
st.caption("Made with ❤️ using Streamlit and Elasticsearch")