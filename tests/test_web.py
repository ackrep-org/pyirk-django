from django.test import TestCase
from django.urls import reverse
from django.db.models import Q
from textwrap import dedent as twdd
from ipydex import IPS

from bs4 import BeautifulSoup

# noinspection PyUnresolvedReferences
import mainapp.util

# noinspection PyUnresolvedReferences
from mainapp import models

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
            if tag.contents and (tag.contents[0] == '\\"I13[\\\\\\"mathematical set\\\\\\"]\\"'):
                break
        else:
            self.assertTrue(False, "could not find expected copy-string in response")

    def test_entity_detail_view(self):

        url = reverse("entitypage", kwargs=dict(key_str="I12"))
        res = self.client.get(url)
        content = res.content.decode("utf8")
        self.assertIn('<span class="entity-key highlight"><a href="/e/I12">I12</a></span>', content)

        src1 = twdd(
            """
            <span class="entity-key highlight"><a href="/e/I12">I12</a></span><!--
            --><!--
            --><!--
            -->["<span class="entity-label" title="base class for any knowledge object of interrest in the field of mathematics">mathematical object</span>"]<!--
            -->
            <div class="entity-description">base class for any knowledge object of interrest in the field of mathematics</div>
            """
        )
        self.assertIn(src1, content)

        url = "/search/?q=bound"
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)

    def test_entity_detail_view2(self):
        url = reverse("entitypage", kwargs=dict(key_str="I9907"))
        res = self.client.get(url)

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

    def test_LanguageSpecifiedString(self):
        t1 = models.LanguageSpecifiedString.objects.create(langtag="en", content="test1")
        t2 = models.LanguageSpecifiedString.objects.create(langtag="de", content="test1")
        res = models.LanguageSpecifiedString.objects.filter(langtag="de")
        self.assertGreaterEqual(len(res), 1)

        self.assertIn(t2, res)
        w = models.Entity.objects.get(key_str="I900")
        res = w.label.filter(langtag="en")
        self.assertGreaterEqual(len(res), 1)

        labels = w.label.all()

        q = "sta"
        res = models.Entity.objects.filter(
            Q(label__content__icontains=q) | Q(key_str__icontains=q) | Q(description__icontains=q)
        )
        self.assertGreater(len(res), 5)
