import argparse
from search import SearchModule
from web_scraper import WebScraper
from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from diskcache import Cache
import json
import csv


class SearchAndScrape:
    def __init__(self, max_results=5, cache_dir="cache"):
        self.search_module = SearchModule(max_results=max_results)
        self.web_scraper = WebScraper()
        self.console = Console()
        self.cache = Cache(cache_dir)

    def search_and_scrape(
        self,
        query: str,
        skip_restricted=True,
        time_range=None,
        include_keywords=None,
        exclude_keywords=None,
    ):
        """
        Perform a search and scrape content from the resulting URLs.

        Args:
            query (str): The search query.
            skip_restricted (bool): If True, skip pages restricted by robots.txt.
            time_range (str): Time range for search ('d', 'w', 'm', 'y', 'none').
            include_keywords (list): Keywords to include in search results.
            exclude_keywords (list): Keywords to exclude from search results.

        Returns:
            list: A list of dictionaries containing search results and scraped content.
        """
        if query in self.cache:
            self.console.print(
                f"[green]Loaded cached results for query: {query}[/green]"
            )
            return self.cache[query]

        self.console.print(f"[cyan]Searching for: {query}[/cyan]")
        search_results = self.search_module.search(
            query,
            time_range=time_range,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords,
        )
        if not search_results:
            self.console.print("[red]No search results found.[/red]")
            return []

        urls = [result["link"] for result in search_results]
        combined_results = []

        # Progress bar for scraping
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            console=self.console,
        ) as progress:
            scrape_task = progress.add_task(
                "Scraping URLs...", total=len(urls))
            scraped_data = {}

            for url in urls:
                try:
                    scraped_data[url] = self.web_scraper.scrape_page(url)
                except Exception as e:
                    self.console.print(
                        f"[red]Error scraping {url}: {e}[/red]")
                progress.advance(scrape_task)

        for result in search_results:
            url = result["link"]
            scraped_content = scraped_data.get(url, {})
            is_restricted = "Access denied by robots.txt" in scraped_content.get(
                "content", ""
            )
            if skip_restricted and is_restricted:
                self.console.print(
                    f"[yellow]Skipped restricted page: {url}[/yellow]"
                )
                continue

            content = scraped_content.get("content", "No content scraped.")
            word_count = (
                len(content.split()) if content != "No content scraped." else 0
            )
            links = list(set(scraped_content.get("links", [])))
            combined_results.append(
                {
                    "title": result["title"],
                    "snippet": result["snippet"],
                    "link": url,
                    "scraped_content": content,
                    "word_count": 0 if is_restricted else word_count,
                    "source": urlparse(url).netloc,
                    "scraped_links": links,
                }
            )

        self.cache[query] = combined_results
        return combined_results

    def display_results(self, results):
        """
        Display results in a rich table format.

        Args:
            results (list): The list of combined search and scrape results.
        """
        table = Table(title="Search and Scrape Results")

        table.add_column("Title", justify="left", style="cyan", no_wrap=True)
        table.add_column("Snippet", justify="left")
        table.add_column("Source", justify="left", style="magenta")
        table.add_column("Word Count", justify="right", style="green")

        for result in results:
            table.add_row(
                result["title"],
                result["snippet"],
                result["source"],
                str(result["word_count"]),
            )

        self.console.print(table)

        for i, result in enumerate(results, 1):
            self.console.print(
                f"\n[bold magenta]Result {i}: {result['title']}[/bold magenta]"
            )
            self.console.print(
                f"[cyan]Scraped Content:[/cyan] {
                    result['scraped_content'][:500]}..."
            )
            self.console.print(
                f"[cyan]Links:[/cyan] {result['scraped_links']}\n"
            )

    def export_results(self, results, output_format="json"):
        """
        Export results to JSON or CSV.

        Args:
            results (list): The list of combined search and scrape results.
            output_format (str): The format to export to ('json' or 'csv').
        """
        if output_format == "json":
            with open("search_and_scrape_results.json", "w") as f:
                json.dump(results, f, indent=4)
            self.console.print(
                "[green]Results exported to search_and_scrape_results.json[/green]")
        elif output_format == "csv":
            with open("search_and_scrape_results.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            self.console.print(
                "[green]Results exported to search_and_scrape_results.csv[/green]")
        else:
            self.console.print(
                "[red]Unsupported export format. Use 'json' or 'csv'.[/red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search and scrape web content.")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--re", type=int, default=5,
                        help="Number of results to fetch")
    parser.add_argument(
        "--time_range",
        type=str,
        default="none",
        choices=["d", "w", "m", "y", "none"],
        help="Time range for search ('d' for day, 'w' for week, etc.)",
    )
    parser.add_argument(
        "--include",
        type=str,
        help="Comma-separated keywords to include in the results",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Comma-separated keywords to exclude from the results",
    )
    parser.add_argument(
        "--export",
        type=str,
        default="json",
        choices=["json", "csv"],
        help="Export results to JSON or CSV (default: JSON)",
    )

    args = parser.parse_args()

    include_keywords = [kw.strip() for kw in args.include.split(
        ",")] if args.include else None
    exclude_keywords = [kw.strip() for kw in args.exclude.split(
        ",")] if args.exclude else None

    search_and_scrape = SearchAndScrape(max_results=args.re)
    results = search_and_scrape.search_and_scrape(
        query=args.query,
        time_range=args.time_range,
        include_keywords=include_keywords,
        exclude_keywords=exclude_keywords,
    )

    if results:
        search_and_scrape.display_results(results)
        search_and_scrape.export_results(results, output_format=args.export)
