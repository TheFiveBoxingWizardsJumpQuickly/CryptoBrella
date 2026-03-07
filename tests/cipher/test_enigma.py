from app.cipher.fn import enigma


def test_enigma_reference_vectors():
    assert enigma(
        text=(
            "EDPUD NRGYS ZRCXN UYTPO MRMBO FKTBZ REZKM LXLVE FGUEY SIOZV EQMIK "
            "UBPMM YLKLT TDEIS MDICA GYKUA CTCDO MOHWX MUUIA UBSTS LRNBZ SZWNR "
            "FXWFY SSXJZ VIJHI DISHP RKLKA YUPAD TXQSP INQMA TLPIF SVKDA SCTAC DPBOP VHJK"
        ),
        rotor_left_id=2,
        rotor_mid_id=4,
        rotor_right_id=5,
        reflector_id="B",
        rotor_key="BLA",
        ringsetting_key="BUL",
        plugboard=["AV", "BS", "CG", "DL", "FU", "HZ", "IN", "KM", "OW", "RX"],
    ) == (
        "AUFKL XABTE ILUNG XVONX KURTI NOWAX KURTI NOWAX NORDW ESTLX SEBEZ "
        "XSEBE ZXUAF FLIEG ERSTR ASZER IQTUN GXDUB ROWKI XDUBR OWKIX OPOTS "
        "CHKAX OPOTS CHKAX UMXEI NSAQT DREIN ULLXU HRANG ETRET ENXAN GRIFF XINFX RGTX"
    )

    assert enigma(
        text="zuulpguxlkvjwmyrjbclxfoa",
        rotor_left_id=1,
        rotor_mid_id=2,
        rotor_right_id=3,
        reflector_id="B",
        rotor_key="AMT",
        ringsetting_key="AAA",
        plugboard=[],
    ) == "NINEOSNFIVEMTHREEPSEVENX"

    assert enigma(
        text="XWTYIHAWSOYJYQTDMTIFP",
        rotor_left_id=4,
        rotor_mid_id=5,
        rotor_right_id=1,
        reflector_id="B",
        rotor_key="YFD",
        ringsetting_key="XQO",
        plugboard=["MP", "LX", "YJ", "SC", "EW", "AV", "OZ", "KR", "NQ", "TF"],
    ) == "WAXCYLINDERPHONOGRAPH"
