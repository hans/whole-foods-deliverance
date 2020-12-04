from collections import namedtuple
import re

import numpy as np
from pint import Quantity

from config import UNIT_REGISTRY, UNIT_STRING_REPLACEMENTS


class ShoppingListItem(object):

    def __init__(self, name, quantity_str: Quantity):
        self.name = name

        self.quantity_str = quantity_str
        self.quantity = None
        try:
            for search, repl in UNIT_STRING_REPLACEMENTS:
                quantity_str = re.sub(search, repl, quantity_str)
            self.quantity = UNIT_REGISTRY.parse_expression(quantity_str)
        except:
            pass

    def compatibility_score(self, item: "AmazonItem"):
        """
        Return a float score characterizing the compatibility between this
        shopping list item and the given result. Scores should be comparable
        only within results for this shopping list item.
        """

        score = 0

        # Integer amount of the item we'd need to buy.
        need_n_of_item = 1

        print(self.quantity, item.quantity)
        if self.quantity is not None and item.quantity is not None:
            # Compute difference in quantity in terms of our units.
            quantity_diff = item.quantity - self.quantity
            if quantity_diff < 0:
                need_n_of_item = np.ceil(self.quantity / item.quantity)
                quantity_diff = item.quantity * need_n_of_item - self.quantity

            score -= quantity_diff.to_base_units().magnitude
        else:
            # Unknown quantity -- bring down the score a bit.
            score -= 1e-2

        # if item.quantity is not None:
        #     # Calculate item unit price in terms of base units.
        #     # TODO this may differ between items in the cart -- need to enforce
        #     # global consistency
        #     item_quantity = item.quantity.to_base_units()
        #     item_unit_price = item.price / item_quantity.magnitude
        #
        #     score -= item_unit_price

        score -= item.price * need_n_of_item

        return score



class AmazonItem(object):

    def __init__(self, name, asin: str, price, quantity: Quantity):
        self.name = name
        self.asin = asin
        self.price = price
        self.quantity = quantity

    def __repr__(self):
        return f"AmazonItem(\"{self.name}\", {self.asin}, {self.price}, {self.quantity})"

    __str__ = __repr__
