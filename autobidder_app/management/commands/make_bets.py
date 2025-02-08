import pytz
import requests
from bs4 import BeautifulSoup
import re
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import close_old_connections

from autobidder_app.models import Bet

from datetime import timedelta
from autobidder_app.utils.notification import send_bet_exceeded_message
from autobidder_app.views import delete_bet
import asyncio
import random
import time
from autobidder_app.utils.logger import setup_logger
from autobidder_app.utils.voodoo_log_in import Authenticator


# Constants
BID_URL_TEMPLATE = "https://voodoo.domains/uk/voodoo1domainlisting/bid?backorder_domain_id="
LOGIN_URL = "https://voodoo.domains/uk/accounts/ajax/auth"
BIDDING_START_HOUR, BIDDING_END_HOUR = 9, 22
bucharest_tz = pytz.timezone('Europe/Bucharest')
TIME_BEFORE_EXPIRATION = timedelta(hours=1)
minimal_bet = 900


# loggins
logger = setup_logger("bet_processor", log_directory="logs/make_bets", days=7)



class BetProcessor(Authenticator):
    def __init__(self, domain_id=None):
        super().__init__()  # Initialize AuthenticatorMixin
        if domain_id:
            self.bets = Bet.objects.select_related('domain').filter(domain__domain_id=domain_id)
            logger.info(f"BetProcessor initialized for a single domain ID: {domain_id}.")
        else:
            target_time = now().astimezone(bucharest_tz) + TIME_BEFORE_EXPIRATION
            self.bets = Bet.objects.select_related('domain').filter(domain__expiration_date__lte=target_time)
            logger.info(f"BetProcessor initialized. Loaded {len(self.bets)} bets.")



    def fetch_next_bid_amount(self, domain_id, domain_name):
        """Fetch the next bid amount for a domain."""
        logger.info(f"Fetching bid amount for domain ID: {domain_id} - {domain_name}")

        if not self.is_logged_in() and not self.login():
            logger.error(f"Login failed for domain ID {domain_id}. Exiting process.")
            return None

        response = self.session.get(f"{BID_URL_TEMPLATE}{domain_id}", timeout=10)
        if response.status_code != 200:
            logger.warning(
                f"Failed to fetch data for domain ID {domain_id} ({domain_name}). Status: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Check if auction has ended
        alert_message = soup.find('div', class_='alert alert-danger alert-dismissable')
        if alert_message and "Час прийому заявок минув" in alert_message.get_text(strip=True):
            logger.info(f"Auction ended for domain ID {domain_id} ({domain_name}). Deleting bet from database.")
            delete_bet(None, bet_id=domain_id)  # Call the view function directly
            return None

        # Extract input value (current bid)
        input_value = self.get_int_value(soup.find('input', {'id': 'modal_backorder_sum'}))
        if input_value is None:
            logger.info(f"No input bid found for domain ID {domain_id} ({domain_name}). Assuming no current bid.")

        # Extract next possible bid
        bid_info = soup.find('p', {'id': 'modal_backorder_original_info'})
        next_bid = self.extract_bid_value(bid_info)

        if next_bid is not None and (input_value is None or input_value < next_bid):
            logger.info(f"We should rise a bet to {next_bid} for domain ID {domain_id} ({domain_name})")
            return next_bid

        logger.info(f"Current bid {input_value} is sufficient for domain ID {domain_id} ({domain_name}). No action needed.")
        return None

    def get_int_value(self, element):
        """Extract integer value from HTML element."""
        if element and element.has_attr('value'):
            try:
                return int(element['value'].replace('\xa0', '').replace(' ', ''))
            except ValueError:
                logger.error("Input field is empty.")
        return None

    def extract_bid_value(self, element):
        """Extract minimum bid value from HTML element text."""
        if element and element.text:
            match = re.search(r'від\s(\d+)\sдо\s(\d+)', element.text)
            if match:
                try:
                    return int(match.group(1).replace('\xa0', '').replace(' ', ''))
                except ValueError:
                    logger.error("Failed to convert extracted bid value.")
        return None

    def is_within_bidding_hours(self):
        """Check if the current time is within allowed bidding hours."""
        current_hour = now().astimezone(bucharest_tz).hour
        return BIDDING_START_HOUR <= current_hour < BIDDING_END_HOUR

    def make_bid(self, domain_id, next_bid):
        """Place a bid."""
        bid_url = f"{BID_URL_TEMPLATE}{domain_id}"
        payload = {
            "backorder_sum": next_bid,
            "form_action[save]": "Зробити пропозицію"
        }

        try:
            response = self.session.post(bid_url, data=payload, timeout=10)
            response.raise_for_status()

            # Debug response text
            logger.debug(f"Response Text Snippet: {response.text[:500]}")

            # Check for success message in response
            if "вашу заявку успішно збережено" in response.text.lower():
                logger.info(f"Successfully placed bid of {next_bid} for domain ID {domain_id}.")
                return True
            else:
                logger.error(f"Failed to place bid for domain ID {domain_id}. Response did not indicate success.")
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Error placing bid for domain ID {domain_id}: {e}")
        return False

    def process_bets(self, domain_id=None):
        """Process all bets or a specific domain if provided."""
        logger.info("Starting bet processing.")

        if not self.is_logged_in() and not self.login():
            logger.error("Skipping all bets - Unable to authenticate.")
            return

        # If domain_id is specified, filter bets for that domain only
        if domain_id:
            self.bets = self.bets.filter(domain__domain_id=domain_id)
            logger.info(f"Processing a single bet for domain ID {domain_id}")

        for bet in self.bets:
            next_bid = self.fetch_next_bid_amount(bet.domain.domain_id, bet.domain.name)
            if next_bid is None:
                continue

            if bet.max_bet >= next_bid:
                if self.make_bid(bet.domain.domain_id, next_bid):
                    logger.info(f"Bid of {next_bid} placed for {bet.domain.name}.")
                else:
                    logger.error(f"Failed to place bid for {bet.domain.name}.")
            else:
                logger.info(f"Max bet {bet.max_bet} is too low for {bet.domain.name}. Sending notification.")
                asyncio.run(send_bet_exceeded_message(bet.domain.name, next_bid, bet.max_bet, bet.domain.domain_id))

        logger.info("Bet processing completed.")

    def process_night_bets(self):
        """Process bets that expire at night time. Makes a bid only if there were no bids before."""
        logger.info("Checking night bets.")

        if not self.is_logged_in():
            if not self.login():
                logger.error("Skipping all bets - Unable to authenticate.")
                return

        for bet in self.bets:
            next_bid = self.fetch_next_bid_amount(bet.domain.domain_id, bet.domain.name)

            #prevent error
            if next_bid is None:
                continue

            if next_bid > minimal_bet:
                logger.info(f"Skipping {bet.domain.name} - A bid has already been placed, we do not rise bets at night time (Next bid: {next_bid}).")
                continue

            if bet.max_bet >= next_bid:
                if self.make_bid(bet.domain.domain_id, next_bid):
                    logger.info(f"Night bid of {next_bid} placed for {bet.domain.name}.")
                else:
                    logger.error(f"Failed to place night bid for {bet.domain.name}.")
        logger.info("Night bet processing completed.")


def run_bet_processing(domain_id=None):
    """Process betting for all domains or a single domain if specified."""
    if domain_id is None:
        delay = random.randint(60, 600)
        logger.info(f"Delaying bet processing by {delay} seconds...")
        time.sleep(delay)

    processor = BetProcessor(domain_id=domain_id)

    if domain_id:
        logger.info(f"Processing bid for single domain ID: {domain_id}")
        processor.process_bets(domain_id=domain_id)
    elif processor.is_within_bidding_hours():
        processor.process_bets()
    else:
        processor.process_night_bets()




class Command(BaseCommand):
    help = 'Process bets processing.'

    def handle(self, *args, **kwargs):
        try:
            run_bet_processing()
        except Exception as e:
            logger.critical(f"Critical error in bet processor: {e}", exc_info=True)
        finally:
            #close db connections in case of errors
            close_old_connections()
            logger.info("Database connections closed after command execution.")