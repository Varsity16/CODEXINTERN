import os
import requests
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

print(f"API Key Loaded: {NEWS_API_KEY[:4]}... (should not be None)")

if not NEWS_API_KEY:
    print("\nERROR: Could not load NEWS_API_KEY from .env file. Please check the file.")
else:

    base_url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    
    try:
        print(f"Attempting to connect to: {base_url}")
        response = requests.get(base_url)
        print(f"Status Code: {response.status_code}")


        if response.status_code == 200:
            data = response.json()
            

            if data.get('status') == 'ok':
                articles = data.get('articles', [])
                
                if articles:
                    print("\n--- Top Headlines ---")

                    for i, article in enumerate(articles):
                        print(f"{i + 1}. {article.get('title')}")
                    print("---------------------\n")
                else:
                    print("\nAPI request was successful, but no articles were found for this query.")
            
            else:

                print(f"\nAPI returned an error: {data.get('message')}")
        
        else:

            print(f"\nHTTP Error: Failed to retrieve data. Status code: {response.status_code}")
            print(f"Response: {response.text}")


    except requests.exceptions.RequestException as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        print("This is likely a network problem. Check your internet connection or firewall.")