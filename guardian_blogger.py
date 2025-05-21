
# guardian_blogger.py
import os
import requests
import logging
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Configuration
BLOGGER_BLOG_ID = "8297266893026626512"
GUARDIAN_API_KEY = "f962d128-a739-4249-b704-cfa30b55e736"
GUARDIAN_ENDPOINT = "https://content.guardianapis.com/search"
POSTED_IDS_FILE = 'posted_articles.txt'

def get_posted_ids():
    try:
        if os.path.exists(POSTED_IDS_FILE):
            with open(POSTED_IDS_FILE, 'r') as f:
                return set(line.strip() for line in f.readlines())
        return set()
    except Exception as e:
        logger.error(f"Error reading posted IDs: {str(e)}")
        return set()

def save_posted_id(article_id):
    try:
        with open(POSTED_IDS_FILE, 'a') as f:
            f.write(f"{article_id}\n")
        return True
    except Exception as e:
        logger.error(f"Error saving ID: {str(e)}")
        return False

def get_guardian_articles():
    """Fetch latest articles from The Guardian"""
    params = {
        'order-by': 'newest',
        'show-fields': 'body,thumbnail,headline,byline',
        'show-sections': 'true',  # Add section information
        'api-key': GUARDIAN_API_KEY
    }
    
    try:
        response = requests.get(GUARDIAN_ENDPOINT, params=params)
        response.raise_for_status()
        return process_guardian_response(response.json())
    except Exception as e:
        logger.error(f"Guardian API error: {str(e)}")
        return []

def process_guardian_response(data):
    articles = []
    for result in data['response']['results']:
        articles.append({
            'id': result['id'],
            'title': result['fields'].get('headline', ''),
            'author': result['fields'].get('byline', 'The Guardian'),
            'content': result['fields'].get('body', ''),
            'image': result['fields'].get('thumbnail', ''),
            'url': result['webUrl'],
            'date': result['webPublicationDate'],
            'category': result.get('sectionName', 'General')  # Add category
        })
    return articles

def format_article_html(article):
    date_str = datetime.fromisoformat(article['date'][:-1]).strftime('%B %d, %Y')
    content = article['content'].replace('\n', '<br>')
    image_tag = f'<img src="{article["image"]}" style="max-width:100%">' if article['image'] else ''
    
    return f"""
    <div style="max-width:800px; margin:0 auto; font-family:Arial, sans-serif;">
        <h1>{article['title']}</h1>
        <div class="meta">
            By {article['author']} | {date_str}
        </div>
        {image_tag}
        <div class="content">
            {content}
        </div>
        <div class="source">
            Original: <a href="{article['url']}">Read on The Guardian</a>
        </div>
    </div>
    """

def post_to_blogger(article):
    try:
        if not os.path.exists('token.json'):
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json',
                scopes=['https://www.googleapis.com/auth/blogger']
            )
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        creds = Credentials.from_authorized_user_file('token.json')
        service = build('blogger', 'v3', credentials=creds)
        
        post_body = {
            'title': article['title'],
            'content': format_article_html(article),
            'labels': [article['category'], 'News Update']  # Add category as label
        }
        
        post = service.posts().insert(
            blogId=BLOGGER_BLOG_ID,
            body=post_body
        ).execute()
        
        return post.get('url', '')
    
    except Exception as e:
        logger.error(f"Blogger error: {str(e)}")
        return None

def main():
    posted_ids = get_posted_ids()
    new_articles = [a for a in get_guardian_articles() if a['id'] not in posted_ids]
    
    if not new_articles:
        logger.info("No new articles to post")
        return True

    success = False
    for article in new_articles[:2]:  # Post max 2 articles
        if post_url := post_to_blogger(article):
            save_posted_id(article['id'])
            logger.info(f"Posted [{article['category']}]: {post_url}")
            success = True
    return success

if __name__ == "__main__":
    exit(0 if main() else 1)
