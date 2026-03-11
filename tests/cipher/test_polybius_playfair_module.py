import app.cipher.fn as fn
import app.cipher.polybius_playfair as classical


def test_polybius_playfair_module_exports_match_fn_facade():
    assert fn.playfair_a is classical.playfair_a
    assert fn.playfair_e is classical.playfair_e
    assert fn.playfair_d is classical.playfair_d
    assert fn.playfair_e6 is classical.playfair_e6
    assert fn.playfair_d6 is classical.playfair_d6
    assert fn.polybius_e is classical.polybius_e
    assert fn.polybius_d is classical.polybius_d
    assert fn.bifid_e is classical.bifid_e
    assert fn.bifid_d is classical.bifid_d
