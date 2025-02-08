from django.core.management.base import BaseCommand
import asyncio
from autobidder_app.telegram_bot.telegram import main


class Command(BaseCommand):
    help = "Start the Telegram bot"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Telegram bot...")
        asyncio.run(main())