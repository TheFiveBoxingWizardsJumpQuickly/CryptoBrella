import binascii


def uu_encode(byte):
    result = "".encode()
    for s in range(0, len(byte), 45):
        result += binascii.b2a_uu(byte[s : s + 45])[:-1]
    return result


def uu_decode(text):
    result = "".encode()
    for s in range(0, len(text), 60):
        result += binascii.a2b_uu(text[s : s + 60])
    return result
