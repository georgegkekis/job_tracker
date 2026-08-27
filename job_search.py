from playwright.sync_api import sync_playwright
from datetime import datetime
import csv
import re
import time
from urllib.parse import quote


SEARCH_TERMS = [
    "Software Engineer Python",
    "Automated Test Engineer",
    "SDET",
    "Software Developer in Test",
]

CSV_FILE = "totaljobs_results.csv"


def extract_number(text):
    """
    Extract an integer from strings such as:
        '3,478 jobs'
        '721'
        'There are 165 jobs'
    """
    match = re.search(r"[\d,]+", text)
    if not match:
        return None

    return int(match.group().replace(",", ""))


def get_result_count(page):
    """
    Try to find the main Totaljobs result count.

    Totaljobs currently displays headings such as:
        '3,088 jobs in Halesowen + 10 miles'
        '1,769 Contract Remote Worker jobs in UK + 10 miles'
    """

    page.wait_for_timeout(2000)

    # Look through headings first
    for selector in ["h1", "h2"]:
        elements = page.locator(selector)

        for i in range(elements.count()):
            text = elements.nth(i).inner_text().strip()

            if "job" in text.lower():
                number = extract_number(text)

                if number is not None:
                    return number

    # Fallback: search page text
    body = page.locator("body").inner_text()

    patterns = [
        r"([\d,]+)\s+jobs",
        r"There are\s+([\d,]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)

        if match:
            return int(match.group(1).replace(",", ""))

    return None


def search(page, term):
    """
    Go directly to a Totaljobs search-results URL.
    """

    # Totaljobs uses hyphenated search terms in the URL
    slug = term.lower().replace(" ", "-")

    url = f"https://www.totaljobs.com/jobs/{quote(slug)}"

    print(f"Opening: {url}")

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    # Cookie banner
    try:
        page.get_by_role(
            "button",
            name=re.compile("accept", re.I)
        ).click(timeout=3000)
    except:
        pass

    page.wait_for_timeout(3000)

    return get_result_count(page)


def get_contract_count(page):
    """
    Select Contract employment type.
    """
    try:
        page.get_by_text(
            "Contract",
            exact=True
        ).first.click()

        page.wait_for_timeout(2000)

        return get_result_count(page)

    except Exception as e:
        print("Could not select Contract:", e)
        return None


def get_80k_count(page):
    """
    Select 'at least £80,000' salary filter.
    """

    try:
        page.get_by_text(
            re.compile(r"at least £80,000", re.I)
        ).first.click()

        page.wait_for_timeout(2000)

        return get_result_count(page)

    except Exception as e:
        print("Could not select £80k filter:", e)
        return None


def append_results(rows):
    """
    Append results to CSV. Create header if needed.
    """

    try:
        with open(CSV_FILE, "r"):
            file_exists = True
    except FileNotFoundError:
        file_exists = False

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "search_term",
                "all_jobs",
                "over_80k",
                "contracts",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(rows)


def main():

    results = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        for term in SEARCH_TERMS:

            print()
            print(f"Searching: {term}")

            all_jobs = search(page, term)
            print(f"All jobs: {all_jobs}")

            search(page, term)

            over_80k = get_80k_count(page)

            print(f"£80k+: {over_80k}")

            search(page, term)

            contracts = get_contract_count(page)

            print(f"Contracts: {contracts}")

            results.append(
                {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "search_term": term,
                    "all_jobs": all_jobs,
                    "over_80k": over_80k,
                    "contracts": contracts,
                }
            )

            time.sleep(2)

        browser.close()

    append_results(results)

    print()
    print(f"Saved to {CSV_FILE}")


if __name__ == "__main__":
    main()