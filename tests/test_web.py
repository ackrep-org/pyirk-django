import os

from django.test import TransactionTestCase, TestCase
from django.urls import reverse
from django.db.models import Q
from textwrap import dedent as twdd
# noinspection PyUnresolvedReferences
from ipydex import IPS
from django.conf import settings

from bs4 import BeautifulSoup

# noinspection PyUnresolvedReferences
import mainapp.util
import pyerk

# noinspection PyUnresolvedReferences
from mainapp import models

# The tests can be run with
# `python manage.py test`
# `python manage.py test --rednose` # with colors

# this is relevant for switching of some database optimizations which are incompatible with django.test.TestCase
# because every testcase rewinds its transactions
settings.RUNNING_TESTS = True

# noinspection PyUnresolvedReferences
from mainapp.util import w, u, q_reverse

ERK_ROOT_DIR = pyerk.aux.get_erk_root_dir()
TEST_DATA_PATH2 = os.path.join(ERK_ROOT_DIR, "erk-data", "control-theory", "control_theory1.py")


# we need TransactionTestCase instead of simpler (and faster) TestCase because of the non-atomic way
class TestMainApp1(TestCase):
    def setUp(self):

        # set `speedup` to False because TestCase disallows things like `transaction.set_autocommit(False)`
        print("In method", mainapp.util.aux.bgreen(self._testMethodName))
        mainapp.util.reload_data(speedup=False)

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
        url = reverse("entitypage", kwargs=dict(uri=w("I12")))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf8")
        self.assertIn(
            '<span class="entity-key highlight"><a href="/e/erk%3A%2Fbuiltins%23I12">I12</a></span>', content
        )

        src1 = twdd(
            """
            <span class="entity-key highlight"><a href="/e/erk%3A%2Fbuiltins%23I12">I12</a></span><!--
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
        # test displaying an entity from a loaded module
        mod1 = pyerk.erkloader.load_mod_from_path(TEST_DATA_PATH2, prefix="ct")
        url = reverse("entitypage", kwargs=dict(uri=w("ct__I9907")))
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)
        # TODO: add some actual test code here (which was probaly forgotten earlier)
        # likely it was intended to test context-rendering

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
        x = models.Entity.objects.get(uri=u("I900"))
        res = x.label.filter(langtag="en")
        self.assertGreaterEqual(len(res), 1)

        labels = x.label.all()

        q = "sta"
        res = models.Entity.objects.filter(
            Q(label__content__icontains=q) | Q(uri__icontains=q) | Q(description__icontains=q)
        )
        self.assertGreater(len(res), 5)

    def test_web_visualization1(self):
        mod1 = pyerk.erkloader.load_mod_from_path(TEST_DATA_PATH2, prefix="ct")
        self.assertIn("ct", pyerk.ds.uri_prefix_mapping.b)

        url = reverse("entityvisualization", kwargs=dict(uri=w("ct__I9907")))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        test_str = f"utc_visualization_of_{u('ct__I9907')}"
        content = res.content.decode("utf8")

        with open("tmp.txt", "w") as txtfile:
            txtfile.write(content)
        self.assertIn(test_str, content)

        # test if labels have visualization links:

        self.assertIn('<a href="/e/erk%3A%2Focse%2F0.2%23I9906/v">I9906', content)

        url2 = q_reverse("entityvisualization", uri=u("ct__I9906"))

        self.assertIn(url2, content)

        # test label formating

        soup = BeautifulSoup(content, "lxml")
        svg_tag = soup.findAll("svg")[0]

        # TODO: make this independet of changing data
        link1, link2 = svg_tag.findAll(name="a", attrs={"href": url2})

        self.assertEqual(link1.parent.parent.name, "g")
        self.assertEqual(link1.parent.parent.get("class"), ["node"])
        self.assertEqual(link1.text, "I9906")
        self.assertEqual(link2.text, '["square matrix"]')
