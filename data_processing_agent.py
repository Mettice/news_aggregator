from crewai import Agent
from elasticsearch import Elasticsearch
from transformers import pipeline, Pipeline
from pydantic import Field, ConfigDict
from typing import Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DataProcessingAgent(Agent):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    es: Elasticsearch = Field(default=None, exclude=True)
    summarizer: Optional[Pipeline] = Field(default=None, exclude=True)
    classifier: Optional[Pipeline] = Field(default=None, exclude=True)

    def __init__(self):
        super().__init__(
            name="News Processing Agent",
            role="News Processor",
            backstory="I am an agent that processes and enriches news articles with summaries and categories",
            description="Agent that processes and enriches news articles",
            goal="Enhance news articles with categories and summaries"
        )
        self.es = Elasticsearch(
            [{'scheme': 'http', 'host': 'localhost', 'port': 9200}],
            basic_auth= (os.getenv("elastic_username"), os.getenv("elastic_password"))
        )
        try:
            print("Loading NLP models...")

            self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
            self.classifier = pipeline("zero-shot-classification")
            print("NLP models loaded successfully")
        except Exception as e:
            print(f"Error loading NLP models: {str(e)}")
            self.summarizer = None
            self.classifier = None
        
    def process_articles(self):
        # Get unprocessed articles
        results = self.es.search(
            index="news",
            body={
                "query": {
                    "bool": {
                        "must_not": {
                            "exists": {
                                "field": "summary"
                            }
                        }
                    }
                },
                "size": 10
            }
        )
        
        for hit in results['hits']['hits']:
            try:
                article = hit['_source']
                print(f"\nProcessing: {article['title']}")
                
                # Skip articles with insufficient content
                if not article.get('content') or len(article['content'].strip()) < 100:
                    print(f"Skipping article due to insufficient content (length: {len(article.get('content', ''))}")
                    article['summary'] = article.get('content', '')
                    article['category'] = article.get('category', 'Uncategorized')
                    article['category_score'] = 0.0
                else:
                    # Generate summary with dynamic max_length
                    try:
                        if self.summarizer:
                            content_length = len(article['content'])
                            # Set max_length to half the content length, but keep it between 30 and 130
                            max_length = min(max(30, content_length // 2), 130)
                            min_length = min(max_length // 2, 30)
                            
                            summary = self.summarizer(
                                article['content'][:1024], 
                                max_length=max_length,
                                min_length=min_length,
                                do_sample=False
                            )[0]['summary_text']
                            article['summary'] = summary
                            print(f"Generated summary: {summary[:100]}...")
                        else:
                            article['summary'] = article['content'][:200] + "..."
                    except Exception as e:
                        print(f"Error generating summary: {str(e)}")
                        article['summary'] = article['content'][:200] + "..."
                    
                    # Categorize the article
                    try:
                        if self.classifier and len(article['content'].strip()) > 100:
                            categories = ["Politics", "Technology", "Business", "Sports", "Entertainment", "Health", "Science"]
                            result = self.classifier(
                                article['content'][:512], 
                                candidate_labels=categories,
                                hypothesis_template="This text is about {}.",
                                multi_label=False
                            )
                            article['category'] = result['labels'][0]
                            article['category_score'] = float(result['scores'][0])
                            print(f"Categorized as: {article['category']} (confidence: {article['category_score']:.2f})")
                        else:
                            article['category'] = article.get('category', 'Uncategorized')
                            article['category_score'] = 0.0
                    except Exception as e:
                        print(f"Error categorizing article: {str(e)}")
                        article['category'] = article.get('category', 'Uncategorized')
                        article['category_score'] = 0.0
                
                # Update in Elasticsearch
                self.es.update(
                    index='news',
                    id=hit['_id'],
                    body={'doc': article}
                )
                
                print(f"Successfully processed: {article['title']}")
                
            except Exception as e:
                print(f"Error processing article {hit['_id']}: {str(e)}")
                continue
    
    def run(self):
        """Execute the agent's processing task"""
        if not self.summarizer or not self.classifier:
            print("Warning: NLP models not loaded. Will use basic text processing.")
        
        print("\nStarting article processing...")
        self.process_articles()
        print("\nArticle processing completed")
        return "Processing task completed successfully"

if __name__ == "__main__":
    agent = DataProcessingAgent()
    agent.run()
