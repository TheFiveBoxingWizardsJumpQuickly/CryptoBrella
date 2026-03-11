from .code_tables import list_0, list_A, list_a
from .math_functions import xgcd


def affine_e_a(text, a, b, nc=False):
    if list_A.find(text) >= 0:
        table = list_A
    elif list_a.find(text) >= 0:
        table = list_a
    elif list_0.find(text) >= 0 and nc:
        table = list_0
    else:
        return text

    length = len(table)
    position = table.find(text)
    converted = (position * a + b) % length
    return "".join(table[converted])


def affine_d_a(text, a, b, nc=False):
    if list_A.find(text) >= 0:
        table = list_A
    elif list_a.find(text) >= 0:
        table = list_a
    elif list_0.find(text) >= 0 and nc:
        table = list_0
    else:
        return text

    length = len(table)

    if a == 0:
        x = 0
    else:
        g, x, _ = xgcd(a, length)
        if g != 1:
            return "#"

    position = table.find(text)
    converted = (position * x - b * x) % length
    return "".join(table[converted])


def affine_e(text, a, b):
    converted = ""
    for char in text:
        converted += affine_e_a(char, a, b)
    return converted


def affine_d(text, a, b):
    converted = ""
    for char in text:
        converted += affine_d_a(char, a, b)
    return converted
