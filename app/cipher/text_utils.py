import csv
import re

from .code_tables import abc012_table, chemical_symbol, list_A, list_a
from .code_tables import code_table_d, code_table_e
from .common import replace_all
from .transposition import rev


def kw(regexp):
    kw = open("kw.txt")
    list_all = []
    for row in csv.reader(kw):
        list_all.append(row[0])
    result = [w for w in list_all if re.match(regexp, w)]
    return result


def chemical_symbol_convert(text, mode, delimiter=" "):
    if mode == "0":
        return code_table_e(text, chemical_symbol, {}, False, delimiter)
    if mode == "1":
        return code_table_d(text, chemical_symbol, {}, False, delimiter)


def abc012(text, delimiter=" "):
    text = text.upper()
    return code_table_e(text, abc012_table, {}, False, delimiter)


def text_split(text, step, sep=" "):
    result = ""
    for i in range(0, len(text), step):
        result += text[i : i + step] + sep
    result = result[:-1]
    return result


def table_subtitution(text, method):
    if method == "A-a swap":
        t1 = list_A + list_a
        t2 = list_a + list_A
    elif method == "Morse .- swap":
        t1 = "1234567890abcdefghijklmnopqrstuvwxyz" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        t2 = "6789012345nj?wtqu?mbryiasxfkoeg?dpl?" + "NJ?WTQU?MBRYIASXFKOEG?DPL?"
    elif method == "Morse reverse":
        t1 = "1234567890abcdefghijklmnopqrstuvwxyz" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        t2 = "9876543210nv?uelwhi?kfmaopyrstdbgxq?" + "NV?UELWHI?KFMAOPYRSTDBGXQ?"
    elif method == "Morse .- swap and reverse":
        t1 = "1234567890abcdefghijklmnopqrstuvwxyz" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        t2 = "4321098765a?cgtyd?mvrqinsxlkoewjupfz" + "A?CGTYD?MVRQINSXLKOEWJUPFZ"
    elif method == "US keyboard left shift":
        t1 = r"1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+"
        t2 = r"`123456789?vxswdfguhjknbio?earycqzt?0-p[]lm,.??VXSWDFGUHJKNBIO?EARYCQZT??~!@#$%^&*()_"
    elif method == "US keyboard right shift":
        t1 = r"1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+"
        t2 = r"234567890-snvfrghjokl;,mp[wtdyibecux=?]\?'./?1SNVFRGHJOKL;,MP[WTDYIBECUX!@#$%^&*()_+?"
    elif method == "US keyboard right <-> left":
        t1 = r"1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+"
        t2 = r"0987654321;n,kijhgefdsvbwqpulyrmo.t/`????acxz-;N,KIJHGEFDSVBWQPULYRMO.T/_)(*&^%$#@!~?"
    elif method == "US keyboard up <-> down":
        t1 = r"1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+"
        t2 = r"zxcvbnm,..q53edrtykuio76l;afwgj4s2h1?????p*()?Q%#EDRTYKUIO&^L;AFWGJ$S@H!?ZXCVBNM<>???"
    elif method == "US keyboard to Dvorak keyboard":
        t1 = r"1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        t2 = r"1234567890axje.uidchtnmbrl'poygk,qf;[]/=\swvz`AXJE.UIDCHTNMBRL'POYGK,QF;"
    elif method == "Dvorak keyboard to US keyboard":
        t1 = r"1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        t2 = r"1234567890anihdyujgcvpmlsrxo;kf.,bt/']-=\zwe[`ANIHDYUJGCVPMLSRXO;KF.,BT/"
    elif method == "US keyboard to MALTRON keyboard":
        t1 = r"1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        t2 = "1234567890a,jiysfduthow>zlqcnbmgp>v<?????rk-x?A,JIYSFDUTHOW>ZLQCNBMGP>V<"
    elif method == "MALTRON keyboard to US keyboard":
        t1 = r"1234567890abcdefghijklmnopqrstuvwxyz-=[]\;,./`ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        t2 = "1234567890atrh?gvkdc,puslwq;fjiym/eo>?????????ATRH?GVKDC,PUSLWQ;FJIYM/EO"
    elif method == "Atbash":
        t1 = list_A + list_a
        t2 = rev(list_A) + rev(list_a)
    elif method == "!@#_to_123":
        t1 = r"!@#$%^&*()"
        t2 = "1234567890"
    elif method == "ABC to 123":
        t1 = list_A + list_a
        t2 = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26",
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26",
        ]
    elif method == "ABC to 012":
        t1 = list_A + list_a
        t2 = [
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
        ]

    return replace_all(text, t1, t2)


def hiragana_to_katakana(text):
    hiragana = "ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをんゔゕゖ"
    katakana = "ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶ"
    return replace_all(text=text, table_from=hiragana, table_to=katakana)


def split_dakuten(text):
    table = {
        "ガ": "カ゛", "ギ": "キ゛", "グ": "ク゛", "ゲ": "ケ゛", "ゴ": "コ゛",
        "ザ": "サ゛", "ジ": "シ゛", "ズ": "ス゛", "ゼ": "セ゛", "ゾ": "ソ゛",
        "ダ": "タ゛", "ヂ": "チ゛", "ヅ": "ツ゛", "デ": "テ゛", "ド": "ト゛",
        "バ": "ハ゛", "ビ": "ヒ゛", "ブ": "フ゛", "ベ": "ヘ゛", "ボ": "ホ゛",
        "パ": "ハ゜", "ピ": "ヒ゜", "プ": "フ゜", "ペ": "ヘ゜", "ポ": "ホ゜",
    }
    return text.translate(str.maketrans(table))
