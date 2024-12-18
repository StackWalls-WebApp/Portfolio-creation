import sys
import json
import time
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from newspaper import Article
from playwright.sync_api import sync_playwright

def normalize_url(url):
    """Ensure the URL has a scheme (http or https)."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    return url

def fetch_with_requests(url, headers=None, timeout=10):
    """Fetch page content using requests."""
    if headers is None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/87.0.4280.66 Safari/537.36"
            )
        }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        if 'text/html' in resp.headers.get('Content-Type', ''):
            return resp.text
        else:
            return None
    except requests.RequestException as e:
        print(f"[Requests] Failed to fetch {url}: {e}", file=sys.stderr)
        return None

def fetch_with_playwright(url, wait_time=5, scroll_count=3):
    """Fetch fully rendered HTML using Playwright, wait for JS, and scroll."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"[Playwright] Failed initial navigation: {e}", file=sys.stderr)
            browser.close()
            return None
        
        # Wait for dynamic content
        time.sleep(wait_time)
        
        # Scroll multiple times to load additional content
        for _ in range(scroll_count):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

        html = page.content()
        browser.close()
        return html

def extract_main_content(url, html):
    """Attempt to extract the main article text using Newspaper3k."""
    try:
        article = Article(url)
        article.set_html(html)
        article.download_state = 2  # Using provided HTML
        article.parse()
        main_text = article.text.strip()
        return main_text if main_text else None
    except Exception as e:
        print(f"[Newspaper3k] Error extracting main content: {e}", file=sys.stderr)
        return None

def parse_meta_tags(soup):
    """Extract meta tags and return a list of dicts."""
    meta_tags = []
    for meta in soup.find_all('meta'):
        attrs = {k.lower(): v for k, v in meta.attrs.items()}
        meta_tags.append(attrs)
    return meta_tags if meta_tags else None

def get_image_name(image_url, alt_text):
    """Derive an image name from alt or the filename."""
    if alt_text:
        return alt_text
    parsed = urlparse(image_url)
    filename = os.path.basename(parsed.path)
    if filename:
        filename = filename.split('?')[0].split('#')[0]
        return filename
    return None

def extract_info(url, html):
    """Extract structured information from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    result = {}

    # Title
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        if title:
            result["title"] = title

    # Meta tags
    meta_tags = parse_meta_tags(soup)
    if meta_tags:
        result["meta_tags"] = meta_tags

    # Links
    links = []
    for a_tag in soup.find_all('a', href=True):
        link_url = urljoin(url, a_tag['href'])
        text = a_tag.get_text(strip=True)
        link_info = {}
        if link_url:
            link_info["url"] = link_url
        if text:
            link_info["text"] = text
        if link_info:
            links.append(link_info)
    if links:
        result["links"] = links

    # Images
    images = []
    for img_tag in soup.find_all('img', src=True):
        img_url = urljoin(url, img_tag['src'])
        alt_text = img_tag.get('alt', '').strip()
        image_name = get_image_name(img_url, alt_text)
        img_info = {}
        if img_url:
            img_info["url"] = img_url
        if alt_text:
            img_info["alt"] = alt_text
        if image_name:
            img_info["image_name"] = image_name
        if img_info:
            images.append(img_info)
    if images:
        result["images"] = images

    # Iframes
    iframes = []
    for iframe_tag in soup.find_all('iframe', src=True):
        iframe_url = urljoin(url, iframe_tag['src'])
        if iframe_url:
            iframes.append(iframe_url)
    if iframes:
        result["iframes"] = iframes

    # Remove scripts and styles for text extraction
    for script in soup(["script", "style", "noscript"]):
        script.decompose()

    # All visible text
    text_content = ' '.join(soup.get_text(separator=' ').split())
    if text_content.strip():
        result["all_text"] = text_content

    # Headings
    headings = {}
    for h in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        h_tags = [tag.get_text(strip=True) for tag in soup.find_all(h) if tag.get_text(strip=True)]
        if h_tags:
            headings[h] = h_tags
    if headings:
        result["headings"] = headings

    # Forms and inputs
    forms = []
    for form_tag in soup.find_all('form'):
        form_info = {}
        action = form_tag.get('action', '').strip()
        method = form_tag.get('method', 'get').lower().strip()
        if action:
            form_info["action"] = action
        if method:
            form_info["method"] = method

        inputs_list = []
        for input_tag in form_tag.find_all(['input', 'select', 'textarea']):
            input_type = input_tag.get('type', 'text')
            input_name = input_tag.get('name', '')
            input_value = input_tag.get('value', '')
            input_item = {}
            if input_type:
                input_item["type"] = input_type
            if input_name:
                input_item["name"] = input_name
            if input_value:
                input_item["value"] = input_value

            if input_tag.name == 'select':
                options = [option.get('value', '') for option in input_tag.find_all('option') if option.get('value')]
                if options:
                    input_item["options"] = options

            if input_item:
                inputs_list.append(input_item)
        
        if inputs_list:
            form_info["inputs"] = inputs_list

        if form_info:
            forms.append(form_info)
    if forms:
        result["forms"] = forms

    # Scripts
    scripts = []
    for script_tag in soup.find_all('script'):
        script_content = script_tag.get_text(strip=True)
        script_src = script_tag.get('src', '')
        script_info = {}
        if script_src:
            full_src = urljoin(url, script_src)
            script_info["src"] = full_src
        if script_content:
            script_info["content"] = script_content
        if script_info:
            scripts.append(script_info)
    if scripts:
        result["scripts"] = scripts

    # Styles
    styles = []
    for style_tag in soup.find_all('style'):
        style_content = style_tag.get_text(strip=True)
        if style_content:
            styles.append(style_content)
    if styles:
        result["styles"] = styles

    # Structured Data (JSON-LD)
    structured_data = []
    for sd_tag in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(sd_tag.string)
            structured_data.append(data)
        except Exception:
            pass
    if structured_data:
        result["structured_data"] = structured_data

    return result

def main(url):
    url = normalize_url(url)

    # Step 1: Try requests
    html = fetch_with_requests(url)

    # Step 2: If not adequate, try Playwright
    if not html or len(html) < 2000:
        print("[Info] Page content might be short or dynamic, trying Playwright...", file=sys.stderr)
        html = fetch_with_playwright(url)
    
    if not html:
        print("[Error] Could not fetch the page content.", file=sys.stderr)
        return {}

    extracted_info = extract_info(url, html)

    # Extract main article content (if available)
    main_article_content = extract_main_content(url, html)
    if main_article_content:
        extracted_info["main_article_content"] = main_article_content

    return extracted_info

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrapper.py <URL>")
        sys.exit(1)

    url_to_scrape = sys.argv[1]
    result = main(url_to_scrape)

    # Print results as JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))
