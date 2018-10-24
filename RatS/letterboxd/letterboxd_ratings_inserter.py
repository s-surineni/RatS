import datetime
import os
import sys
import time

from selenium.common.exceptions import StaleElementReferenceException, ElementNotInteractableException, \
    NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions, ui
from selenium.webdriver.support.wait import WebDriverWait

from RatS.base.base_ratings_inserter import RatingsInserter
from RatS.letterboxd.letterboxd_site import Letterboxd
from RatS.utils.command_line import print_progress_bar
from RatS.utils.file_impex import save_movies_to_csv

TIMESTAMP = datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')
CSV_FILE_NAME = TIMESTAMP + '_converted_for_Letterboxd.csv'


class LetterboxdRatingsInserter(RatingsInserter):
    def __init__(self, args):
        super(LetterboxdRatingsInserter, self).__init__(Letterboxd(args), args)
        self.progress_counter_selector = '.import-progress #import-count strong'

    def insert(self, movies, source):
        sys.stdout.write('\r===== {site_displayname}: posting {movies_count} movies\r\n'.format(
            site_displayname=self.site.site_displayname,
            movies_count=len(movies)
        ))
        sys.stdout.flush()

        save_movies_to_csv(movies, folder=self.exports_folder, filename=CSV_FILE_NAME, rating_source=source)
        self.upload_csv_file(len(movies))

        sys.stdout.write('\r\n===== {site_displayname}: The file with {movies_count} movies was uploaded '
                         'and successfully processed by the servers. '
                         'You may check your {site_name} account later.\r\n'.format(
                             site_displayname=self.site.site_displayname,
                             movies_count=len(movies),
                             site_name=self.site.site_name
                         ))
        sys.stdout.flush()

        self.site.browser_handler.kill()

    def upload_csv_file(self, movies_count):
        self.site.browser.get('https://letterboxd.com/import/')
        time.sleep(1)
        filename = os.path.join(self.exports_folder, CSV_FILE_NAME)
        self._fill_filename_into_upload_form(filename)

        wait = ui.WebDriverWait(self.site.browser, 600)
        self._wait_for_movie_matching(wait, movies_count)
        self._wait_for_import_processing(wait, movies_count)

    def _fill_filename_into_upload_form(self, filename):
        iteration = 0
        while True:
            iteration += 1
            try:
                self.site.browser.execute_script(
                    "document.getElementById('imdb-form').setAttribute('style', 'visibility: visible;')"
                )
                self.site.browser.find_element_by_id('upload-imdb-import').clear()
                self.site.browser.find_element_by_id('upload-imdb-import').send_keys(os.path.join(filename))
                break
            except (NoSuchElementException, ElementNotInteractableException) as e:
                if iteration > 10:
                    raise e
                time.sleep(iteration * 1)
                continue

    def _wait_for_movie_matching(self, wait, movies_count):
        time.sleep(5)
        disabled_import_button_selector = "//div[@class='import-buttons']//a[@data-track-category='Import' and contains(@class, 'import-button-disabled')]"  # pylint: disable=line-too-long
        enabled_import_button_selector = "//div[@class='import-buttons']//a[@data-track-category='Import' and not(contains(@class, 'import-button-disabled'))]"  # pylint: disable=line-too-long

        wait.until(lambda driver: driver.find_element_by_xpath(disabled_import_button_selector))
        sys.stdout.write('\r\n===== {site_displayname}: matching the movies...\r\n'.format(
            site_displayname=self.site.site_displayname
        ))
        sys.stdout.flush()

        self._print_progress(movies_count)

        wait.until(lambda driver: driver.find_element_by_xpath(enabled_import_button_selector))
        self.site.browser.find_element_by_xpath(enabled_import_button_selector).click()

    def _wait_for_import_processing(self, wait, movies_count):
        time.sleep(5)

        wait.until(lambda driver: driver.find_element_by_id('import-count'))
        sys.stdout.write('\r\n===== {site_displayname}: processing the movies...\r\n'.format(
            site_displayname=self.site.site_displayname
        ))
        sys.stdout.flush()

        self._print_progress(movies_count)

        WebDriverWait(self.site.browser, 600).until(
            expected_conditions.invisibility_of_element_located((By.ID, 'import-count'))
        )

    def _print_progress(self, movies_count):
        while len(self.site.browser.find_elements_by_css_selector(self.progress_counter_selector)) is not 0:
            try:
                counter = int(self.site.browser.find_element_by_css_selector(self.progress_counter_selector).text)
                if not self.standard_progress_bar:
                    self.standard_progress_bar = ProgressBar(
                        max_value=movies_count, redirect_stdout=True)
                self.standard_progress_bar.update(counter)
            except (StaleElementReferenceException, NoSuchElementException):
                pass
            time.sleep(1)
        self.standard_progress_bar.update(movies_count)
        self.standard_progress_bar.finish()
