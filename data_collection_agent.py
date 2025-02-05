from crewai import Agent
import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from datetime import datetime
from pydantic import Field, ConfigDict
from typing import Dict
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

class DataCollectionAgent(Agent):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    es: Elasticsearch = Field(default=None, exclude=True)
    headers: Dict[str, str] = Field(default=None, exclude=True)
    news_api_key: str = Field(default=None, exclude=True)
    
    def __init__(self):
        super().__init__(
            name="News Collection Agent",
            role="News Collector",
            backstory="I am an agent that collects news articles from various sources and stores them in Elasticsearch",
            description="Agent that collects news articles from various sources",
            goal="Collect and store news articles in Elasticsearch"
        )
        
        # Get credentials from environment variables
        elastic_username = os.getenv("elastic_username")
        elastic_password = os.getenv("elastic_password")
        
        if not elastic_username or not elastic_password:
            raise ValueError("Elasticsearch credentials not found in environment variables")
            
        self.es = Elasticsearch(
            [{'scheme': 'http', 'host': 'localhost', 'port': 9200}],
            basic_auth=(elastic_username, elastic_password)
        )
        
        self.news_api_key = os.getenv("news_api_key")
        if not self.news_api_key:
            raise ValueError("NewsAPI key not found in environment variables")
            
        print(f"Elasticsearch connected: {self.es.info()}")


    def collect_from_newsapi(self):
        try:
            # Define categories to fetch
            categories = ['business', 'technology', 'science', 'health', 'entertainment']
            
            for category in categories:
                url = 'https://newsapi.org/v2/top-headlines'
                params = {
                    'apiKey': self.news_api_key,
                    'category': category,
                    'language': 'en',
                    'pageSize': 20,
                    'country': 'us'  # Add country parameter for better results
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                news_data = response.json()
                
                if news_data['status'] != 'ok':
                    print(f"Error fetching {category} news: {news_data.get('message', 'Unknown error')}")
                    continue
                
                for article in news_data['articles']:
                    try:
                        # Better content validation
                        title = article.get('title', '').strip()
                        content = article.get('content', article.get('description', '')).strip()
                        
                        # Skip articles with insufficient or duplicate content
                        if not title or not content or len(content) < 100:
                            print(f"Skipping article due to insufficient content: {title}")
                            continue
                            
                        # Format the article
                        doc = {
                            'title': title,
                            'content': content,
                            'url': article.get('url', ''),
                            'source': article.get('source', {}).get('name', 'Unknown'),
                            'date': article.get('publishedAt', datetime.now().isoformat()),
                            'category': category.title(),
                            'author': article.get('author', 'Unknown'),
                            'description': article.get('description', '')
                        }
                        
                        # Index the article
                        self.es.index(index='news', document=doc)
                        print(f"Indexed {category} article: {title}")
                        
                    except Exception as e:
                        print(f"Error processing article: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error in NewsAPI collection: {str(e)}")
    
    def run(self):
        """Execute the agent's news collection task"""
        print("Starting news collection...")
        self.collect_from_newsapi()
        print("News collection completed")
        return "News collection task completed successfully"

if __name__ == "__main__":
    agent = DataCollectionAgent()
    agent.run()
