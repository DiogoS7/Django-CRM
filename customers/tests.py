from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Activity, Customer


def make_customer(**overrides):
    data = {
        "first_name": "Ana",
        "last_name": "Silva",
        "email": "ana@example.com",
        "phone": "+351 912 345 678",
        "address": "Rua Direita 10",
        "city": "Lisboa",
        "zipcode": "1100-001",
    }
    data.update(overrides)
    return Customer.objects.create(**data)


def form_data(**overrides):
    data = {
        "first_name": "Rui",
        "last_name": "Costa",
        "company": "Lusotec",
        "job_title": "CEO",
        "status": "lead",
        "owner": "",
        "email": "rui@example.com",
        "phone": "912000000",
        "address": "Av. da Liberdade 1",
        "city": "Lisboa",
        "zipcode": "1250-096",
    }
    data.update(overrides)
    return data


class AnonymousAccessTests(TestCase):
    def test_pages_redirect_to_login(self):
        customer = make_customer()
        urls = [
            reverse("customers:home"),
            reverse("customers:list"),
            reverse("customers:create"),
            reverse("customers:detail", args=[customer.pk]),
            reverse("customers:update", args=[customer.pk]),
            reverse("customers:delete", args=[customer.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)


class CustomerViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester", password="s3cure-pass-123")
        self.client.force_login(self.user)

    def test_home_dashboard_counts(self):
        make_customer(status="lead", owner=self.user)
        make_customer(status="customer", email="b@example.com")
        response = self.client.get(reverse("customers:home"))
        self.assertEqual(response.status_code, 200)
        counts = {s["value"]: s["count"] for s in response.context["pipeline"]}
        self.assertEqual(counts["lead"], 1)
        self.assertEqual(counts["customer"], 1)
        self.assertEqual(response.context["my_open_count"], 1)

    def test_create_customer_records_author(self):
        response = self.client.post(reverse("customers:create"), form_data(owner=self.user.pk))
        customer = Customer.objects.get(email="rui@example.com")
        self.assertRedirects(response, customer.get_absolute_url())
        self.assertEqual(customer.created_by, self.user)
        self.assertEqual(customer.owner, self.user)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(reverse("customers:create"), form_data(email="not-an-email"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Customer.objects.exists())

    def test_missing_customer_returns_404(self):
        response = self.client.get(reverse("customers:detail", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_detail_page_renders(self):
        customer = make_customer()
        Activity.objects.create(customer=customer, kind="call", subject="Intro call")
        response = self.client.get(customer.get_absolute_url())
        self.assertContains(response, "Intro call")
        self.assertEqual(response.context["next_stage"]["value"], "contacted")

    def test_delete_requires_post(self):
        customer = make_customer()
        url = reverse("customers:delete", args=[customer.pk])

        self.client.get(url)
        self.assertTrue(Customer.objects.filter(pk=customer.pk).exists())

        self.client.post(url)
        self.assertFalse(Customer.objects.filter(pk=customer.pk).exists())

    def test_update_status_logs_activity(self):
        customer = make_customer()
        data = form_data(email=customer.email, status="qualified")
        self.client.post(reverse("customers:update", args=[customer.pk]), data)
        customer.refresh_from_db()
        self.assertEqual(customer.status, "qualified")
        self.assertTrue(customer.activities.filter(kind="status").exists())

    def test_set_status_via_path(self):
        customer = make_customer()
        url = reverse("customers:set_status", args=[customer.pk])

        self.assertEqual(self.client.get(url).status_code, 405)

        self.client.post(url, {"status": "contacted"})
        customer.refresh_from_db()
        self.assertEqual(customer.status, "contacted")
        self.assertEqual(customer.activities.get().subject, "Lead → Contacted")

        self.client.post(url, {"status": "bogus"})
        customer.refresh_from_db()
        self.assertEqual(customer.status, "contacted")

    def test_log_activity(self):
        customer = make_customer()
        url = reverse("customers:log_activity", args=[customer.pk])
        self.client.post(url, {"kind": "meeting", "subject": "Demo", "details": "Went well"})
        activity = customer.activities.get()
        self.assertEqual(activity.kind, "meeting")
        self.assertEqual(activity.created_by, self.user)

    def test_log_activity_rejects_manual_status_kind(self):
        customer = make_customer()
        url = reverse("customers:log_activity", args=[customer.pk])
        response = self.client.post(url, {"kind": "status", "subject": "Fake"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(customer.activities.exists())

    def test_search_matches_every_word(self):
        make_customer(first_name="Ana", city="Lisboa")
        make_customer(first_name="Ana", city="Porto", email="ana2@example.com")
        make_customer(first_name="Bruno", city="Lisboa", email="b@example.com")

        response = self.client.get(reverse("customers:list"), {"q": "ana lisboa"})
        results = list(response.context["page"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].city, "Lisboa")

    def test_list_filters_and_sorting(self):
        make_customer(first_name="Zé", status="customer", owner=self.user)
        make_customer(first_name="Ana", status="lead", email="b@example.com")

        response = self.client.get(reverse("customers:list"), {"view": "mine"})
        self.assertEqual([c.first_name for c in response.context["page"]], ["Zé"])

        response = self.client.get(reverse("customers:list"), {"status": "lead"})
        self.assertEqual([c.first_name for c in response.context["page"]], ["Ana"])

        response = self.client.get(reverse("customers:list"), {"sort": "-status"})
        self.assertEqual([c.status for c in response.context["page"]], ["customer", "lead"])

        # Unknown sort keys fall back to name instead of crashing.
        response = self.client.get(reverse("customers:list"), {"sort": "password"})
        self.assertEqual(response.status_code, 200)


class RegistrationTests(TestCase):
    def test_register_logs_user_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "new@example.com",
                "password1": "a-Strong-pass-987",
                "password2": "a-Strong-pass-987",
            },
        )
        self.assertRedirects(response, reverse("customers:home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user("existing", email="taken@example.com", password="x-Pass-12345")
        response = self.client.post(
            reverse("register"),
            {
                "username": "another",
                "first_name": "A",
                "last_name": "B",
                "email": "TAKEN@example.com",
                "password1": "a-Strong-pass-987",
                "password2": "a-Strong-pass-987",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="another").exists())
