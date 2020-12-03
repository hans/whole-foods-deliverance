from collections import namedtuple


class ShoppingListItem(object):

    def __init__(self, name, amount_str):
        self.name = name
        self.amount_str = amount_str

    def get_amount(self, units):
        raise NotImplementedError()
