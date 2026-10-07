import random
import unicodedata
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from customers.models import Activity, Customer

FIRST_NAMES = ["Ana", "João", "Maria", "Pedro", "Inês", "Tiago", "Sofia", "Rui", "Beatriz", "Miguel", "Carla", "Diogo"]
LAST_NAMES = ["Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues", "Martins", "Sousa", "Gomes"]
COMPANIES = [
    "Atlântico Logística", "Vinhas do Oeste", "Lusotec Sistemas", "Cerâmica Ribeiro", "Mar Azul Hotéis",
    "Nortenha Engenharia", "Padaria Central", "Solaris Energia", "Ponte Seguros", "Quinta Verde Agro",
]
TITLES = [
    "Operations Manager", "CEO", "Procurement Lead", "Finance Director", "Office Manager",
    "Head of IT", "Sales Director", "Founder", "Purchasing Assistant", "COO",
]
CITIES = [
    ("Lisboa", "Lisboa", "1100"),
    ("Porto", "Porto", "4000"),
    ("Braga", "Braga", "4700"),
    ("Coimbra", "Coimbra", "3000"),
    ("Faro", "Faro", "8000"),
    ("Torres Vedras", "Lisboa", "2560"),
]
STREETS = ["Rua Direita", "Avenida da República", "Rua do Comércio", "Largo do Rossio", "Rua das Flores"]
STATUS_WEIGHTS = [("lead", 35), ("contacted", 25), ("qualified", 18), ("customer", 15), ("inactive", 7)]
ACTIVITY_SAMPLES = [
    ("call", "Intro call", "Walked through their current process and pain points."),
    ("call", "Follow-up call", "They want a quote before the end of the month."),
    ("email", "Sent pricing proposal", "Attached the standard proposal with volume discount."),
    ("email", "Shared case study", ""),
    ("meeting", "On-site demo", "Demo went well. Decision maker joined for the last 20 minutes."),
    ("meeting", "Quarterly review", "Happy with service; interested in expanding to a second site."),
    ("note", "Budget approved for Q1", ""),
    ("note", "Prefers contact by email", "Avoid calling before 10:00."),
]


def ascii_slug(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


class Command(BaseCommand):
    help = "Create sample customers (with activity history) so the app has data to show."

    def add_arguments(self, parser):
        parser.add_argument("count", nargs="?", type=int, default=30)
        parser.add_argument("--clear", action="store_true", help="Delete all existing customers first.")

    def handle(self, *args, count, clear, **options):
        if clear:
            deleted, _ = Customer.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing records.")

        users = list(get_user_model().objects.filter(is_active=True))
        statuses = [s for s, _ in STATUS_WEIGHTS]
        weights = [w for _, w in STATUS_WEIGHTS]
        now = timezone.now()

        for _ in range(count):
            first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            company = random.choice(COMPANIES)
            city, region, postcode = random.choice(CITIES)
            owner = random.choice(users) if users and random.random() < 0.85 else None

            customer = Customer.objects.create(
                first_name=first,
                last_name=last,
                company=company,
                job_title=random.choice(TITLES),
                status=random.choices(statuses, weights)[0],
                owner=owner,
                created_by=owner,
                email=f"{ascii_slug(first)}.{ascii_slug(last)}@{ascii_slug(company).replace(' ', '')}.pt",
                phone=f"+351 9{random.randint(10, 39)} {random.randint(100, 999)} {random.randint(100, 999)}",
                address=f"{random.choice(STREETS)} {random.randint(1, 200)}",
                city=city,
                state=region,
                zipcode=f"{postcode}-{random.randint(1, 999):03d}",
            )
            # auto_now_add can't be set on create, so backdate afterwards for realistic dates.
            created = now - timedelta(days=random.randint(5, 120))
            Customer.objects.filter(pk=customer.pk).update(created_at=created, updated_at=created)

            for kind, subject, details in random.sample(ACTIVITY_SAMPLES, random.randint(0, 4)):
                activity = Activity.objects.create(
                    customer=customer, kind=kind, subject=subject, details=details, created_by=owner
                )
                when = created + timedelta(days=random.randint(0, (now - created).days), hours=random.randint(8, 18))
                Activity.objects.filter(pk=activity.pk).update(created_at=min(when, now))

        self.stdout.write(self.style.SUCCESS(f"Created {count} sample customers."))
