from django.test import TestCase
from django.urls import reverse
from ipydex import IPS

# noinspection PyUnresolvedReferences
import mainapp.util

# The tests can be run with
# `python manage.py test`
# `python manage.py test --rednose` # with colors


class TestMainApp1(TestCase):
    def setUp(self):
        mainapp.util.reload_data()

    def test_home_page1(self):

        # get url by its unique name, see urls.py

        url = reverse("landingpage")
        res = self.client.get(url)

        # `utc` means "unit test comment"
        # this is a simple mechanism to ensure the desired content actually was delivered
        self.assertEquals(res.status_code, 200)
        self.assertContains(res, "utc_landing_page")
        self.assertNotContains(res, "utc_debug_page")

    def test_entity_detail_view(self):
        url = reverse("entitypage", kwargs=dict(key_str="I15"))
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)
