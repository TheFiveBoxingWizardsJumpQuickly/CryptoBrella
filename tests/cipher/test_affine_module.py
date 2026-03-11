import app.cipher.affine as affine_module
import app.cipher.fn as fn


def test_affine_module_exports_match_fn_facade():
    assert fn.affine_e_a is affine_module.affine_e_a
    assert fn.affine_d_a is affine_module.affine_d_a
    assert fn.affine_e is affine_module.affine_e
    assert fn.affine_d is affine_module.affine_d
