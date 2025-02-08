import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import localtime, make_aware, now
from autobidder_app.models import Domain


from autobidder_app.utils.logger import setup_logger
from autobidder_app.utils.voodoo_log_in import Authenticator


#logging
logger = setup_logger("voodoo_parser", log_directory="logs/voodoo", days=7)

BASE_URL = "https://voodoo.domains/uk/listings/all"


def process_pages(session: requests.Session, day_param: int) -> None:
    """Fetch all pages from Voodoo listings and process their content."""
    response = session.get(BASE_URL, params={"day": day_param})

    if not response.ok:
        logger.warning("Failed to fetch the first page")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    total_pages = extract_total_pages(soup)
    logger.info(f"Total pages found: {total_pages}")
    get_domains_from_page(soup) #fist page parse with no extra request
    for page in range(1, total_pages + 1):
        logger.info(f"Processing page {page}")
        response = session.get(BASE_URL, params={"day": day_param, "page": page})
        if not response.ok:
            logger.warning(f"Failed to fetch page {page}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        get_domains_from_page(soup)


def extract_total_pages(soup: BeautifulSoup) -> int:
    """Get pages number"""
    pagination = soup.find("ul", class_="pagination")
    if pagination:
        page_numbers = [int(link.text) for link in pagination.find_all("a") if link.text.isdigit()]
        return max(page_numbers, default=1)
    return 1


def get_domains_from_page(soup: BeautifulSoup) -> None:
    """Get domain names from the page"""
    rows = soup.find_all("tr", style="cursor: pointer;")
    for row in rows:
        process_domain_row(row)


def process_domain_row(row):
    """Save domain details."""
    domain_id = row.get("data-id")
    domain_name = row.find("div", class_="fqdn").text.strip() if row.find("div", class_="fqdn") else None
    expiration_date = parse_date(row.find_all("td", class_="text-center")[1].text.strip()) if row.find_all("td", class_="text-center") else None

    if domain_id and domain_name and expiration_date:
        Domain.objects.get_or_create(
            domain_id=domain_id,
            defaults={"name": domain_name, "expiration_date": expiration_date}
        )
        logger.info(f"Processed domain: {domain_name}")
    else:
        logger.warning(f"Skipping incomplete domain data: ID={domain_id}, Name={domain_name}")


def parse_date(raw_date: str):
    """Make date format for extracted date"""
    if raw_date.startswith("≈"):
        raw_date = raw_date.replace("≈", "").strip()
    try:
        return make_aware(datetime.strptime(raw_date, "%d.%m.%Y %H:%M:%S"))
    except ValueError:
        logger.warning(f"Skipping invalid date format: {raw_date}")
        return None

def run_parser():
    try:
        auth = Authenticator()

        if not auth.is_logged_in():
            logger.error("Authorization failed.")
            return {"status": "error", "message": "Authorization failed."}

        session = auth.session
        #set the last day avaiable (+3 days from today)
        day_param = int(
            (localtime(now()) + timedelta(days=3))
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )

        process_pages(session, day_param)

        return {"status": "success", "message": "Parsing completed successfully."}
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return {"status": "error", "message": str(e)}


class Command(BaseCommand):
    """Parse domains for backorder."""

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Voodoo parser...")
        result = run_parser()
        logger.info(result["message"])