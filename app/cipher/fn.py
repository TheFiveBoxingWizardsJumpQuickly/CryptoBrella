import base64
import binascii
import hashlib
import what3words

from .transposition import *
from .common import *
from .code_tables import *
from .base_conversion import *
from .math_functions import *
from .enigma import enigma, plugboard_gen
from .purple import purple_decode, purple_encode
from .kakushi import kakushi_encode, kakushi_decode
from .misc import *


def adfgx_e(text, table_keyword, transposition_keyword):
    table = mixed_alphabet(table_keyword, True)
    letter_set = "ADFGX"
    trimmed_text = text.replace(" ", "").upper().replace("J", "I")

    fractionated = ""
    for s in trimmed_text:
        index = table.index(s)
        row_num = int(index/5)
        col_num = index % 5
        fractionated += letter_set[row_num]
        fractionated += letter_set[col_num]

    return "".join(columnar_e(fractionated, assign_digits(transposition_keyword)))


def adfgx_d(text, table_keyword, transposition_keyword):
    fractionated = columnar_d(text, assign_digits(transposition_keyword))

    table = mixed_alphabet(table_keyword, True)
    letter_set = "ADFGX"

    plain_text = ""
    for i, s in enumerate(fractionated):
        if i % 2 == 0:
            row_num = letter_set.index(s)
        else:
            col_num = letter_set.index(s)
            plain_text += table[row_num*5 + col_num]

    return "".join(plain_text)


def adfgvx_e(text, table_keyword, transposition_keyword):
    table = mixed_alphanumeric(table_keyword)
    letter_set = "ADFGVX"
    trimmed_text = text.replace(" ", "").upper()

    fractionated = ""
    for s in trimmed_text:
        index = table.index(s)
        row_num = int(index/6)
        col_num = index % 6
        fractionated += letter_set[row_num]
        fractionated += letter_set[col_num]

    return "".join(columnar_e(fractionated, assign_digits(transposition_keyword)))


def adfgvx_d(text, table_keyword, transposition_keyword):
    fractionated = columnar_d(text, assign_digits(transposition_keyword))

    table = mixed_alphanumeric(table_keyword)
    letter_set = "ADFGVX"

    plain_text = ""
    for i, s in enumerate(fractionated):
        if i % 2 == 0:
            row_num = letter_set.index(s)
        else:
            col_num = letter_set.index(s)
            plain_text += table[row_num*6 + col_num]

    return "".join(plain_text)


def rot_a(c, k, type="encode"):
    if list_A.find(c) >= 0:
        list = list_A
    elif list_a.find(c) >= 0:
        list = list_a
    elif list_0.find(c) >= 0:
        list = list_0
    else:
        return c

    l = len(list)
    position = list.find(c)

    if type == "encode":
        p = (position + k) % l
    elif type == "decode":
        p = (position - k) % l
    elif type == "beaufort":
        p = (k - position) % l
    else:
        p = c
    return list[p]


def vig_a(c, k, type):
    t = list_A.find(k)
    if t < 0:
        t = list_a.find(k)
    if t < 0:
        t = list_0.find(k)
    if t < 0:
        t = 0
    return rot_a(c, t, type)


def rot(c, k, nc=False):
    l = len(c)
    p = ""
    if nc:
        target = list_A + list_a + list_0
    else:
        target = list_A + list_a

    for i in range(l):
        if c[i] in target:
            p += rot_a(c[i], k)
        else:
            p += c[i]
    return p


def vig_e(c, k, nc=False):
    l_c = len(c)
    l_k = len(k)
    p = ""
    if nc:
        target = list_A + list_a + list_0
    else:
        target = list_A + list_a

    j = 0
    for i in range(l_c):
        if c[i] in target:
            p += vig_a(c[i], k[j], "encode")
            j = (j + 1) % l_k
        else:
            p += c[i]
    return p


def vig_d(c, k, nc=False):
    l_c = len(c)
    l_k = len(k)
    p = ""
    if nc:
        target = list_A + list_a + list_0
    else:
        target = list_A + list_a

    j = 0
    for i in range(l_c):
        if c[i] in target:
            p += vig_a(c[i], k[j], "decode")
            j = (j + 1) % l_k
        else:
            p += c[i]
    return p


def beaufort(c, k, nc=False):
    l_c = len(c)
    l_k = len(k)
    p = ""
    if nc:
        target = list_A + list_a + list_0
    else:
        target = list_A + list_a

    j = 0
    for i in range(l_c):
        if c[i] in target:
            p += vig_a(c[i], k[j], "beaufort")
            j = (j + 1) % l_k
        else:
            p += c[i]
    return p


def vig_e_auto(c, k, nc=False):
    l_c = len(c)
    p = ""
    if nc:
        target = list_A + list_a + list_0
    else:
        target = list_A + list_a
    j = 0
    for i in range(l_c):
        if c[i] in target:
            p += vig_a(c[i], k[j], "encode")
            k += c[i]
            j = j + 1
        else:
            p += c[i]
    return p


def vig_d_auto(c, k, nc=False):
    l_c = len(c)
    p = ""
    if nc:
        target = list_A + list_a + list_0
    else:
        target = list_A + list_a
    j = 0
    for i in range(l_c):
        if c[i] in target:
            p += vig_a(c[i], k[j], "decode")
            k += vig_a(c[i], k[j], "decode")
            j = j + 1
        else:
            p += c[i]
    return p


def kw(regexp):
    import csv
    import re
    kw = open("kw.txt")
    list_all = []
    for row in csv.reader(kw):
        list_all.append(row[0])
    list = [w for w in list_all if re.match(regexp, w)]
    return(list)


def atbash(c, nc=False):
    list_A_atbash = rev(list_A)
    list_a_atbash = list_A_atbash.lower()
    list_0_atbash = rev(list_0_for_atbash)
    tr_A = str.maketrans(list_A, list_A_atbash)
    tr_a = str.maketrans(list_a, list_a_atbash)
    tr_0 = str.maketrans(list_0_for_atbash, list_0_atbash)
    if nc:
        return(c.translate(tr_A).translate(tr_a).translate(tr_0))
    else:
        return(c.translate(tr_A).translate(tr_a))


def hexbash(c):
    c = c.lower()
    list_hex_atbash = rev(list_hex)
    tr_hex = str.maketrans(list_hex, list_hex_atbash)
    return(c.translate(tr_hex))


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
    t0_r = int(t0/mx)
    t0_c = t0 % mx
    t1_r = int(t1/mx)
    t1_c = t1 % mx
    if t0_r == t1_r and t0_c == t1_c:
        # 同じ文字が連続したときの挙動はrumkinに合わせる。Nianticもそうしていたので・・
        s0 = ((t0_r+sft) % mx)*mx+((t0_c+sft) % mx)
        s1 = ((t1_r+sft) % mx)*mx+((t1_c+sft) % mx)
    elif t0_r == t1_r:
        s0 = t0_r*mx+((t0_c+sft) % mx)
        s1 = t1_r*mx+((t1_c+sft) % mx)
    elif t0_c == t1_c:
        s0 = ((t0_r+sft) % mx)*mx + t0_c
        s1 = ((t1_r+sft) % mx)*mx + t1_c
    else:
        s0 = t0_r*mx+t1_c
        s1 = t1_r*mx+t0_c

    p = key[s0]+key[s1]
    return p


def playfair_e(c):
    c = c.upper().replace("J", "I")
    if len(c) % 2 == 1:
        c += "X"
    p = ""
    for i in range(0, len(c), 2):
        p += playfair_a(c[i:i+2], "e", 5)

    return p


def playfair_d(c):
    c = c.upper().replace("J", "I")
    if len(c) % 2 == 1:
        c += "X"
    p = ""
    for i in range(0, len(c), 2):
        p += playfair_a(c[i:i+2], "d", 5)

    return p


def playfair_e6(c):
    c = c.upper()
    if len(c) % 2 == 1:
        c += "X"
    p = ""
    for i in range(0, len(c), 2):
        p += playfair_a(c[i:i+2], "e", 6)

    return p


def playfair_d6(c):
    c = c.upper()
    if len(c) % 2 == 1:
        c += "X"
    p = ""
    for i in range(0, len(c), 2):
        p += playfair_a(c[i:i+2], "d", 6)

    return p


def polybius_e(text, table_keyword=""):
    table = mixed_alphabet(table_keyword, True)
    text = text.upper().replace("J", "I")
    coordinates = []
    for i in range(len(text)):
        index = table.index(text[i])
        coordinates.append(str(int(index/5)+1))
        coordinates.append(str((index % 5)+1))
    return "".join(coordinates)


def polybius_d(text, table_keyword=""):
    table = mixed_alphabet(table_keyword, True)
    remain = ""
    if len(text) % 2 == 1:
        remain = "[" + text[-1] + "]"
        text = text[0:-1]
    result = [table[(int(text[i])-1)*5 + (int(text[i+1])-1)]
              for i in range(0, len(text), 2)]
    return "".join(result) + remain


def bifid_e(text, table_keyword=""):
    table = mixed_alphabet(table_keyword, True)
    text = text.upper().replace("J", "I")
    coordinates = [[0, 0] for i in range(len(text))]
    for i in range(len(text)):
        index = table.index(text[i])
        coordinates[i] = [int(index/5), index % 5]

    transposed_coordinates = [0]*len(text)*2
    for i in range(len(text)):
        transposed_coordinates[i] = coordinates[i][0]
        transposed_coordinates[i+len(text)] = coordinates[i][1]

    result = ""
    for i in range(len(text)):
        result += table[transposed_coordinates[2*i]
                        * 5+transposed_coordinates[2*i+1]]

    return result


def bifid_d(text, table_keyword=""):
    table = mixed_alphabet(table_keyword, True)
    text = text.upper().replace("J", "I")

    transposed_coordinates = [0]*len(text)*2
    for i in range(len(text)):
        index = table.index(text[i])
        transposed_coordinates[2*i] = int(index/5)
        transposed_coordinates[2*i + 1] = index % 5

    coordinates = [[0, 0] for i in range(len(text))]
    for i in range(len(text)):
        coordinates[i] = [transposed_coordinates[i],
                          transposed_coordinates[i + len(text)]]

    result = ""
    for i in range(len(text)):
        result += table[coordinates[i][0]*5+coordinates[i][1]]

    return result


def morse_e(text, bin_code=False, delimiter=" "):
    text = text.upper()
    return code_table_e(text, morse_code_table, {"-": "0", ".": "1"}, bin_code, delimiter)


def morse_d(text, bin_code=False, delimiter=" "):
    return code_table_d(text, morse_code_table, {"-": "0", ".": "1"}, bin_code, delimiter)


def morse_wabun_e(text, bin_code=False, delimiter=" "):
    text = hiragana_to_katakana(text)
    text = split_dakuten(text)
    return code_table_e(text, morse_wabun_code_table, {"-": "0", ".": "1"}, bin_code, delimiter)


def morse_wabun_d(text, bin_code=False, delimiter=" "):
    return code_table_d(text, morse_wabun_code_table, {"-": "0", ".": "1"}, bin_code, delimiter)


def bacon1_e(text, bin_code=False, delimiter=" "):
    text = text.upper()
    return code_table_e(text, bacon1_table, {"a": "0", "b": "1"}, bin_code, delimiter)


def bacon1_d(text, bin_code=False, delimiter=" "):
    return code_table_d(text, bacon1_table, {"a": "0", "b": "1"}, bin_code, delimiter)


def bacon2_e(text, bin_code=False, delimiter=" "):
    text = text.upper()
    return code_table_e(text, bacon1_table, {"a": "0", "b": "1"}, bin_code, delimiter)


def bacon2_d(text, bin_code=False, delimiter=" "):
    return code_table_d(text, bacon1_table, {"a": "0", "b": "1"}, bin_code, delimiter)


def chemical_symbol_convert(text, mode, delimiter=" "):
    if mode == '0':
        # Atomic number to sympol
        return code_table_e(text, chemical_symbol, {}, False, delimiter)
    elif mode == '1':
        # Symbol to atomic number
        return code_table_d(text, chemical_symbol, {}, False, delimiter)


def abc012(text, delimiter=" "):
    text = text.upper()
    return code_table_e(text, abc012_table, {}, False, delimiter)


def affine_e_a(text, a, b, nc=False):
    if list_A.find(text) >= 0:
        list = list_A
    elif list_a.find(text) >= 0:
        list = list_a
    elif list_0.find(text) >= 0 and nc:
        list = list_0
    else:
        return text

    l = len(list)
    position = list.find(text)
    converted = (position*a + b) % l
    return "".join(list[converted])


def affine_d_a(text, a, b, nc=False):
    if list_A.find(text) >= 0:
        list = list_A
    elif list_a.find(text) >= 0:
        list = list_a
    elif list_0.find(text) >= 0 and nc:
        list = list_0
    else:
        return text

    l = len(list)

    if a == 0:
        x = 0
    else:
        g, x, y = xgcd(a, l)
        if g != 1:
            return '#'

    position = list.find(text)
    converted = (position*x - b*x) % l
    return "".join(list[converted])


def affine_e(text, a, b):
    l = len(text)
    converted = ""
    for i in range(l):
        converted += affine_e_a(text[i], a, b)
    return converted


def affine_d(text, a, b):
    l = len(text)
    converted = ""
    for i in range(l):
        converted += affine_d_a(text[i], a, b)
    return converted


def text_split(text, step, sep=' '):
    result = ''
    for i in range(0, len(text), step):
        result += text[i:i+step] + sep
    result = result[:-1]
    return result


def table_subtitution(text, method):
    if method == 'A-a swap':
        t1 = list_A + list_a
        t2 = list_a + list_A
    elif method == 'Morse .- swap':
        t1 = '1234567890abcdefghijklmnopqrstuvwxyz' + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        t2 = '6789012345nj?wtqu?mbryiasxfkoeg?dpl?' + 'NJ?WTQU?MBRYIASXFKOEG?DPL?'
    elif method == 'Morse reverse':
        t1 = '1234567890abcdefghijklmnopqrstuvwxyz' + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        t2 = '9876543210nv?uelwhi?kfmaopyrstdbgxq?' + 'NV?UELWHI?KFMAOPYRSTDBGXQ?'
    elif method == 'Morse .- swap and reverse':
        t1 = '1234567890abcdefghijklmnopqrstuvwxyz' + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        t2 = '4321098765a?cgtyd?mvrqinsxlkoewjupfz' + 'A?CGTYD?MVRQINSXLKOEWJUPFZ'
    elif method == 'US keyboard left shift':
        t1 = r'1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+'
        t2 = r'`123456789?vxswdfguhjknbio?earycqzt?0-p[]lm,.??VXSWDFGUHJKNBIO?EARYCQZT??~!@#$%^&*()_'
    elif method == 'US keyboard right shift':
        t1 = r'1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+'
        t2 = r"234567890-snvfrghjokl;,mp[wtdyibecux=?]\?'./?1SNVFRGHJOKL;,MP[WTDYIBECUX!@#$%^&*()_+?"
    elif method == 'US keyboard right <-> left':
        t1 = r'1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+'
        t2 = r"0987654321;n,kijhgefdsvbwqpulyrmo.t/`????acxz-;N,KIJHGEFDSVBWQPULYRMO.T/_)(*&^%$#@!~?"
    elif method == 'US keyboard up <-> down':
        t1 = r'1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+'
        t2 = r"zxcvbnm,..q53edrtykuio76l;afwgj4s2h1?????p*()?Q%#EDRTYKUIO&^L;AFWGJ$S@H!?ZXCVBNM<>???"
    elif method == 'US keyboard to Dvorak keyboard':
        t1 = '1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        t2 = "1234567890axje.uidchtnmbrl'poygk,qf;[]/=\swvz`AXJE.UIDCHTNMBRL'POYGK,QF;"
    elif method == 'Dvorak keyboard to US keyboard':
        t1 = '1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        t2 = "1234567890anihdyujgcvpmlsrxo;kf.,bt/']-=\zwe[`ANIHDYUJGCVPMLSRXO;KF.,BT/"
    elif method == 'US keyboard to MALTRON keyboard':
        t1 = '1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        t2 = "1234567890a,jiysfduthow>zlqcnbmgp>v<?????rk-x?A,JIYSFDUTHOW>ZLQCNBMGP>V<"
    elif method == 'MALTRON keyboard to US keyboard':
        t1 = '1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        t2 = "1234567890atrh?gvkdc,puslwq;fjiym/eo>?????????ATRH?GVKDC,PUSLWQ;FJIYM/EO"
    elif method == 'Atbash':
        t1 = list_A + list_a
        t2 = rev(list_A) + rev(list_a)
    elif method == '!@#_to_123':
        t1 = r'!@#$%^&*()'
        t2 = '1234567890'
    elif method == 'ABC to 123':
        t1 = list_A + list_a
        t2 = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26',
              '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26']
    elif method == 'ABC to 012':
        t1 = list_A + list_a
        t2 = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25',
              '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25']

    return replace_all(text, t1, t2)


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
    text = 'Code table = ['
    for i in list_a:
        text += dic[i] + ' '

    text = text[:-1] + ']'
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
    for i in range(len(text)-1):
        if not ' ' in text[i:i+2]:
            bigram.append(text[i:i+2])

    unique_bigram = unique_list(bigram)
    for b in unique_bigram:
        freq.append([b, bigram.count(b)])
    return sorted(freq, key=lambda x: x[1], reverse=True)


def trigram_frequency(text):
    freq = []
    trigram = []
    for i in range(len(text)-1):
        if not ' ' in text[i:i+3]:
            trigram.append(text[i:i+3])

    unique_trigram = unique_list(trigram)
    for b in unique_trigram:
        freq.append([b, trigram.count(b)])
    return sorted(freq, key=lambda x: x[1], reverse=True)


def ngram_distance(text, ngram):
    import re
    if text == '' or ngram == '':
        return []
    ngram_length = len(ngram)
    iter = re.finditer(ngram, text)
    start_point_list = []
    for i in iter:
        start_point_list.append(i.span()[0])
    if len(start_point_list) == 0:
        return []

    distance = []
    for i in range(len(start_point_list)-1):
        distance.append(
            len(text[start_point_list[i]:start_point_list[i+1]].replace(' ', '')))

    unique_distance = unique_list(distance)
    freq = []
    for d in unique_distance:
        freq.append([d, distance.count(d)])
    return sorted(freq, key=lambda x: x[1], reverse=True)


def uu_encode(byte):
    result = ''.encode()
    for s in range(0, len(byte), 45):
        result += binascii.b2a_uu(byte[s:s+45])[:-1]
    return result


def uu_decode(text):
    result = ''.encode()
    for s in range(0, len(text), 60):
        result += binascii.a2b_uu(text[s:s+60])
    return result


def hiragana_to_katakana(text):
    hiragana = 'ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをんゔゕゖ'
    katakana = 'ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶ'
    return replace_all(text=text, table_from=hiragana, table_to=katakana)


def split_dakuten(text):
    dict = {
        'ガ': 'カ゛', 'ギ': 'キ゛', 'グ': 'ク゛', 'ゲ': 'ケ゛', 'ゴ': 'コ゛',
        'ザ': 'サ゛', 'ジ': 'シ゛', 'ズ': 'ス゛', 'ゼ': 'セ゛', 'ゾ': 'ソ゛',
        'ダ': 'タ゛', 'ヂ': 'チ゛', 'ヅ': 'ツ゛', 'デ': 'テ゛', 'ド': 'ト゛',
        'バ': 'ハ゛', 'ビ': 'ヒ゛', 'ブ': 'フ゛', 'ベ': 'ヘ゛', 'ボ': 'ホ゛',
        'パ': 'ハ゜', 'ピ': 'ヒ゜', 'プ': 'フ゜', 'ペ': 'ヘ゜', 'ポ': 'ホ゜',
    }
    return text.translate(str.maketrans(dict))


def convert_to_3wa(apikey, latitude, longitude, language):
    geocoder = what3words.Geocoder(apikey)
    res = geocoder.convert_to_3wa(what3words.Coordinates(
        latitude, longitude), language=language)
    return res


def convert_to_coordinates(apikey, words):
    words = str(words).strip().replace(' ', '.').replace(
        ',', '.').replace('・', '.').replace('。', '.').replace('、', '.').replace('　', '.')
    pattern = re.compile(r'^[^\.]+\.[^\.]+\.[^\.]+$')
    if pattern.search(words):
        geocoder = what3words.Geocoder(apikey)
        res = geocoder.convert_to_coordinates(words)
        return res
    else:
        return {'format error': words + ' is not W3W format.'}


def braille_d(braille_dots):
    ascii_hex = braille_table[braille_dots]
    return chr(int(ascii_hex, 16))


def braille_ja_d(braille_dots):
    return braille_ja_table.get(braille_dots, '')


def auto_split_number_string(text, pattern):
    text = text.upper()
    if pattern == 'DEC':
        # 32-122
        split_numbers = re.findall(
            r'3[2-9]|[4-9][0-9]|1[0-1][0-9]|12[0-2]', text)
    elif pattern == 'HEX':
        # 20-7A
        split_numbers = re.findall(
            r'[2-6][0-9A-F]|7[0-9A]', text)
    elif pattern == 'OCT':
        # 40-172
        split_numbers = re.findall(
            r'[4-7][0-7]|1[0-6][0-7]|17[0-2]', text)
    elif pattern == 'BIN':
        # 00100000-01111010
        split_numbers = re.findall(
            r'001[0-1]{5}|010[0-1]{5}|0110[0-1]{4}|01110[0-1]{3}|01111000|01111001|01111010', text)
    elif pattern == 'vanity_toggle':
        split_numbers = re.findall(
            r'2{1,3}|3{1,3}|4{1,3}|5{1,3}|6{1,3}|7{1,4}|8{1,3}|9{1,4}', text)
    elif pattern == 'vanity_rept_number':
        split_numbers = re.findall(
            r'[1-3][2-9]|4[7,9]', text)
    elif pattern == 'vanity_number_rept':
        split_numbers = re.findall(
            r'[2-9][1-3]|[7,9]4', text)

    return [number for number in split_numbers]


def vanity_e(text, style):
    text = text.upper()
    result = ''
    dict_toggle = {'A': '2', 'B': '22', 'C': '222', 'D': '3', 'E': '33', 'F': '333', 'G': '4', 'H': '44', 'I': '444', 'J': '5', 'K': '55', 'L': '555', 'M': '6',
                   'N': '66', 'O': '666', 'P': '7', 'Q': '77', 'R': '777', 'S': '7777', 'T': '8', 'U': '88', 'V': '888', 'W': '9', 'X': '99', 'Y': '999', 'Z': '9999', }
    dict_rept_number = {'A': '12', 'B': '22', 'C': '32', 'D': '13', 'E': '23', 'F': '33', 'G': '14', 'H': '24', 'I': '34', 'J': '15', 'K': '25', 'L': '35',
                        'M': '16', 'N': '26', 'O': '36', 'P': '17', 'Q': '27', 'R': '37', 'S': '47', 'T': '18', 'U': '28', 'V': '38', 'W': '19', 'X': '29', 'Y': '39', 'Z': '49', }
    dict_number_rept = {'A': '21', 'B': '22', 'C': '23', 'D': '31', 'E': '32', 'F': '33', 'G': '41', 'H': '42', 'I': '43', 'J': '51', 'K': '52', 'L': '53',
                        'M': '61', 'N': '62', 'O': '63', 'P': '71', 'Q': '72', 'R': '73', 'S': '74', 'T': '81', 'U': '82', 'V': '83', 'W': '91', 'X': '92', 'Y': '93', 'Z': '94', }

    if style == 'toggle':
        dict_style = dict_toggle
    elif style == 'rept_number':
        dict_style = dict_rept_number
    elif style == 'number_rept':
        dict_style = dict_number_rept
    translator = str.maketrans(dict_style)

    result = ' '.join([s.translate(translator) for s in text])

    return result


def vanity_d(text, style):
    result = ''
    dict_toggle = {'A': '2', 'B': '22', 'C': '222', 'D': '3', 'E': '33', 'F': '333', 'G': '4', 'H': '44', 'I': '444', 'J': '5', 'K': '55', 'L': '555', 'M': '6',
                   'N': '66', 'O': '666', 'P': '7', 'Q': '77', 'R': '777', 'S': '7777', 'T': '8', 'U': '88', 'V': '888', 'W': '9', 'X': '99', 'Y': '999', 'Z': '9999', }
    dict_rept_number = {'A': '12', 'B': '22', 'C': '32', 'D': '13', 'E': '23', 'F': '33', 'G': '14', 'H': '24', 'I': '34', 'J': '15', 'K': '25', 'L': '35',
                        'M': '16', 'N': '26', 'O': '36', 'P': '17', 'Q': '27', 'R': '37', 'S': '47', 'T': '18', 'U': '28', 'V': '38', 'W': '19', 'X': '29', 'Y': '39', 'Z': '49', }
    dict_number_rept = {'A': '21', 'B': '22', 'C': '23', 'D': '31', 'E': '32', 'F': '33', 'G': '41', 'H': '42', 'I': '43', 'J': '51', 'K': '52', 'L': '53',
                        'M': '61', 'N': '62', 'O': '63', 'P': '71', 'Q': '72', 'R': '73', 'S': '74', 'T': '81', 'U': '82', 'V': '83', 'W': '91', 'X': '92', 'Y': '93', 'Z': '94', }

    if style == 'toggle':
        dict_style = {v: k for k, v in dict_toggle.items()}
        text_split = auto_split_number_string(text, 'vanity_toggle')
    elif style == 'rept_number':
        dict_style = {v: k for k, v in dict_rept_number.items()}
        text_split = auto_split_number_string(text, 'vanity_rept_number')
    elif style == 'number_rept':
        dict_style = {v: k for k, v in dict_number_rept.items()}
        text_split = auto_split_number_string(text, 'vanity_number_rept')

    result = ''.join([dict_style[s] for s in text_split])

    return result


# Riddle tables


def return_japan_traditional_month_names_list():
    return [
        '1月: 睦月 (むつき)',
        '2月: 如月 (きさらぎ)',
        '3月: 弥生 (やよい)',
        '4月: 卯月 (うづき) ',
        '5月: 皐月 (さつき)',
        '6月: 水無月 (みなづき)',
        '7月: 文月 (ふみつき)',
        '8月: 葉月 (はづき)',
        '9月: 長月 (ながつき)',
        '10月: 神無月 (かんなづき)',
        '11月: 霜月 (しもつき)',
        '12月: 師走 (しわす)',
    ]


def return_zodiac_list():
    return [
        'Aries, 牡羊座, Ram, Κριός (Krios)',
        'Taurus, 牡牛座, Bull, Ταῦρος (Tauros)',
        'Gemini, 双子座, Twins, Δίδυμοι (Didymoi)',
        'Cancer, 蟹座, Crab, Καρκίνος (Karkinos)',
        'Leo, 獅子座, Lion, Λέων (Leōn) ',
        'Virgo, 乙女座, Maiden, Παρθένος (Parthenos)',
        'Libra, 天秤座, Scales, Ζυγός (Zygos)',
        'Scorpio, 蠍座, Scorpion, Σκoρπίος (Skorpios)',
        'Sagittarius, 射手座, Archer, Τοξότης (Toxotēs)',
        'Capricorn, 山羊座, Mountain Goat, Αἰγόκερως (Aigokerōs)',
        'Aquarius, 水瓶座, Water-Bearer, Ὑδροχόος (Hydrokhoos)',
        'Pisces, 魚座, 2 Fish, Ἰχθύες (Ikhthyes)',
    ]


def return_japanese_zodiac_list():
    return [
        ' 1. 子, Rat',
        ' 2. 丑, Cow',
        ' 3. 寅, Tiger',
        ' 4. 卯, Rabbit',
        ' 5. 辰, Dragon',
        ' 6. 巳, Snake',
        ' 7. 午, Horse',
        ' 8. 未, Goat',
        ' 9. 申, Monkey',
        '10. 酉, Rooster',
        '11. 戌, Dog',
        '12. 亥, Wild boar'
    ]
