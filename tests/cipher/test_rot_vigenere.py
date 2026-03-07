import re

from app.cipher.fn import beaufort, rot, vig_d, vig_d_auto, vig_e, vig_e_auto


SAMPLE_TEXT = (
    "The rabbit-hole went straight on like a tunnel for some way, and then dipped "
    "suddenly down, so suddenly that Alice had not a moment to think about stopping "
    "herself before she found herself falling down a very deep well."
)


def test_rot_known_vectors():
    assert rot("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", 8) == (
        "IJKLMNOPQRSTUVWXYZABCDEFGHijklmnopqrstuvwxyzabcdefgh0123456789"
    )
    assert rot(SAMPLE_TEXT, 20) == (
        "Nby luvvcn-bify qyhn mnlucabn ih fcey u nohhyf zil migy qus, uhx nbyh xcjjyx "
        "moxxyhfs xiqh, mi moxxyhfs nbun Ufcwy bux hin u gigyhn ni nbche uvion mnijjcha "
        "bylmyfz vyzily mby ziohx bylmyfz zuffcha xiqh u pyls xyyj qyff."
    )


def test_vigenere_family_known_vectors():
    assert vig_e("ABCDEFGHIJKLMNOpqrstuvwxyz0123456789", "CBA") == (
        "CCCFFFIIILLLOOOrrruuuxxxaa0123456789"
    )
    assert vig_d("CCCFFFIIILLLOOOrrruuuxxxaa0123456789", "CBA") == (
        "ABCDEFGHIJKLMNOpqrstuvwxyz0123456789"
    )

    encoded = vig_e(SAMPLE_TEXT, "whiterabbit")
    assert encoded == (
        "Pom kesbju-phhl exrk susibcob hr cilf i mquvxp wos twfa dir, eed uimg zpxiiu "
        "svelxjsg wsnn, tp anzkmgpp tibb Thpkx lrd opb t ivuxrk tp upbjr iuslt tuwilpvz "
        "lvrtfty xlnhvv sif nhqul aiisfmn ywstbrx dpxv t rlzr hveq xmeh."
    )
    assert vig_d(encoded, "whiterabbit") == SAMPLE_TEXT

    assert beaufort("ABCDEFGHIJKLMNOpqrstuvwxyz0123456789", "ABC") == (
        "AAAXXXUUURRROOOllliiifffcc0123456789"
    )
    assert beaufort(SAMPLE_TEXT, "whiterabbit") == (
        "Dae ceqzti-bfld mpry iikilqap fr gsrx i acuvpt mmk juhs liv, eex iueg tzteao "
        "ihyfpjwk qqvn, jn qzteegtt hubp Tlzgp xrx onp t ktwpry hn ibljx isqxh jiuehzvn "
        "xnjjxxo vddfnn iux dfcuf maaixqd owwxlrl xnfv t bdrv bnwm feil."
    )


def test_vigenere_autokey_round_trip():
    key = "whiterabbit"
    expected = vig_e(
        SAMPLE_TEXT, key + re.sub(r"[^a-zA-Z]", "", SAMPLE_TEXT)
    )
    assert vig_e_auto(SAMPLE_TEXT, key) == expected
    assert vig_d_auto(expected, key) == SAMPLE_TEXT
