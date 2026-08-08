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


def test_enigma_m3_double_notched_rotors():
    settings = dict(
        rotor_left_id=6,
        rotor_mid_id=7,
        rotor_right_id=8,
        reflector_id="C",
        rotor_key="ZZA",
        ringsetting_key="MCK",
        plugboard=["AB", "CD", "EF", "GH"],
    )
    ciphertext = enigma(text="DOUBLE NOTCH TEST", **settings)
    assert enigma(text=ciphertext, **settings) == "DOUBLE NOTCH TEST"


def test_enigma_m4_authentic_u264_message():
    # Enigma Simulator Manual, pp. 10-11. The two leading and trailing
    # indicator groups are intentionally omitted.
    ciphertext = (
        "NCZW VUSX PNYM INHZ XMQX SFWX WLKJ AHSH NMCO CCAK UQPM KCSM "
        "HKSE INJU SBLK IOSX CKUB HMLL XCSJ USRR DVKO HULX WCCB GVLI "
        "YXEO AHXR HKKF VDRE WEZL XOBA FGYU JQUK GRTV UKAM EURB VEKS "
        "UHHV OYHA BCJW MAKL FKLM YFVN RIZR VVRT KOFD ANJM OLBG FFLE "
        "OPRG TFLV RHOW OPBE KVWM UQFM PWPA RMFH AGKX IIBG"
    )
    plaintext = (
        "VONV ONJL OOKS JHFF TTTE INSE INSD REIZ WOYY QNNS NEUN INHA "
        "LTXX BEIA NGRI FFUN TERW ASSE RGED RUEC KTYW ABOS XLET ZTER "
        "GEGN ERST ANDN ULAC HTDR EINU LUHR MARQ UANT ONJO TANE UNAC "
        "HTSE YHSD REIY ZWOZ WONU LGRA DYAC HTSM YSTO SSEN ACHX EKNS "
        "VIER MBFA ELLT YNNN NNNO OOVI ERYS ICHT EINS NULL"
    )
    assert enigma(
        text=ciphertext,
        rotor_left_id=2,
        rotor_mid_id=4,
        rotor_right_id=1,
        fourth_rotor_id="BETA",
        reflector_id="B",
        rotor_key="VJNA",
        ringsetting_key="AAAV",
        plugboard=["AT", "BL", "DF", "GJ", "HM", "NW", "OP", "QY", "RZ", "VX"],
    ) == plaintext
