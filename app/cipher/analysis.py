import re

from .code_tables import list_a
from .common import unique, unique_list


def phonetic_alphabet_e(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j.upper())
    return text


def phonetic_alphabet_d(text, dic):
    dic_swap = {v: k for k, v in dic.items()}
    for i, j in dic_swap.items():
        text = text.replace(i, j.upper())
    return text


def return_phonetic_alphabet_values(dic):
    text = "Code table = ["
    for i in list_a:
        text += dic[i] + " "

    text = text[:-1] + "]"
    return text


def letter_frequency(text, sortkey=0, reverse_flag=False):
    unique_text = unique(text)
    freq = []
    for letter in unique_text:
        freq.append([letter, text.count(letter)])
    return sorted(freq, key=lambda x: x[sortkey], reverse=reverse_flag)


def bigram_frequency(text):
    freq = []
    bigram = []
    for i in range(len(text) - 1):
        if " " not in text[i : i + 2]:
            bigram.append(text[i : i + 2])

    unique_bigram = unique_list(bigram)
    for b in unique_bigram:
        freq.append([b, bigram.count(b)])
    return sorted(freq, key=lambda x: x[1], reverse=True)


def trigram_frequency(text):
    freq = []
    trigram = []
    for i in range(len(text) - 1):
        if " " not in text[i : i + 3]:
            trigram.append(text[i : i + 3])

    unique_trigram = unique_list(trigram)
    for b in unique_trigram:
        freq.append([b, trigram.count(b)])
    return sorted(freq, key=lambda x: x[1], reverse=True)


def ngram_distance(text, ngram):
    if text == "" or ngram == "":
        return []
    iter = re.finditer(ngram, text)
    start_point_list = []
    for i in iter:
        start_point_list.append(i.span()[0])
    if len(start_point_list) == 0:
        return []

    distance = []
    for i in range(len(start_point_list) - 1):
        distance.append(len(text[start_point_list[i] : start_point_list[i + 1]].replace(" ", "")))

    unique_distance = unique_list(distance)
    freq = []
    for d in unique_distance:
        freq.append([d, distance.count(d)])
    return sorted(freq, key=lambda x: x[1], reverse=True)
