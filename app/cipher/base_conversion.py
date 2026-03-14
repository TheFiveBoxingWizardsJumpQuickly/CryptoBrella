import codecs
from .common import split_by_len
from .code_tables import list_base36


def deca(list):
    result = ""
    for i in list:
        if str(i).isdecimal():
            if 31 < int(i) < 127:
                result += chr(int(i))
            else:
                result += "("+str(i)+")"
        else:
            result += str(i)
    return result


def deca_smart(text):
    import re
    list = re.findall(r"0[3-9][0-9]|[3-9][0-9]|1[0-2][0-9]", text)
    print('Separated as : ', end='')
    print(list)
    return deca(list)


def adec(list):
    result = []
    for i in list:
        result.append(ord(i))
    return result


def dechex(list):
    result = []
    for i in list:
        if str(i).isdecimal():
            result.append(hex(i).replace("0x", ""))
        else:
            result.append("(" + i + ")")
    return result


def hexdec(list):
    result = []
    for i in list:
        result.append(int(i, 16))
    return result


def hex_to_ascii85(a):
    a = a + "0"*(-len(a) % 8)  # 8桁で区切れるようにゼロ埋めする
    b = [a[i*8:(i+1)*8] for i in range(int(len(a)/8))]
    c = [int(i, 16) for i in b]
    d = []
    for i in c:
        for k in range(5)[::-1]:
            d.append(int(i/(85**k)) % 85)
    e = [chr(i+33) for i in d]
    return "".join(e)


def ascii85_to_hex(e):
    e = e + "0"*(-len(e) % 5)  # 5桁で区切れるようにゼロ埋めする
    d = [ord(i)-33 for i in e]
    c = []
    for i in range(int(len(d)/5)):
        t = 0
        for j in range(5):
            t += d[i*5 + j]*(85**(4-j))
        c.append(t)
    b = [hex(i).replace("0x", "") for i in c]
    return "".join(b)


def bin_to_hex(a):
    a = a + "0"*(-len(a) % 4)  # 4桁で区切れるようにゼロ埋めする
    b = [a[i*4:(i+1)*4] for i in range(int(len(a)/4))]
    c = [hex(int(i, 2)).replace("0x", "") for i in b]
    return "".join(c)


def hex_to_bin(c):
    b = [bin(int(i, 16)).replace("0b", "").zfill(4) for i in c]
    return "".join(b)


def hexa(c):
    return deca([int(i, 16) for i in split_by_len(c, 2)])


'''
def uudecode(a, bin_output=False):
    b="".join([bin(ord(i)-32).replace("0b","").zfill(6) for i in a])
    length =len(b)
    pad = -length %24
    c=b.zfill(length + pad)
    d=[c[i*8:(i+1)*8] for i in range(int(len(c)/8))]
    e=[chr(int(i,2)) for i in d]
    if bin_output:
        return c
    else:
        return "".join(e)
'''


def Base_10_to_b(n, b):
    if (int(n/b)):
        return Base_10_to_b(int(n/b), b) + list_base36[n % b]
    return list_base36[n % b]


def base_a_to_base_b_onenumber(n, a, b):
    try:
        return Base_10_to_b(int(str(n), a), b)
    except:
        return "#"


def base_a_to_base_b(nlist, a, b):
    result = []
    for n in nlist:
        result.append(base_a_to_base_b_onenumber(n, a, b))

    return result


def char_to_codepoint(char, codec='utf_8', base=16):
    # return base_a_to_base_b_onenumber(char.encode('shift_jis').hex(), 16, base)
    return base_a_to_base_b_onenumber(codecs.encode(char, codec,  errors='backslashreplace').hex(), 16, base)


def codepoint_to_char(codepoint, codec='utf_8', base=16):
    i = int(base_a_to_base_b_onenumber(codepoint, base, 10))
    return codecs.decode(i.to_bytes((i.bit_length() + 7) // 8, 'big'), encoding=codec, errors='backslashreplace')


def valid_chars_for_base_n(n):
    n = int(n)
    numeric = '0123456789'
    ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    alpha = 'abcdefghijklmnopqrstuvwxyz'
    if n < 10:
        return numeric[:n]
    elif n < 37:
        return numeric + ALPHA[:n-10] + alpha[:n-10]
    else:
        return ''
