import argparse
from search_and_scrape import SearchAndScrape


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Search and scrape tool",
        add_help=False  # Disable default help to add custom behavior
    )
    parser.add_argument(
        "--results", "-r", type=int, default=5,
        help="Number of results to fetch and scrape (default: 5)"
    )
    parser.add_argument(
        "--time", "-t", type=str, choices=["d", "w", "m", "y", "none"], default="none",
        help="Time range for search results: 'd' (day), 'w' (week), 'm' (month), 'y' (year), or 'none' (default: none)"
    )
    parser.add_argument(
        "--include", "-i", type=str, nargs="*", default=[],
        help="Keywords to include in search results (space-separated)"
    )
    parser.add_argument(
        "--exclude", "-e", type=str, nargs="*", default=[],
        help="Keywords to exclude from search results (space-separated)"
    )
    parser.add_argument(
        "--export", "-x", type=str, choices=["json", "csv"], default=None,
        help="Export results to a file format (json or csv)"
    )
    parser.add_argument(
        "--info", "-I", action="store_true",
        help="Display detailed information about the available arguments"
    )
    parser.add_argument(
        "--help", action="store_true",
        help="Show help message for basic usage"
    )

    # Parse arguments
    args = parser.parse_args()

    # Handle --info argument
    if args.info:
        print("\n[INFO] Detailed Information about Arguments:")
        print("-------------------------------------------------")
        print("--results, -r: Number of results to fetch and scrape.")
        print("    Example: --results 10 or -r 10")
        print("--time, -t: Time range for search results.")
        print("    Options: 'd' (day), 'w' (week), 'm' (month), 'y' (year), 'none'")
        print("    Example: --time w or -t w")
        print("--include, -i: Keywords to include in search results.")
        print("    Example: --include AI future or -i AI future")
        print("--exclude, -e: Keywords to exclude from search results.")
        print("    Example: --exclude chatbot or -e chatbot")
        print("--export, -x: Export results to a specified file format (json or csv).")
        print("    Example: --export json or -x csv")
        print("--info, -I: Display this detailed information.")
        print("--help: Show help message for basic usage.")
        return

    # Handle --help argument
    if args.help:
        parser.print_help()
        return

    # Prompt for search query
    query = input("Enter your search query: ").strip()
    if not query:
        print("[red]Search query cannot be empty.[/red]")
        return

    # Initialize SearchAndScrape with user-defined max_results
    search_and_scrape = SearchAndScrape(max_results=args.results)

    # Execute search and scrape
    results = search_and_scrape.search_and_scrape(
        query=query,
        time_range=args.time,
        include_keywords=args.include,
        exclude_keywords=args.exclude
    )

    if results:
        # Display results
        search_and_scrape.display_results(results)

        # Export results if requested
        if args.export:
            search_and_scrape.export_results(
                results, output_format=args.export)
    else:
        print("[red]No results found or scraped.[/red]")


if __name__ == "__main__":
    main()
