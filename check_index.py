import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# Load environment variables
load_dotenv()

def check_index():
    try:
        # Initialize connection
        es = Elasticsearch(
            cloud_id="news_aggregator:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJGU1NzU1MDM3OWM4YTQzZTZiZTRjNzQ3NmIwYTlkNmY0JDU1ZWU4ZDQyNTdkYTRhMmY4ZDE4MGZlY2Q4NzRlZTdl",
            basic_auth=(os.getenv("elastic_username"), os.getenv("elastic_password")),
            timeout=30
        )
        
        # Check if index exists
        if es.indices.exists(index="news"):
            # Get document count
            count = es.count(index="news")
            print(f"Index 'news' exists with {count['count']} documents")
            
            # Get a sample document
            sample = es.search(
                index="news",
                body={"size": 1}
            )
            if sample["hits"]["hits"]:
                print("\nSample document:")
                print(sample["hits"]["hits"][0]["_source"])
        else:
            print("Index 'news' does not exist")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_index()