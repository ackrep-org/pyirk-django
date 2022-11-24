import os
import urllib
import json

from bs4 import BeautifulSoup
from django.test import TransactionTestCase, TestCase  # noqa
from django.urls import reverse
from django.db.models import Q
from textwrap import dedent as twdd
# noinspection PyUnresolvedReferences
from ipydex import IPS  # noqa
from django.conf import settings
# this is relevant for switching off some database optimizations which are incompatible with django.test.TestCase
# because every testcase rewinds its transactions
settings.RUNNING_TESTS = True


# noinspection PyUnresolvedReferences
import pyerkdjango.util  # noqa
import pyerk  # noqa

# noinspection PyUnresolvedReferences
from pyerkdjango import models  # noqa

# The tests can be run with
# `python manage.py test`
# `python manage.py test --rednose` # with colors


# noinspection PyUnresolvedReferences
from pyerkdjango.util import w, u, q_reverse, urlquote  # noqa

ERK_ROOT_DIR = pyerk.aux.get_erk_root_dir()

# TODO:
# currently loading of ocse is hardcoded in views -> util; This should be refactored in the future (use config file)
# TEST_DATA_PATH2 = os.path.join(ERK_ROOT_DIR, "erk-data", "ocse", "control_theory1.py")
os.environ["UNITTEST"] = "True"


class Test_01_Basics(TestCase):
    """
    Ensure that the testmodule itself works as expected
    """

    def test01_home_page(self):
        url = reverse("landingpage")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test02_home_page(self):
        # load the landing page again to see if tests interact (not wantend)
        url = reverse("landingpage")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)


class Test_02_MainApp(TestCase):
    def setUp(self):
        print("In method", pyerkdjango.util.aux.bgreen(self._testMethodName))
        # set `speedup` to False because TestCase disallows things like `transaction.set_autocommit(False)`
        pyerkdjango.util.reload_data_if_necessary(speedup=False)

    def test01_home_page1(self):

        # get url by its unique name, see urls.py

        url = reverse("landingpage")
        res = self.client.get(url)

        # `utc` means "unit test comment"
        # this is a simple mechanism to ensure the desired content actually was delivered
        self.assertEquals(res.status_code, 200)
        self.assertContains(res, "utc_landing_page")

    def test02_search_api(self):
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

    def test03_entity_detail_view(self):
        url = reverse("entitypage", kwargs=dict(uri=w("I12")))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf8")
        self.assertIn(
            '<span class="entity-key highlight"><a href="/e/erk%253A%252Fbuiltins%2523I12">I12</a></span>', content
        )

        src1 = twdd(
            """
            <span class="entity-key highlight"><a href="/e/erk%253A%252Fbuiltins%2523I12">I12</a></span><!--
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

    def test04_entity_detail_view2(self):
        # test displaying an entity from a loaded module

        # note: currently the ocse is already loaded in the views
        # mod1 = pyerk.erkloader.load_mod_from_path(TEST_DATA_PATH2, prefix="ct")
        url = reverse("entitypage", kwargs=dict(uri=w("ct__I9907")))
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)
        # TODO: add some actual test code here (which was probaly forgotten earlier)
        # likely it was intended to test context-rendering

    def test05_sparql_page(self):
        url = reverse("sparqlpage")
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)

        url = (
            "/sparql/?query=%0D%0APREFIX+%3A+%3Cerk%3A%2F%3E%0D%0ASELECT+*%0D%0AWHERE"
            "+%7B%0D%0A++++%3Fs+%3AR5+%3Fo.%0D%0A%7D%0D%0A"
        )
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)

    def test06_reload_via_url(self):
        url = reverse("reload")
        res = self.client.get(url)
        self.assertEquals(res.status_code, 302)

    def test07_LanguageSpecifiedString(self):
        _ = models.LanguageSpecifiedString.objects.create(langtag="en", content="test1")
        t2 = models.LanguageSpecifiedString.objects.create(langtag="de", content="test1")
        res = models.LanguageSpecifiedString.objects.filter(langtag="de")
        self.assertGreaterEqual(len(res), 1)

        self.assertIn(t2, res)
        x = models.Entity.objects.get(uri=u("I900"))
        res = x.label.filter(langtag="en")
        self.assertGreaterEqual(len(res), 1)

        _ = x.label.all()

        q = "sta"
        res = models.Entity.objects.filter(
            Q(label__content__icontains=q) | Q(uri__icontains=q) | Q(description__icontains=q)
        )
        self.assertGreater(len(res), 5)

    def test08_web_visualization1(self):
        # mod1 = pyerk.erkloader.load_mod_from_path(TEST_DATA_PATH2, prefix="ct")
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

        # note: when hovering over the links firefox displays the unquoted version of this url
        # i.e.: /e/erk:%2Focse%2F0.2#I9906/v
        txt = '<a href="/e/erk%253A%252Fmath%252F0.2%2523I9906/v">I9906'

        self.assertIn(txt, content)

        url_vis = reverse("entityvisualization", kwargs={"uri": urlquote(u("ma__I9906"))})
        url_vis_empirical = "/e/erk%253A%252Fmath%252F0.2%2523I9906/v"
        self.assertIn(url_vis_empirical, content)

        assert url_vis.endswith("/v")

        # the following is necessary due to the temporary replace-hack views.entity_view, see bookmark://vis01

        # noinspection PyUnresolvedReferences
        url_vis2 = urllib.parse.unquote(url_vis)
        url_vis3 = urllib.parse.unquote(url_vis2)
        url_vis_empirical2 = urllib.parse.unquote(url_vis_empirical)
        url_vis_empirical3 = urllib.parse.unquote(url_vis_empirical2)
        self.assertEqual(url_vis_empirical3, url_vis3)

        # test label formating

        soup = BeautifulSoup(content, "lxml")
        svg_tag = soup.findAll("svg")[0]

        # TODO: make this independet of changing data
        link1, link2 = svg_tag.findAll(name="a", attrs={"href": url_vis_empirical})

        self.assertEqual(link1.parent.parent.name, "g")
        self.assertEqual(link1.parent.parent.get("class"), ["node"])
        self.assertEqual(link1.text, "I9906")
        self.assertEqual(link2.text, '["square matrix"]')

    def test09_get_auto_complete_list_api(self):

        url = reverse("get_auto_complete_list")
        res = self.client.get(url)

        completion_suggestions = json.loads(res.content)["data"]

        self.assertGreater(len(completion_suggestions), 50)

    def test10_editor_view(self):

        url = reverse("show_editor")
        res = self.client.get(url)
        self.assertEquals(res.status_code, 200)
