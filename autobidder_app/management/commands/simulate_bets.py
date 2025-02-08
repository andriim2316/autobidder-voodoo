import logging
import asyncio
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from autobidder_app.models import Bet, Domain
from asgiref.sync import sync_to_async


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
TIME_BEFORE_EXPIRATION = timedelta(hours=1)

def create_simulated_bets():
    """Insert simulated bets into the database for testing."""
    simulated_bets = [
        {"domain_name": "test1.com", "expiration_date": now() + timedelta(minutes=30), "domain_id": 15508297, "max_bet": 300},
        {"domain_name": "test2.com", "expiration_date": now() + timedelta(minutes=10), "domain_id": 21246060, "max_bet": 900},
        {"domain_name": "test3.com", "expiration_date": now() + timedelta(minutes=5), "domain_id": 21246061, "max_bet": 900},
    ]

    for bet_data in simulated_bets:
        domain, created = Domain.objects.update_or_create(
            domain_id=bet_data["domain_id"],
            defaults={
                "name": bet_data["domain_name"],
                "expiration_date": bet_data["expiration_date"]  # Ensure expiration date is set
            }
        )

        Bet.objects.update_or_create(
            domain=domain,
            defaults={
                "max_bet": bet_data["max_bet"],
                "expiration_date": bet_data["expiration_date"]  # ✅ Explicitly set expiration date
            }
        )

        logging.info(f"Created simulated bet for {bet_data['domain_name']} (ID: {bet_data['domain_id']})")

async def process_simulated_bets():
    """Process bets from the database and send notifications."""
    from autobidder_app.utils.notification import send_bet_exceeded_message  # ✅ Import inside function

    logging.info("Starting simulated bet processing...")

    # Run the ORM query in a separate thread
    target_time = now() + TIME_BEFORE_EXPIRATION
    bets = await sync_to_async(list)(Bet.objects.select_related("domain").filter(domain__expiration_date__lte=target_time))

    for bet in bets:
        logging.info(f"Checking bet for {bet.domain.name}")
        expiration_time = bet.domain.expiration_date
        time_remaining = expiration_time - now()

        if time_remaining > TIME_BEFORE_EXPIRATION:
            logging.info(f"Skipping {bet.domain.name}, expiration not near.")
            continue

        next_bid = 2500  # Simulated bid value to trigger notifications
        if bet.max_bet >= next_bid:
            logging.info(f"Simulated bid within limit for {bet.domain.name}")
        else:
            logging.info(f"Sending notification for {bet.domain.name}")
            try:
                await send_bet_exceeded_message(bet.domain.name, next_bid, bet.max_bet, bet.domain.domain_id)
                logging.info(f"Notification sent for {bet.domain.name}")
            except Exception as e:
                logging.error(f"Error sending message: {e}")

    logging.info("Simulated bet processing completed.")
class Command(BaseCommand):
    help = "Simulate bets and send Telegram notifications"

    def handle(self, *args, **kwargs):
        create_simulated_bets()  # Insert test data into the database
        asyncio.run(process_simulated_bets())  # Process bets and send notifications