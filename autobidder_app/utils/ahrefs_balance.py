import requests
from decouple import config
from django.core.management import BaseCommand


def check_api_limit():
    """Get api limits balance"""
    api_token = config("AHREFS_API")
    url = f"https://apiv2.ahrefs.com/?token={api_token}&from=subscription_info&output=json"

    response = requests.get(url)  # Blocking request
    if response.status_code != 200:
        return {"error": f"Failed to fetch API limit (status: {response.status_code})"}

    return response.json()
