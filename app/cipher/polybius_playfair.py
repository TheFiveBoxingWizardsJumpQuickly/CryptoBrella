from .code_tables import polybius_table
from .common import mixed_alphabet


def playfair_a(c, mode, mx):
    if mode == "d":
        sft = -1
    else:
        sft = 1

    if mx == 6:
        key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    else:
        key = polybius_table
    c = c.upper()
    t0 = key.index(c[0])
    t1 = key.index(c[1])
    t0_r = int(t0 / mx)
    t0_c = t0 % mx
    t1_r = int(t1 / mx)
    t1_c = t1 % mx
    if t0_r == t1_r and t0_c == t1_c:
        s0 = ((t0_r + sft) % mx) * mx + ((t0_c + sft) % mx)
        s1 = ((t1_r + sft) % mx) * mx + ((t1_c + sft) % mx)
    elif t0_r == t1_r:
        s0 = t0_r * mx + ((t0_c + sft) % mx)
        s1 = t1_r * mx + ((t1_c + sft) % mx)
    elif t0_c == t1_c:
        s0 = ((t0_r + sft) % mx) * mx + t0_c
        s1 = ((t1_r + sft) % mx) * mx + t1_c
    else:
        s0 = t0_r * mx + t1_c
        s1 = t1_r * mx + t0_c

    return key[s0] + key[s1]


def playfair_e(c):
    c = c.upper().replace("J", "I")
    if len(c) % 2 == 1:
        c += "X"
    result = ""
    for i in range(0, len(c), 2):
        result += playfair_a(c[i : i + 2], "e", 5)
    return result


def playfair_d(c):
    c = c.upper().replace("J", "I")
    if len(c) % 2 == 1:
        c += "X"
    result = ""
    for i in range(0, len(c), 2):
        result += playfair_a(c[i : i + 2], "d", 5)
    return result


def playfair_e6(c):
    c = c.upper()
    if len(c) % 2 == 1:
        c += "X"
    result = ""
    for i in range(0, len(c), 2):
        result += playfair_a(c[i : i + 2], "e", 6)
    return result


def playfair_d6(c):
    c = c.upper()
    if len(c) % 2 == 1:
        c += "X"
    result = ""
    for i in range(0, len(c), 2):
        result += playfair_a(c[i : i + 2], "d", 6)
    return result


def polybius_e(text, table_keyword=""):
    table = mixed_alphabet(table_keyword, True)
    text = text.upper().replace("J", "I")
    coordinates = []
    for i in range(len(text)):
        index = table.index(text[i])
        coordinates.append(str(int(index / 5) + 1))
        coordinates.append(str((index % 5) + 1))
    return "".join(coordinates)


def polybius_d(text, table_keyword=""):
    table = mixed_alphabet(table_keyword, True)
    remain = ""
    if len(text) % 2 == 1:
        remain = "[" + text[-1] + "]"
        text = text[0:-1]
    result = [table[(int(text[i]) - 1) * 5 + (int(text[i + 1]) - 1)] for i in range(0, len(text), 2)]
    return "".join(result) + remain


def bifid_e(text, table_keyword=""):
    table = mixed_alphabet(table_keyword, True)
    text = text.upper().replace("J", "I")
    coordinates = [[0, 0] for _ in range(len(text))]
    for i in range(len(text)):
        index = table.index(text[i])
        coordinates[i] = [int(index / 5), index % 5]

    transposed_coordinates = [0] * len(text) * 2
    for i in range(len(text)):
        transposed_coordinates[i] = coordinates[i][0]
        transposed_coordinates[i + len(text)] = coordinates[i][1]

    result = ""
    for i in range(len(text)):
        result += table[transposed_coordinates[2 * i] * 5 + transposed_coordinates[2 * i + 1]]

    return result


def bifid_d(text, table_keyword=""):
    table = mixed_alphabet(table_keyword, True)
    text = text.upper().replace("J", "I")

    transposed_coordinates = [0] * len(text) * 2
    for i in range(len(text)):
        index = table.index(text[i])
        transposed_coordinates[2 * i] = int(index / 5)
        transposed_coordinates[2 * i + 1] = index % 5

    coordinates = [[0, 0] for _ in range(len(text))]
    for i in range(len(text)):
        coordinates[i] = [transposed_coordinates[i], transposed_coordinates[i + len(text)]]

    result = ""
    for i in range(len(text)):
        result += table[coordinates[i][0] * 5 + coordinates[i][1]]

    return result
