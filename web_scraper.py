import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import time
import logging

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_INSTALLED = True
except ImportError:
    PLAYWRIGHT_INSTALLED = False


class WebScraper:
    def __init__(self,
                 user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                 rate_limit=1,
                 timeout=10,
                 max_retries=3,
                 enable_js=False,
                 summarize_content=True):
        self.user_agent = user_agent
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.summarize_content = summarize_content
        self.enable_js = enable_js and PLAYWRIGHT_INSTALLED
        self.last_request_time = {}

        # Set up logging
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger("WebScraper")

        if enable_js and not PLAYWRIGHT_INSTALLED:
            self.logger.warning(
                "Playwright is not installed. JavaScript rendering disabled."
            )
            self.enable_js = False

    def can_fetch(self, url):
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            return rp.can_fetch(self.user_agent, url)
        except Exception as e:
            self.logger.warning(f"Error reading robots.txt for {url}: {e}")
            return True

    def respect_rate_limit(self, url):
        domain = urlparse(url).netloc
        current_time = time.time()
        if domain in self.last_request_time:
            elapsed_time = current_time - self.last_request_time[domain]
            if elapsed_time < self.rate_limit:
                time.sleep(self.rate_limit - elapsed_time)
        self.last_request_time[domain] = time.time()

    def fetch_page(self, url):
        for attempt in range(self.max_retries):
            try:
                self.respect_rate_limit(url)
                headers = {"User-Agent": self.user_agent}
                response = requests.get(
                    url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries}: Error fetching {url}: {e}")
                time.sleep(2 ** attempt)
        self.logger.error(f"Failed to fetch {url} after {
                          self.max_retries} attempts")
        return None

    def fetch_js_page(self, url):
        if not self.enable_js:
            self.logger.warning("JavaScript rendering is disabled.")
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(user_agent=self.user_agent)
                page = context.new_page()
                page.goto(url, timeout=self.timeout * 1000)
                content = page.content()
                return content
            except Exception as e:
                self.logger.error(f"Error fetching {url} with JavaScript: {e}")
                return None
            finally:
                browser.close()

    def extract_metadata(self, soup):
        metadata = {
            "title": soup.title.string if soup.title else "No Title",
            "description": soup.find("meta", attrs={"name": "description"})["content"]
            if soup.find("meta", attrs={"name": "description"})
            else "No Description",
            "keywords": soup.find("meta", attrs={"name": "keywords"})["content"]
            if soup.find("meta", attrs={"name": "keywords"})
            else "No Keywords",
        }
        return metadata

    def extract_content(self, html, url):
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        metadata = self.extract_metadata(soup)
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("section")
            or soup.find("div")
            or soup
        )
        paragraphs = main_content.find_all("p") if main_content else []
        content = " ".join(p.get_text().strip() for p in paragraphs)[:2400]
        links = [urljoin(url, a["href"])
                 for a in soup.find_all("a", href=True)][:10]

        if self.summarize_content and len(content.split()) > 100:
            content = self.summarize_text(content)

        return {
            **metadata,
            "content": content or "No main content found.",
            "links": list(set(links)),
        }

    def summarize_text(self, text):
        sentences = text.split(". ")
        return ". ".join(sentences[:3]) + "..." if len(sentences) > 3 else text

    def scrape_page(self, url):
        if not self.can_fetch(url):
            return {"content": "Access denied by robots.txt", "links": [], "title": "No Title"}

        html = self.fetch_js_page(
            url) if self.enable_js else self.fetch_page(url)
        if not html:
            return {"content": f"Failed to fetch {url}", "links": [], "title": "No Title"}

        return self.extract_content(html, url)

    def scrape_multiple_pages(self, urls):
        results = {}
        for url in urls:
            self.logger.info(f"Scraping {url}...")
            results[url] = self.scrape_page(url)
        return results

    def test_scraper(self, test_urls):
        results = self.scrape_multiple_pages(test_urls)
        for url, result in results.items():
            self.logger.info(f"URL: {url}")
            self.logger.info(f"Title: {result.get('title', 'No Title')}")
            self.logger.info(f"Description: {result.get(
                'description', 'No Description')}")
            self.logger.info(f"Content: {result['content'][:500]}")
            self.logger.info(f"Links: {result['links']}")
