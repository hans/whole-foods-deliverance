import re

from pint import UnitRegistry
import requests
from selenium.webdriver.common.by import By
import toml

CONF_PATH = 'conf.toml'
USER_DATA_DIR = 'chrome-user-data'
BASE_URL = 'https://www.amazon.com/'
try:
    options = toml.load(CONF_PATH)['options']
    if options.get('use_smile'):
        BASE_URL = 'https://smile.amazon.com/'
    if options.get('chrome_data_dir'):
        USER_DATA_DIR = options['chrome_data_dir']
except Exception:
    pass

NAV_TIMEOUT = 20
INTERVAL = 25

VALID_SERVICES = [
    'Whole Foods',
    'Amazon Fresh'
]

UNIT_REGISTRY = UnitRegistry()
# Load default unit additions
UNIT_REGISTRY.load_definitions("units.txt")
# TODO custom overrides

# Replacements to perform on an item title before unit parsing
UNIT_STRING_REPLACEMENTS = [
    ("(?i)fl ozs?", "fluid_ounce"),
    ("(?i)365 everyday", ""),
]

class Patterns:
    AUTH_URL = BASE_URL + 'ap/'
    NOT_LOGGED_IN = "Hello, Sign in"
    OOS_URL = 'gp/buy/itemselect/handlers/display.html'
    OOS = "This item is no longer available"
    THROTTLE_URL = 'throttle.html'
    NO_SLOTS_MULTI = "No.*delivery windows are available"
    SEARCH_PATTERN = "https://www.amazon.com/s?k={term}&i={service}&ref=nb_sb_noss_2"

    # Sort by length so that we get the longest applicable unit string for the parser
    _unit_strings = sorted(
        [unit + suffix for unit in UNIT_REGISTRY._units.keys()
         for suffix in UNIT_REGISTRY._suffixes.keys()],
         reverse=True, key=len)
    UNIT_PATTERN = re.compile(
        f"(?i)(\d+(?:\.\d+)?)\s*({{0}})".format("|".join(_unit_strings)))


class Locators:
    LOGIN = (By.ID, 'nav-link-accountList')
    OOS_ITEM = (By.XPATH, "//*[contains(@class, ' item-row')]")
    OOS_CONTINUE = (By.XPATH, "//*[@name='continue-bottom']")
    CART_ITEMS = (By.XPATH, "//div[@data-name='Active Items']"
                            "/*[contains(@class, 'sc-list-item')]")
    THROTTLE_CONTINUE = (By.XPATH, "//*[contains(@id, 'throttle') and "
                                   "@role='button']")
    PAYMENT_ROW = (By.XPATH, "//*[starts-with(@class, 'payment-row')]")

    SEARCH_RESULT = (By.XPATH, "//div[@id='search']//*[@data-asin!='']")


class SlotLocators:
    def __init__(self, slot_type='single'):
        if slot_type == 'single':
            self.CONTAINER = (By.CLASS_NAME, 'ufss-slotselect-container')
            self.SLOT = (
                By.XPATH,
                "//*[contains(@class, 'ufss-slot ') and "
                "contains(@class, 'ufss-available')]"
            )
            self.CONTINUE = (
                By.XPATH,
                "//*[contains(@class, 'ufss-overview-continue-button')]"
            )
        elif slot_type == 'multi':
            self.CONTAINER = (By.ID, 'slot-container-root')
            self.SLOT = (
                By.XPATH,
                "//*[starts-with(@id, 'slot-button-root-20') and "
                "not(contains(@class, 'disabled'))]"
            )
            self.CONTINUE = (
                By.XPATH,
                "//input[@class='a-button-text a-declarative' and "
                "@type='submit']"
            )
        else:
            raise ValueError("Unrecognized slot type '{}'".format(slot_type))


class SiteConfig:
    def __init__(self, service):
        if service not in VALID_SERVICES:
            raise ValueError(
                "Invalid service '{}'\n Services implemented: \n{}".format(
                    service, VALID_SERVICES
                )
            )
        self.service = service
        self.BASE_URL = BASE_URL
        self.Locators = Locators()
        self.Patterns = Patterns()
        self.routes = {}
        self.routes['SLOT_SELECT'] = {
            'route_start': BASE_URL,
            'waypoints': [
                (
                    (By.ID, 'nav-cart'),
                    'gp/cart/view.html'
                ),
                (
                    (By.XPATH, "//*[contains(text(),'Checkout {}')]/..".format(
                        service
                    )),
                    'alm/byg'
                ),
                (
                    (By.XPATH, "//span[contains(@class, 'byg-continue-button')]"),
                    'alm/substitution'
                ),
                (
                    (By.ID, 'subsContinueButton'),
                    'gp/buy/shipoptionselect/handlers/display.html'
                )
            ]
        }
        self.routes['CHECKOUT'] = {
            'route_start': BASE_URL + 'gp/buy/shipoptionselect/handlers/display.html',
            'waypoints': [
                (
                    [SlotLocators().CONTINUE, SlotLocators('multi').CONTINUE],
                    'gp/buy/payselect/handlers/display.html'
                ),
                (
                    (By.ID, 'continue-top'),
                    'gp/buy/spc/handlers/display.html',
                    'select_payment_method'  # function to be called before nav
                ),
                (
                    (By.XPATH, "//input[contains(@class, 'place-your-order-button')]"),
                    'gp/buy/thankyou/handlers/display.html'
                )
            ]
        }

    @property
    def cart_endpoint(self):
        if self.service == 'Amazon Fresh':
            return 'cart/fresh'
        else:
            return 'cart/localmarket'

    def search_endpoint(self, search_term):
        search_term = requests.utils.quote(search_term)
        if self.service == "Whole Foods":
            return Patterns.SEARCH_PATTERN.format(term=search_term, service="wholefoods")
        elif self.service == "Amazon Fresh":
            return Patterns.SEARCH_PATTERN.format(term=search_term, service="amazonfresh")
