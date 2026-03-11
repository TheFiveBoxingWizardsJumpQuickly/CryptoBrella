import re


def auto_split_number_string(text, pattern):
    text = text.upper()
    if pattern == "DEC":
        split_numbers = re.findall(r"3[2-9]|[4-9][0-9]|1[0-1][0-9]|12[0-2]", text)
    elif pattern == "HEX":
        split_numbers = re.findall(r"[2-6][0-9A-F]|7[0-9A]", text)
    elif pattern == "OCT":
        split_numbers = re.findall(r"[4-7][0-7]|1[0-6][0-7]|17[0-2]", text)
    elif pattern == "BIN":
        split_numbers = re.findall(r"001[0-1]{5}|010[0-1]{5}|0110[0-1]{4}|01110[0-1]{3}|01111000|01111001|01111010", text)
    elif pattern == "vanity_toggle":
        split_numbers = re.findall(r"2{1,3}|3{1,3}|4{1,3}|5{1,3}|6{1,3}|7{1,4}|8{1,3}|9{1,4}", text)
    elif pattern == "vanity_rept_number":
        split_numbers = re.findall(r"[1-3][2-9]|4[7,9]", text)
    elif pattern == "vanity_number_rept":
        split_numbers = re.findall(r"[2-9][1-3]|[7,9]4", text)

    return [number for number in split_numbers]


def vanity_e(text, style):
    text = text.upper()
    dict_toggle = {"A": "2", "B": "22", "C": "222", "D": "3", "E": "33", "F": "333", "G": "4", "H": "44", "I": "444", "J": "5", "K": "55", "L": "555", "M": "6",
                   "N": "66", "O": "666", "P": "7", "Q": "77", "R": "777", "S": "7777", "T": "8", "U": "88", "V": "888", "W": "9", "X": "99", "Y": "999", "Z": "9999"}
    dict_rept_number = {"A": "12", "B": "22", "C": "32", "D": "13", "E": "23", "F": "33", "G": "14", "H": "24", "I": "34", "J": "15", "K": "25", "L": "35",
                        "M": "16", "N": "26", "O": "36", "P": "17", "Q": "27", "R": "37", "S": "47", "T": "18", "U": "28", "V": "38", "W": "19", "X": "29", "Y": "39", "Z": "49"}
    dict_number_rept = {"A": "21", "B": "22", "C": "23", "D": "31", "E": "32", "F": "33", "G": "41", "H": "42", "I": "43", "J": "51", "K": "52", "L": "53",
                        "M": "61", "N": "62", "O": "63", "P": "71", "Q": "72", "R": "73", "S": "74", "T": "81", "U": "82", "V": "83", "W": "91", "X": "92", "Y": "93", "Z": "94"}

    if style == "toggle":
        dict_style = dict_toggle
    elif style == "rept_number":
        dict_style = dict_rept_number
    elif style == "number_rept":
        dict_style = dict_number_rept
    translator = str.maketrans(dict_style)

    return " ".join([s.translate(translator) for s in text])


def vanity_d(text, style):
    dict_toggle = {"A": "2", "B": "22", "C": "222", "D": "3", "E": "33", "F": "333", "G": "4", "H": "44", "I": "444", "J": "5", "K": "55", "L": "555", "M": "6",
                   "N": "66", "O": "666", "P": "7", "Q": "77", "R": "777", "S": "7777", "T": "8", "U": "88", "V": "888", "W": "9", "X": "99", "Y": "999", "Z": "9999"}
    dict_rept_number = {"A": "12", "B": "22", "C": "32", "D": "13", "E": "23", "F": "33", "G": "14", "H": "24", "I": "34", "J": "15", "K": "25", "L": "35",
                        "M": "16", "N": "26", "O": "36", "P": "17", "Q": "27", "R": "37", "S": "47", "T": "18", "U": "28", "V": "38", "W": "19", "X": "29", "Y": "39", "Z": "49"}
    dict_number_rept = {"A": "21", "B": "22", "C": "23", "D": "31", "E": "32", "F": "33", "G": "41", "H": "42", "I": "43", "J": "51", "K": "52", "L": "53",
                        "M": "61", "N": "62", "O": "63", "P": "71", "Q": "72", "R": "73", "S": "74", "T": "81", "U": "82", "V": "83", "W": "91", "X": "92", "Y": "93", "Z": "94"}

    if style == "toggle":
        dict_style = {v: k for k, v in dict_toggle.items()}
        text_split = auto_split_number_string(text, "vanity_toggle")
    elif style == "rept_number":
        dict_style = {v: k for k, v in dict_rept_number.items()}
        text_split = auto_split_number_string(text, "vanity_rept_number")
    elif style == "number_rept":
        dict_style = {v: k for k, v in dict_number_rept.items()}
        text_split = auto_split_number_string(text, "vanity_number_rept")

    return "".join([dict_style[s] for s in text_split])
