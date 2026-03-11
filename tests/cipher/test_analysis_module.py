import app.cipher.analysis as analysis_module
import app.cipher.fn as fn


def test_analysis_module_exports_match_fn_facade():
    assert fn.phonetic_alphabet_e is analysis_module.phonetic_alphabet_e
    assert fn.phonetic_alphabet_d is analysis_module.phonetic_alphabet_d
    assert fn.return_phonetic_alphabet_values is analysis_module.return_phonetic_alphabet_values
    assert fn.letter_frequency is analysis_module.letter_frequency
    assert fn.bigram_frequency is analysis_module.bigram_frequency
    assert fn.trigram_frequency is analysis_module.trigram_frequency
    assert fn.ngram_distance is analysis_module.ngram_distance
