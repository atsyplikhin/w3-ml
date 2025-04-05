import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from datetime import datetime

# Helper function to fetch HTML content from a URL.
def get_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch {url}: Status code {response.status_code}")
        return None

# Base archive URL.
base_url = "https://lists.w3.org/Archives/Public/public-webmachinelearning-wg/"

# Step 1: Open the base URL and get its content.
archive_html = get_html(base_url)
if archive_html is None:
    exit("Could not retrieve the archive page.")

# Step 2: Parse the archive page to find the latest N months' URLs.
soup = BeautifulSoup(archive_html, "html.parser")
# Here you can change N to however many months you want to process.
N = 3
month_links = []

# The sample HTML shows month links inside <td class="cell_period"> tags.
for td in soup.find_all("td", class_="cell_period"):
    a = td.find("a")
    if a and a.get("href"):
        # Construct full URL from the base URL and the relative href.
        month_links.append(base_url + a.get("href"))

# Assuming the archive page is sorted with the latest months first:
latest_month_links = month_links[:N]

# Prepare an array to store the markdown conversions of each message.
message_markdowns = []

# Step 3 & 4: Process each month URL and extract message URLs.
for month_url in latest_month_links:
    print(f"Processing month URL: {month_url}")
    month_html = get_html(month_url)
    if month_html is None:
        continue

    month_soup = BeautifulSoup(month_html, "html.parser")
    # Find all links that point to individual messages (ending with .html)
    message_links = []
    for a in month_soup.find_all("a"):
        href = a.get("href")
        # Filter out navigation links like 'thread.html', 'author.html', etc.
        if href and href.endswith(".html") and all(x not in href for x in ["thread", "author", "subject"]):
            # Avoid duplicates if present.
            if href not in message_links:
                message_links.append(href)
    
    # Create full URLs for messages.
    message_full_urls = [month_url + link for link in message_links]

    # Step 5: Open each message URL, convert to markdown, and store the result.
    for msg_url in message_full_urls:
        print(f"  Processing message URL: {msg_url}")
        msg_html = get_html(msg_url)
        if msg_html is None:
            continue
        # Convert the HTML message to markdown.
        markdown_message = md(msg_html, heading_style="ATX")
        # Optionally, prepend a header to mark the message.
        marked_message = f"### Message URL: {msg_url}\n\n{markdown_message}"
        message_markdowns.append(marked_message)

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