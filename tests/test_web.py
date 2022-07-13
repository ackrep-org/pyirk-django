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

    def test_search_api(self):
        url = "/search/?q=set"
        res = self.client.get(url)

        soup = BeautifulSoup(res.content.decode("utf8"), "lxml")

        script_tags = soup.findAll("script")

        for tag in script_tags:
            # this assumes that Item I13 has not changed its label since the test was written
            if tag.contents and (tag.contents[0] == '\\"I13(\\\\\\"mathematical set\\\\\\")\\"'):
                break
        else:
            self.assertTrue(False, "could not find expected copy-string in response")

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

        # url = reverse("entitypage", kwargs=dict(key_str="I15"))
        # res = self.client.get(url)
        url = "/search/?q=bound"
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)

    def test_sparql_page(self):
        url = reverse("sparqlpage")
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)

        url = "/sparql/?query=%0D%0APREFIX+%3A+%3Cerk%3A%2F%3E%0D%0ASELECT+*%0D%0AWHERE+%7B%0D%0A++++%3Fs+%3AR5+%3Fo.%0D%0A%7D%0D%0A"
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)

    def test_reload_via_url(self):
        url = reverse("reload")
        res = self.client.get(url)
        self.assertEquals(res.status_code, 302)

