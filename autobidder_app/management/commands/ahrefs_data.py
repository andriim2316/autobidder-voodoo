import asyncio
import aiohttp
from decouple import config

from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand

from autobidder_app.models import Domain, AhrefsData
from autobidder_app.utils.logger import setup_logger

# loggins
logger = setup_logger("ahrefs_data", log_directory="logs/ahrefs", days=7)


class AhrefsFetcher:
    def __init__(self):
        self.api_token = config("AHREFS_API")


    async def fetch_data(self, session, domain):
        async with asyncio.Semaphore(100):
            try:
                logger.info(f"Getting data for domain: {domain}")

                domain_rating_url = f"https://apiv2.ahrefs.com/?token={self.api_token}&target={domain}&output=json&from=domain_rating&mode=domain"
                async with session.get(domain_rating_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to get domain rating (status: {response.status})")
                    domain_rating_json = await response.json()
                    domain_data = domain_rating_json.get("domain", {})
                    domain_rating = int(float(domain_data.get("domain_rating", 0.0)))
                    ahrefs_top = int(domain_data.get("ahrefs_top", 0))

                metrics_url = f"https://apiv2.ahrefs.com/?token={self.api_token}&target={domain}&limit=1000&output=json&from=metrics_extended&mode=subdomains"
                async with session.get(metrics_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to get metrics (status: {response.status})")
                    metrics_json = await response.json()
                    metrics = metrics_json.get("metrics", {})

                return {
                    "domain_rating": domain_rating,
                    "ahrefs_top": ahrefs_top,
                    "backlinks": metrics.get("backlinks", 0),
                    "ref_pages": metrics.get("refpages", 0),
                    "pages": metrics.get("pages", 0),
                    "valid_pages": metrics.get("valid_pages", 0),
                    "text_links": metrics.get("text", 0),
                    "image_links": metrics.get("image", 0),
                    "nofollow_links": metrics.get("nofollow", 0),
                    "ugc_links": metrics.get("ugc", 0),
                    "sponsored_links": metrics.get("sponsored", 0),
                    "dofollow_links": metrics.get("dofollow", 0),
                    "redirect_links": metrics.get("redirect", 0),
                    "canonical_links": metrics.get("canonical", 0),
                    "gov_links": metrics.get("gov", 0),
                    "edu_links": metrics.get("edu", 0),
                    "rss_links": metrics.get("rss", 0),
                    "alternate_links": metrics.get("alternate", 0),
                    "html_pages": metrics.get("html_pages", 0),
                    "internal_links": metrics.get("links_internal", 0),
                    "external_links": metrics.get("links_external", 0),
                    "ref_domains": metrics.get("refdomains", 0),
                    "ref_class_c": metrics.get("refclass_c", 0),
                    "ref_ips": metrics.get("refips", 0),
                    "linked_root_domains": metrics.get("linked_root_domains", 0),
                }
            except Exception as e:
                logger.error(f"Error fetching data for domain {domain}: {e}")
                return None

    async def fetch_all(self, domains):
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_data(session, domain) for domain in domains]
            return await asyncio.gather(*tasks)


class AhrefsDataUpdater:
    def __init__(self):
        self.fetcher = AhrefsFetcher()

    async def update_ahrefs_data(self):
        domains_to_update = await sync_to_async(
            lambda: list(Domain.objects.filter(ahrefs_data__isnull=True).values_list("name", flat=True))
        )()
        logger.info(f"Found {len(domains_to_update)} domains to process: {domains_to_update}")

        results = await self.fetcher.fetch_all(domains_to_update)

        ahrefs_data_objects = []

        for domain_name, data in zip(domains_to_update, results):
            if data:
                domain = await sync_to_async(Domain.objects.get)(name=domain_name)
                ahrefs_data = AhrefsData(domain=domain, **data)
                ahrefs_data_objects.append(ahrefs_data)

        if ahrefs_data_objects:
            await sync_to_async(AhrefsData.objects.bulk_create)(ahrefs_data_objects)
            logger.info(f"Successfully added {len(ahrefs_data_objects)} entries to the database.")

    @staticmethod #not used
    def update_or_create_ahrefs_data(domain_name, data):
        """Update or create Ahrefs data"""
        domain = Domain.objects.get(name=domain_name)
        AhrefsData.objects.update_or_create(domain=domain, defaults=data)
        logger.info(f"Added to db: {domain_name}")


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        updater = AhrefsDataUpdater()
        asyncio.run(updater.update_ahrefs_data())
        logger.info("Ahrefs data update completed successfully!")