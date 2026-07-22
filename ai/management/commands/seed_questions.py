from django.core.management.base import BaseCommand

from ai.models import OnboardingQuestion
from ai.utils import DEFAULT_QUESTIONS


class Command(BaseCommand):
    help = "Seed default onboarding questions into the database."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for q in DEFAULT_QUESTIONS:
            obj, was_created = OnboardingQuestion.objects.update_or_create(
                id=q["id"],
                defaults={
                    "question_type": q["question_type"],
                    "prompt": q["prompt"],
                    "options": q["options"],
                    "max_selections": q["max_selections"],
                    "order": q["order"],
                    "is_progressive": q["is_progressive"],
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created} question(s) created, {updated} updated."
            )
        )
