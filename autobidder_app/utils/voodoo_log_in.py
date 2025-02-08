import requests
from decouple import config
from autobidder_app.utils.logger import setup_logger


LOGIN_URL = "https://voodoo.domains/uk/accounts/ajax/auth"
logger = setup_logger("authenticator", log_directory="logs/auth", days=7)

class Authenticator:
    def __init__(self):
        self.session = requests.Session()
        self.is_authenticated = False

    def is_logged_in(self):
        logger.info("Checking user authentication status...")
        try:
            response = self.session.get(LOGIN_URL)
            response_json = response.json()

            if response_json.get("auth_id") == 0:
                logger.warning("User not logged in. Attempting login...")
                return self.login()
            else:
                self.is_authenticated = True
                logger.info("User is already logged in.")
                return True
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Error during login check: {e}")
            return False

    def login(self):
        if self.is_authenticated:
            logger.info("Skipping login as user is already authenticated.")
            return True

        logger.info("Attempting to log in to Voodoo...")
        payload = {
            "auth_login": config("VOODOO_USERNAME"),
            "auth_password": config("VOODOO_PASSWORD")
        }

        try:
            response = self.session.post(LOGIN_URL, data=payload)
            response.raise_for_status()

            response_json = response.json()
            if response_json.get("auth_id", 0) > 0:
                self.is_authenticated = True
                logger.info(f"Login successful with auth_id: {response_json['auth_id']}")
                return True
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Login failed: {e}")
        return False