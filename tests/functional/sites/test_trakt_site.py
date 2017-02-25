from unittest import TestCase

from RatS.sites.trakt_site import Trakt


class TraktSiteTest(TestCase):
    def test_login(self):
        self.site = Trakt()
        self.assertIn(self.site.USERNAME, self.site.browser.page_source)

    def tearDown(self):
        self.site.browser.quit()