import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# Load environment variables
load_dotenv()

def test_connection():
    try:
        # Print environment variables (without password)
        print(f"Username: {os.getenv('elastic_username')}")
        print("Password: [hidden]")
        
        # Initialize connection
        es = Elasticsearch(
            cloud_id="news_aggregator:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJGU1NzU1MDM3OWM4YTQzZTZiZTRjNzQ3NmIwYTlkNmY0JDU1ZWU4ZDQyNTdkYTRhMmY4ZDE4MGZlY2Q4NzRlZTdl",
            basic_auth=(os.getenv("elastic_username"), os.getenv("elastic_password")),
            timeout=30
        )
        
        # Test connection
        info = es.info()
        print(f"Successfully connected to Elasticsearch {info['version']['number']}")
        return True
        
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()