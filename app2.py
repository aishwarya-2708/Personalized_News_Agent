


from flask import Flask, render_template, request, jsonify
import google.genai as genai
import requests
from dotenv import load_dotenv
import os
import feedparser

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"
NEWS_API_KEY = os.getenv("NEWSAPI_KEY")

# Fetch news articles
def fetch_news(topic, language="en", page_size=5):
    articles = []
    if language == "en":
        try:
            params = {
                "q": topic,
                "language": language,
                "pageSize": page_size,
                "apiKey": NEWS_API_KEY,
            }
            response = requests.get("https://newsapi.org/v2/everything", params=params)
            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])
        except Exception as e:
            print(f"❌ NewsAPI request failed: {e}")
    else:
        # Use Google News RSS for Hindi/Marathi
        lang_code = language
        query = topic.replace(" ", "+")
        rss_url = f"https://news.google.com/rss/search?q={query}+language:{lang_code}&hl={lang_code}&gl=IN&ceid=IN:{lang_code}"
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:page_size]:
            articles.append({
                "title": entry.title,
                "description": entry.summary,
                "url": entry.link,
                "content": entry.summary
            })
    return articles

# Summarize article in selected language with proper bullets
def summarize_article(article, language="en"):
    content = article.get("content") or article.get("description") or article.get("title") or "No content available"
    content = content[:1500]

    # Map language code to natural language for prompt
    lang_map = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
    lang_name = lang_map.get(language, "English")

    prompt = f"""
Summarize the following article in 2-3 concise bullet points in {lang_name}.
Do NOT include any '-' or numbering, just plain sentences for each bullet.

Article:
{content}
"""

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        # Split into lines and remove empty lines
        return [line.strip() for line in response.text.split("\n") if line.strip()]
    except Exception as e:
        return [f"⚠️ Error summarizing: {e}"]

# Flask routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_news", methods=["POST"])
def get_news():
    data = request.json
    topic = data.get("topic", "").strip()
    language = data.get("language", "en")

    if not topic:
        return jsonify([])

    articles = fetch_news(topic, language=language, page_size=5)
    results = []

    for a in articles:
        summary = summarize_article(a, language)
        results.append({
            "title": a.get("title", "No title"),
            "summary": summary,
            "url": a.get("url", "#")
        })

    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

