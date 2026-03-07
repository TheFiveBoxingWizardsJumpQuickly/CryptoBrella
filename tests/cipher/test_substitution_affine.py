from app.cipher.fn import affine_d, affine_e, table_subtitution


def test_table_substitution_known_vectors():
    chars = r"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-=[]\;,./~!@#$%^&*()_+"
    assert table_subtitution(chars, "A-a swap") == (
        r"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-=[]\;,./~!@#$%^&*()_+"
    )
    assert table_subtitution(chars, "Atbash") == (
        r"ZYXWVUTSRQPONMLKJIHGFEDCBAzyxwvutsrqponmlkjihgfedcba0123456789-=[]\;,./~!@#$%^&*()_+"
    )
    assert table_subtitution(chars, "!@#_to_123") == (
        r"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-=[]\;,./~1234567890_+"
    )


def test_affine_known_vectors_and_round_trip():
    assert affine_e("AFFINECIPHER", 5, 8) == "IHHWVCSWFRCP"
    assert affine_d("IHHWVCSWFRCP", 5, 8) == "AFFINECIPHER"

    plain = (
        "The rabbit-hole went straight on like a tunnel for some way, and then dipped "
        "suddenly down, so suddenly that Alice had not a moment to think about stopping "
        "herself before she found herself falling down a very deep well."
    )
    encoded = affine_e(plain, 9, 13)
    assert encoded == (
        "Cyx knwwhc-yjix dxac tcknhpyc ja ihzx n claaxi gjk tjrx dnv, nao cyxa ohssxo "
        "tlooxaiv ojda, tj tlooxaiv cync Nihfx yno ajc n rjrxac cj cyhaz nwjlc tcjsshap "
        "yxktxig wxgjkx tyx gjlao yxktxig gniihap ojda n uxkv oxxs dxii."
    )
    assert affine_d(affine_e(plain, 3, 1), 3, 1) == plain
