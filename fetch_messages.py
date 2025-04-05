from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urlparse, urlunparse

# Global cache for meeting minutes content (keyed by normalized URL)
meeting_minutes_cache = {}

# Global set to track which meeting minutes URLs have been appended already
appended_minutes = set()

# Helper function to fetch HTML content from a URL.
def get_html(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to fetch {url}: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# Function to normalize a URL by removing its fragment.
def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))

# Recursive function to scrape meeting minutes from a URL.
# It returns the minutes markdown (including any nested minutes) and marks the URL as appended.
def scrape_minutes_recursive(url, visited=None):
    norm_url = normalize_url(url)
    if visited is None:
        visited = set()
    if norm_url in visited:
        return ""
    visited.add(norm_url)
    
    # If already appended globally, skip further appending.
    if norm_url in appended_minutes:
        return ""
    
    # Fetch and convert the minutes page if not already cached.
    if norm_url in meeting_minutes_cache:
        content = meeting_minutes_cache[norm_url]
    else:
        html = get_html(norm_url)
        if not html:
            content = "Failed to retrieve meeting minutes."
        else:
            content = md(html, heading_style="ATX")
        meeting_minutes_cache[norm_url] = content

    # Mark this URL as appended globally.
    appended_minutes.add(norm_url)
    
    # Now, parse the HTML (refetch if needed) to find additional nested minutes links.
    html = get_html(norm_url)
    nested_content = ""
    if html:
        soup = BeautifulSoup(html, "html.parser")
        # Look for links that contain "minutes.html"
        for a in soup.find_all("a", href=True):
            link = a['href']
            # Skip mailto links.
            if link.startswith("mailto:"):
                continue
            if "minutes.html" not in link:
                continue
            # Convert relative URLs to absolute (using norm_url as base).
            if not link.startswith("http"):
                base_dir = norm_url.rsplit('/', 1)[0] + '/'
                link = base_dir + link
            nested_norm = normalize_url(link)
            if nested_norm in visited or nested_norm in appended_minutes:
                continue
            # Recursively scrape nested meeting minutes.
            rec_md = scrape_minutes_recursive(link, visited)
            if rec_md.strip():
                nested_content += f"\n---\n### Nested Meeting Minutes from: {nested_norm}\n\n{rec_md}\n"
    return content + nested_content

# ------------------------------
# Main scraping routine for the mailing list messages
# ------------------------------

# Base archive URL.
base_url = "https://lists.w3.org/Archives/Public/public-webmachinelearning-wg/"

# Step 1: Fetch the base archive page.
archive_html = get_html(base_url)
if archive_html is None:
    exit("Could not retrieve the archive page.")

# Step 2: Parse the archive page to extract the latest N month URLs.
soup = BeautifulSoup(archive_html, "html.parser")
N = 3  # Change as needed.
month_links = []
for td in soup.find_all("td", class_="cell_period"):
    a = td.find("a")
    if a and a.get("href"):
        month_links.append(base_url + a.get("href"))
latest_month_links = month_links[:N]

# List to store final markdown for each message.
message_markdowns = []

# Process each month.
for month_url in latest_month_links:
    print(f"Processing month URL: {month_url}")
    month_html = get_html(month_url)
    if not month_html:
        continue
    month_soup = BeautifulSoup(month_html, "html.parser")
    # Extract links to individual messages (skip navigation links).
    message_links = []
    for a in month_soup.find_all("a"):
        href = a.get("href")
        if href and href.endswith(".html") and all(x not in href for x in ["thread", "author", "subject"]):
            if href not in message_links:
                message_links.append(href)
    # Build full message URLs.
    message_full_urls = [month_url + link for link in message_links]
    
    # Process each message.
    for msg_url in message_full_urls:
        print(f"  Processing message URL: {msg_url}")
        msg_html = get_html(msg_url)
        if not msg_html:
            continue
        # Convert the message HTML to markdown.
        message_markdown = md(msg_html, heading_style="ATX")
        combined_markdown = f"### Message URL: {msg_url}\n\n{message_markdown}\n"
        
        # Parse the message to extract meeting minutes links.
        msg_soup = BeautifulSoup(msg_html, "html.parser")
        minutes_links = set()
        for a in msg_soup.find_all("a", href=True):
            href = a['href']
            # Skip mailto links.
            if href.startswith("mailto:"):
                continue
            # Convert relative URLs to absolute.
            if not href.startswith("http"):
                href = month_url + href
            # Only consider links that contain "minutes.html".
            if "minutes.html" not in href:
                continue
            norm_href = normalize_url(href)
            minutes_links.add(norm_href)
        
        # For each meeting minutes link found in the message, 
        # append its content only if it hasn’t been appended already.
        for minutes_url in minutes_links:
            if minutes_url in appended_minutes:
                print(f"    Skipping already appended minutes from: {minutes_url}")
                continue
            print(f"    Processing meeting minutes from: {minutes_url}")
            minutes_md = scrape_minutes_recursive(minutes_url)
            if minutes_md.strip():
                combined_markdown += f"\n---\n### Meeting Minutes from: {minutes_url}\n\n{minutes_md}\n"
        
        message_markdowns.append(combined_markdown)

# Prepare markdown content with LLM prompt
prefix = """
Analyze text below to answer the following questions:
1. What are the most important topics discussed?
"""

all_content = prefix +"\n\n" + "\n\n---\n\n".join(message_markdowns)

# Save to a file with timestamp in the filename
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
filename = f"webml_messages_{timestamp}.md"

with open(filename, "w", encoding="utf-8") as f:
    f.write(all_content)

print(f"\nSaved {len(message_markdowns)} messages to {filename}")