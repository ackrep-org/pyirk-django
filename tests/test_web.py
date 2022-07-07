from django.test import TestCase
from django.urls import reverse
from ipydex import IPS
from bs4 import BeautifulSoup

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

        txt = """
        <myscript id="copy_text_0" type="application/json">"test"</myscript>
        <myscript id="copy_text_1" type="application/xyz">"test"</myscript>
        <myscript id="copy_text_2" type="application/json">"test"</myscript>
        <p>some text</p>
        """
        bs = BeautifulSoup(txt, 'html.parser')
        res = bs.find_all("myscript")
        for tag in res:
            if tag.attrs.get("type") == "application/json":
                tag.name = "script"
        txt2 = str(bs)

        url = reverse("entitypage", kwargs=dict(key_str="I15"))
        res = self.client.get(url)
        url = reverse("entitypage", kwargs=dict(key_str="I3007"))
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)

