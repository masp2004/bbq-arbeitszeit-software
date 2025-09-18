# ------------------------------
# PEP 8 Cheatsheet – Basics
# ------------------------------

# ✅ Zeilenlänge: Bitte Zeilenumbrüche bei langen Auflistungen.
#    (Offizielle Vorgabe sind 79 Zeichen/Zeile)
long_list = [
    "eins", "zwei", "drei", "vier", "fünf",
    "sechs", "sieben", "acht", "neun", "zehn",
]

# ✅ Leerzeilen: 2 zwischen Funktionen/Klassen, 1 innerhalb von Klassen
def add(a, b):
    '''Return the sum of a and b.'''  # Docstring immer im Präsens
    return a + b


class RepairModel:
    '''Model for predicting repairs based on sales and history.'''

    def __init__(self, data):
        self.data = data  # Variablen im snake_case

    def predict(self):
        '''Return a prediction based on the given data.'''
        return len(self.data)


# ✅ Imports: Standardbibliothek, dann Third-Party, dann lokale Module
import os
import sys

import numpy as np
import pandas as pd

from myproject import mymodule


# ✅ Namenskonventionen
variable_name = 42       # snake_case für Variablen/Funktionen
CONSTANT_NAME = 3.14     # SCREAMING_SNAKE_CASE für Konstanten


class MyClass:           # PascalCase für Klassen
    pass



import datetime


def _shift(start, end, break_time=0):
    return {
        "start": start,
        "end": end,
        "break": break_time,
    }


def test_smoke():
    assert True


def test_shift():
    s = _shift(
        datetime.datetime(2023, 1, 1, 9, 0, 0),
        datetime.datetime(2023, 1, 1, 17, 0, 0),
        break_time=30,
    )
    assert s["start"] == datetime.datetime(2023, 1, 1, 9, 0, 0)
    assert s["end"] == datetime.datetime(2023, 1, 1, 17, 0, 0)
    assert s["break"] == 30


def test_long_assert():
    """Dummy assertion split across lines and staying <79 chars."""
    assert (
        sum([1, 2, 3, 4, 5, 6, 7, 8])
        == 36
    )
