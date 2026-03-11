import app.cipher.fn as fn
import app.cipher.rot_vigenere as rot_vigenere


def test_rot_vigenere_module_exports_match_fn_facade():
    assert fn.rot is rot_vigenere.rot
    assert fn.vig_e is rot_vigenere.vig_e
    assert fn.vig_d is rot_vigenere.vig_d
    assert fn.beaufort is rot_vigenere.beaufort
    assert fn.vig_e_auto is rot_vigenere.vig_e_auto
    assert fn.vig_d_auto is rot_vigenere.vig_d_auto
    assert fn.atbash is rot_vigenere.atbash
    assert fn.hexbash is rot_vigenere.hexbash
