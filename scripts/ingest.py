import os
import uuid
import requests
import cohere
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models

# Load environment variables from the parent directory's .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# --- CONFIGURATION ---
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
COLLECTION_NAME = "news_articles"
REUTERS_SITEMAP_URL = "https://www.reuters.com/arc/outboundfeeds/sitemap-index/?outputType=xml"
ARTICLE_LIMIT = 50

# --- VALIDATE ENVIRONMENT ---
if not COHERE_API_KEY:
    raise ValueError("COHERE_API_KEY environment variable not found. Please check your .env file.")
if not QDRANT_URL:
    raise ValueError("QDRANT_URL must be set in the .env file.")

# --- INITIALIZE CLIENTS ---
co = cohere.Client(COHERE_API_KEY)
qdrant_client = QdrantClient(url=QDRANT_URL)

def get_article_urls_from_sitemap(sitemap_url, limit):
    """Fetches and parses sitemaps to get article URLs, filtering out non-article links."""
    print("Fetching article URLs from sitemap...")
    urls = []
    try:
        index_resp = requests.get(sitemap_url, timeout=10)
        index_soup = BeautifulSoup(index_resp.content, "lxml-xml")
        sitemap_links = [loc.text for loc in index_soup.find_all("loc")]

        if not sitemap_links:
            print("No sitemap links found in the index.")
            return []

        news_sitemap_url = None
        for link in sitemap_links:
            if 'news' in link or 'article' in link:
                 news_sitemap_url = link
                 break
        if not news_sitemap_url: news_sitemap_url = sitemap_links[0]

        print(f"Fetching articles from: {news_sitemap_url}")
        sitemap_resp = requests.get(news_sitemap_url, timeout=10)
        sitemap_soup = BeautifulSoup(sitemap_resp.content, "lxml-xml")
        
        for loc in sitemap_soup.find_all("loc"):
            url = loc.text
            if "reuters.com/resizer" not in url and ".jpg" not in url and ".png" not in url:
                urls.append(url)
            if len(urls) >= limit:
                break
        print(f"Found {len(urls)} potential article URLs.")
        return urls
    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []

def scrape_article_content(url):
    """Scrapes the main text content from a news article URL."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.content, "html.parser")
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

        main_content = soup.find("main", {"id": "main-content"})
        if main_content:
            paragraphs = main_content.find_all("p")
            content = " ".join([p.get_text(strip=True) for p in paragraphs])
            return title, content
            
        return title, ""
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None, None

def main():
    """Main function to run the ingestion pipeline."""
    print("--- Starting News Ingestion Pipeline ---")
    article_urls = get_article_urls_from_sitemap(REUTERS_SITEMAP_URL, ARTICLE_LIMIT)
    if not article_urls:
        print("No articles to process. Exiting.")
        return

    print("Setting up Qdrant collection...")
    try:
        qdrant_client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=1024, # CRITICAL: Vector size for Cohere's embed-english-v3.0
                distance=models.Distance.COSINE
            )
        )
        print("Collection setup complete.")
    except Exception as e:
        print(f"Error setting up Qdrant collection: {e}")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    all_points = []
    successful_scrapes = 0
    for i, url in enumerate(article_urls):
        print(f"Processing article {i+1}/{len(article_urls)}: {url}")
        title, content = scrape_article_content(url)
        if not content:
            print(f"  -> Skipping, no content found.")
            continue
        
        successful_scrapes += 1
        chunks = text_splitter.split_text(content)
        print(f"  -> Success! Split into {len(chunks)} chunks.")
        if not chunks: continue

        try:
            # Get embeddings from Cohere API
            response = co.embed(
                texts=chunks,
                model='embed-english-v3.0',
                input_type='search_document'
            )
            embeddings = response.embeddings
        except Exception as e:
            print(f"  -> Error getting embeddings from Cohere: {e}. Skipping article.")
            continue

        for chunk_text, embedding_vector in zip(chunks, embeddings):
            point = models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding_vector,
                payload={"text": chunk_text, "source_url": url, "title": title}
            )
            all_points.append(point)

    if all_points:
        print(f"\nSuccessfully scraped {successful_scrapes} articles.")
        print(f"Upserting {len(all_points)} points to Qdrant in batches...")
        # Upsert in batches to avoid potential timeout issues
        for i in range(0, len(all_points), 100):
            batch = all_points[i:i+100]
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch,
                wait=True
            )
        print("--- Ingestion Complete! ---")
    else:
        print(f"\nSuccessfully scraped {successful_scrapes} articles.")
        print("--- No data was ingested. ---")

if __name__ == "__main__":
    main()