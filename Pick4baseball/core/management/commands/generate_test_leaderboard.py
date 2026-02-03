from django.core.management.base import BaseCommand
from core.models import UserProfile, SeasonScore
import random

class Command(BaseCommand):
    help = "Generate fake leaderboard data for testing"

    def handle(self, *args, **kwargs):
        users = UserProfile.objects.all()

        for user in users:
            score, created = SeasonScore.objects.get_or_create(user=user)
            score.total_points = random.randint(10, 150)
            score.weeks_won = random.randint(0, 5)
            score.save()

        self.stdout.write(self.style.SUCCESS("Test leaderboard data generated."))