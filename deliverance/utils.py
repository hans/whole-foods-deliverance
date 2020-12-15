import toml
import random
import logging
import re
from time import sleep
from functools import wraps
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        TimeoutException)

from pint import Quantity

from config import CONF_PATH, Locators, Patterns, \
                   UNIT_REGISTRY, UNIT_STRING_REPLACEMENTS

log = logging.getLogger(__name__)


def conf_dependent(conf_key):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'conf' not in kwargs:
                try:
                    kwargs['conf'] = toml.load(CONF_PATH)[conf_key]
                except Exception:
                    log.error("{}() requires a config file at"
                              " '{}' with key '{}'".format(func.__name__,
                                                           CONF_PATH,
                                                           conf_key))
                    return
            try:
                return func(*args, **kwargs)
            except Exception:
                log.error('Action failed:', exc_info=True)
                return
        return wrapper
    return decorator


def remove_qs(url):
    """Remove URL query string the lazy way"""
    return url.split('?')[0]


def jitter(seconds):
    """This seems unnecessary"""
    pct = abs(random.gauss(.2, .05))
    sleep(random.uniform(seconds*(1-pct), seconds*(1+pct)))


def timestamp():
    return datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')


def dump_toml(obj, name):
    filepath = '{}_{}.toml'.format(name, timestamp())
    log.info('Writing {} items to: {}'.format(len(obj), filepath))
    with open(filepath, 'w', encoding='utf-8') as f:
        toml.dump(obj, f)


def dump_source(driver):
    filename = 'source_dump{}_{}.html'.format(
        urlparse(driver.current_url).path.replace('/', '-')
        .replace('.html', ''),
        timestamp()
    )
    log.info('Dumping page source to: ' + filename)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)


def parse_units(item_title: str) -> Optional[Quantity]:
    """
    Attempt to extract quantity information from an item title.
    """
    ret = None

    item_title = item_title.lower()
    for search, repl in UNIT_STRING_REPLACEMENTS:
        item_title = re.sub(search, repl, item_title)

    for amount, unit in Patterns.UNIT_PATTERN.findall(item_title):
        result_units_str = f"{amount} {unit}"

        # Now pass off to pint.
        print("\t", result_units_str)
        try:
            ret = UNIT_REGISTRY.parse_expression(result_units_str)
        except Exception as e:
            log.warn(f"Failed to parse unit string '{result_units_str}'", exc_info=e)

        return ret

    return None


###########
# Elements
#########

class element_clickable:
    """An expected condition for use with WebDriverWait"""

    def __init__(self, element):
        self.element = element

    def __call__(self, driver):
        if self.element.is_displayed() and self.element.is_enabled():
            return self.element
        else:
            return False


class presence_of_any_elements_located(object):
    """An expected condition for use with WebDriverWait"""

    def __init__(self, locators):
        self.locators = locators

    def __call__(self, driver):
        for locator in self.locators:
            elements = driver.find_elements(*locator)
            if elements:
                return elements
        return False


class element_does_not_have_class(object):
    """
    Expected condition for use with WebDriverWait
    """

    def __init__(self, locator, css_class):
        self.locator = locator
        self.css_class = css_class

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        class_string = " " + element.get_attribute("class") + " "
        if f" {self.css_class} " in class_string:
            return False
        else:
            return True


def no_ewc_spinner(driver):
    """expected condition"""
    # There are two EWC spinners. #1 appears on page load; #2 appears when the
    # cart is modified (e.g. an item is added) from the page.

    # #1
    ewc1 = driver.find_element(*Locators.CART_FLYOUT_CONTENT)
    ewc1_classes = " " + ewc1.get_attribute("class") + " "
    if " nav-spinner " in ewc1_classes:
        return False

    # #2
    ewc2 = driver.find_element(*Locators.EWC_SPINNER)
    if ewc2.is_displayed():
        return False

    return True


def wait_for_elements(driver, locators, timeout=5):
    if not isinstance(locators, list):
        locators = [locators]
    try:
        return WebDriverWait(driver, timeout).until(
            presence_of_any_elements_located(locators)
        )
    except TimeoutException:
        log.error("Timed out waiting for target element: {}".format(locators))
        raise


def wait_for_element(driver, locators, **kwargs):
    return wait_for_elements(driver, locators, **kwargs)[0]


def get_element_text(element, xpath=None):
    if xpath is not None:
        element = element.find_element_by_xpath(xpath)
    return element.get_attribute('innerText').strip()


def click_when_enabled(driver, element, timeout=10):
    element = WebDriverWait(driver, timeout).until(
        element_clickable(element)
    )
    try:
        driver.execute_script("arguments[0].scrollIntoView();", element)
        element.click()
    except ElementClickInterceptedException:
        delay = 1
        log.warning('Click intercepted. Waiting for {}s'.format(delay))
        sleep(delay)
        element.click()
