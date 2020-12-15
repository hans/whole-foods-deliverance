from copy import deepcopy
from typing import List

import numpy as np
from pint import Quantity

from .elements import FlyoutCartItem
from .utils import parse_units


class ShoppingListItem(object):

    def __init__(self, name, quantity_str: Quantity):
        self.name = name

        self.quantity_str = quantity_str
        self.quantity = parse_units(quantity_str)

    def compatibility_score(self, item: "AmazonItem"):
        """
        Return a float score characterizing the compatibility between this
        shopping list item and the given result. Scores should be comparable
        only within results for this shopping list item.
        """

        score = 0

        # Integer amount of the item we'd need to buy.
        need_n_of_item = 1

        print(self.name, self.quantity, '//', item.name, item.quantity)
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

    def __init__(self, name, asin: str, price, quantity: Quantity, multiples=1):
        self.name = name
        self.asin = asin
        self.price = price
        self.quantity = quantity
        self.multiples = multiples

    @classmethod
    def from_cart_item(cls, item: FlyoutCartItem):
        return cls(name=item.name, asin=item.product_id, price=item.price,
                   quantity=parse_units(item.name), multiples=item.quantity)

    def __repr__(self):
        multiple_str = f"{self.multiples} * " if self.multiples != 1 else ""
        return f"AmazonItem({multiple_str}\"{self.name}\", {self.asin}, {self.price}, {self.quantity})"

    __str__ = __repr__

    def __hash__(self):
        # NB Pint Quantity instanes are not hashable
        return hash((self.asin, repr(self.quantity), self.multiples))

    def __eq__(self, other):
        return isinstance(other, AmazonItem) and hash(self) == hash(other)


def diff_carts(c1: List[AmazonItem], c2: List[AmazonItem]) -> List[AmazonItem]:
    # # Convert to set representation with multiples as part of the element,
    # # so that we can catch increments of existing cart items
    # c1_set = set()
    new_items = set(c2) - set(c1)
    missing_items = set(c1) - set(c2)

    # TODO handle incremented quantities of existing items -- index each set by
    # ASIN and see if there are matches.

    return list(new_items)
