#!/usr/bin/env python3
import argparse
import sys
from scraper import MultiSourceJobScraper

def main():
    parser = argparse.ArgumentParser(description="Multi-Portal Sri Lanka Job Scraper CLI")
    parser.add_argument("--list-sources", action="store_true", help="List supported job portals")
    parser.add_argument("--list-categories", action="store_true", help="List available TopJobs categories")
    parser.add_argument("--source", "-s", type=str, default="ALL", help="Source portal: ALL, topjobs, xpressjobs, rooster, jobpal, observerjobs")
    parser.add_argument("--category", "-c", type=str, default="SDQ", help="Category code for TopJobs (e.g. SDQ, HNS, ACA)")
    parser.add_argument("--deep", action="store_true", help="Perform deep scraping for full details/images when available")
    parser.add_argument("--output", "-o", type=str, default="job_results.json", help="Output file path (.json or .csv)")

    args = parser.parse_args()
    scraper = MultiSourceJobScraper()

    if args.list_sources:
        print("\n--- Supported Job Portals ---")
        sources = scraper.get_sources()
        for key, name in sources.items():
            print(f"[{key}] {name}")
        print("\n")
        return

    if args.list_categories:
        print("\n--- Available TopJobs Categories ---")
        categories = scraper.get_topjobs_categories()
        for code, name in categories.items():
            print(f"[{code}] {name}")
        print(f"\nTotal: {len(categories)} categories\n")
        return

    source_key = args.source.upper()
    print(f"-> Starting scrape for Source: [{source_key}] | Category: [{args.category}]...")

    def cli_progress(percent, msg, cur, tot):
        print(f"[{percent:3d}%] {msg}")

    jobs = scraper.scrape(
        source_key=source_key,
        category_code=args.category,
        deep_scrape=args.deep,
        progress_callback=cli_progress
    )

    print(f"\nTotal job opportunities extracted: {len(jobs)}")

    if args.output.endswith('.csv'):
        scraper.export_to_csv(jobs, args.output)
    else:
        scraper.export_to_json(jobs, args.output)

if __name__ == "__main__":
    main()
