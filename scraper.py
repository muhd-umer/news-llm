# scraper.py

import time
import random
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from googlesearch import search


class NewsScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        }
        self.session = requests.Session()

    def search_news(self, country: str, topic: str, num_results: int = 10) -> List[str]:
        query = f"{country} {topic} news"
        if country.lower() == "international":
            query = f"international {topic} news"

        urls = list(search(query, num=num_results, stop=num_results, pause=2))
        return urls

    def scrape_content(self, url: str) -> str:
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text(separator=" ", strip=True)

            # Remove extra whitespace
            text = " ".join(text.split())

            return text
        except requests.exceptions.RequestException as e:
            print(f"Error scraping {url}: {str(e)}")
            return ""

    def scrape_news(
        self, country: str, topics: List[str], urls_per_topic: int = 5
    ) -> Dict[str, List[Dict[str, str]]]:
        results = {}

        for topic in topics:
            urls = self.search_news(country, topic, urls_per_topic)
            topic_results = []

            for url in urls:
                content = self.scrape_content(url)
                if content:
                    topic_results.append({"url": url, "content": content})
                time.sleep(random.uniform(1, 3))  # Randomized sleep time

            results[topic] = topic_results

        return results


if __name__ == "__main__":
    # Test the scraper
    scraper = NewsScraper()
    country = "Australia"
    topics = ["entertainment"]
    results = scraper.scrape_news(country, topics, urls_per_topic=5)

    for topic, articles in results.items():
        print(f"\n{topic.capitalize()} News:")
        for article in articles:
            print(f"URL: {article['url']}")
            print(f"Content preview: {article['content'][:200]}...")
