from .code_tables import list_0, list_0_for_atbash, list_A, list_a, list_hex
from .transposition import rev


def rot_a(c, k, type="encode"):
    if list_A.find(c) >= 0:
        table = list_A
    elif list_a.find(c) >= 0:
        table = list_a
    elif list_0.find(c) >= 0:
        table = list_0
    else:
        return c

    length = len(table)
    position = table.find(c)

    if type == "encode":
        target = (position + k) % length
    elif type == "decode":
        target = (position - k) % length
    elif type == "beaufort":
        target = (k - position) % length
    else:
        return c
    return table[target]


def vig_a(c, k, type):
    shift = list_A.find(k)
    if shift < 0:
        shift = list_a.find(k)
    if shift < 0:
        shift = list_0.find(k)
    if shift < 0:
        shift = 0
    return rot_a(c, shift, type)


def rot(c, k, nc=False):
    target = list_A + list_a + list_0 if nc else list_A + list_a
    result = ""

    for char in c:
        if char in target:
            result += rot_a(char, k)
        else:
            result += char
    return result


def vig_e(c, k, nc=False):
    target = list_A + list_a + list_0 if nc else list_A + list_a
    key_length = len(k)
    result = ""
    key_index = 0

    for char in c:
        if char in target:
            result += vig_a(char, k[key_index], "encode")
            key_index = (key_index + 1) % key_length
        else:
            result += char
    return result


def vig_d(c, k, nc=False):
    target = list_A + list_a + list_0 if nc else list_A + list_a
    key_length = len(k)
    result = ""
    key_index = 0

    for char in c:
        if char in target:
            result += vig_a(char, k[key_index], "decode")
            key_index = (key_index + 1) % key_length
        else:
            result += char
    return result


def beaufort(c, k, nc=False):
    target = list_A + list_a + list_0 if nc else list_A + list_a
    key_length = len(k)
    result = ""
    key_index = 0

    for char in c:
        if char in target:
            result += vig_a(char, k[key_index], "beaufort")
            key_index = (key_index + 1) % key_length
        else:
            result += char
    return result


def vig_e_auto(c, k, nc=False):
    target = list_A + list_a + list_0 if nc else list_A + list_a
    result = ""
    key_index = 0

    for char in c:
        if char in target:
            result += vig_a(char, k[key_index], "encode")
            k += char
            key_index += 1
        else:
            result += char
    return result


def vig_d_auto(c, k, nc=False):
    target = list_A + list_a + list_0 if nc else list_A + list_a
    result = ""
    key_index = 0

    for char in c:
        if char in target:
            decoded = vig_a(char, k[key_index], "decode")
            result += decoded
            k += decoded
            key_index += 1
        else:
            result += char
    return result


def atbash(c, nc=False):
    list_A_atbash = rev(list_A)
    list_a_atbash = list_A_atbash.lower()
    list_0_atbash = rev(list_0_for_atbash)
    tr_A = str.maketrans(list_A, list_A_atbash)
    tr_a = str.maketrans(list_a, list_a_atbash)
    tr_0 = str.maketrans(list_0_for_atbash, list_0_atbash)
    if nc:
        return c.translate(tr_A).translate(tr_a).translate(tr_0)
    return c.translate(tr_A).translate(tr_a)


def hexbash(c):
    c = c.lower()
    list_hex_atbash = rev(list_hex)
    tr_hex = str.maketrans(list_hex, list_hex_atbash)
    return c.translate(tr_hex)
