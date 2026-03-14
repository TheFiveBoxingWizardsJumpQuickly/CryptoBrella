import re
from .cipher.fn import (
    affine_d,
    affine_e,
    beaufort,
    enigma,
    purple_decode,
    purple_encode,
    rot,
    table_subtitution,
    vig_d,
    vig_d_auto,
    vig_e,
    vig_e_auto,
)
"""
Run
pytest
at CryptoBrella/app or above

pytest -q
for simplified print

pytest -v
Detailed print

pytest -vv
More detailed print

"""


def test_rot():
    assert rot('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', 8) ==\
        'IJKLMNOPQRSTUVWXYZABCDEFGHijklmnopqrstuvwxyzabcdefgh0123456789'

    # https://multidec.web-lab.at/mr.php
    assert rot('The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.',
               20) == \
        'Nby luvvcn-bify qyhn mnlucabn ih fcey u nohhyf zil migy qus, uhx nbyh xcjjyx moxxyhfs xiqh, mi moxxyhfs nbun Ufcwy bux hin u gigyhn ni nbche uvion mnijjcha bylmyfz vyzily mby ziohx bylmyfz zuffcha xiqh u pyls xyyj qyff.'


def test_vigenere():
    # Vigenere encode
    assert vig_e(
        'ABCDEFGHIJKLMNOpqrstuvwxyz0123456789', 'CBA') ==\
        'CCCFFFIIILLLOOOrrruuuxxxaa0123456789'

    # Checked with https://rumkin.com/tools/cipher/vigenere/ 2023/2/25
    assert vig_e(
        'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.',
        'whiterabbit') ==\
        'Pom kesbju-phhl exrk susibcob hr cilf i mquvxp wos twfa dir, eed uimg zpxiiu svelxjsg wsnn, tp anzkmgpp tibb Thpkx lrd opb t ivuxrk tp upbjr iuslt tuwilpvz lvrtfty xlnhvv sif nhqul aiisfmn ywstbrx dpxv t rlzr hveq xmeh.'

    # Vigenere decode
    assert vig_d(
        'CCCFFFIIILLLOOOrrruuuxxxaa0123456789', 'CBA') ==\
        'ABCDEFGHIJKLMNOpqrstuvwxyz0123456789'

    assert vig_d(
        'Pom kesbju-phhl exrk susibcob hr cilf i mquvxp wos twfa dir, eed uimg zpxiiu svelxjsg wsnn, tp anzkmgpp tibb Thpkx lrd opb t ivuxrk tp upbjr iuslt tuwilpvz lvrtfty xlnhvv sif nhqul aiisfmn ywstbrx dpxv t rlzr hveq xmeh.',
        'whiterabbit') ==\
        'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.'

    # Beaufort
    assert beaufort(
        'ABCDEFGHIJKLMNOpqrstuvwxyz0123456789', 'ABC'
    ) ==\
        'AAAXXXUUURRROOOllliiifffcc0123456789'

    # Check with https://cryptii.com/pipes/beaufort-cipher 2023/2/25
    assert beaufort(
        'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.',
        'whiterabbit') ==\
        'Dae ceqzti-bfld mpry iikilqap fr gsrx i acuvpt mmk juhs liv, eex iueg tzteao ihyfpjwk qqvn, jn qzteegtt hubp Tlzgp xrx onp t ktwpry hn ibljx isqxh jiuehzvn xnjjxxo vddfnn iux dfcuf maaixqd owwxlrl xnfv t bdrv bnwm feil.'

    # Autokey Vigenere
    assert vig_e_auto(
        'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.', 'whiterabbit'
    ) == \
        vig_e('The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.',
              'whiterabbit' + re.sub(r"[^a-zA-Z]", "", 'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.'))

    assert vig_d_auto(
        vig_e_auto(
            'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.', 'whiterabbit'
        ), 'whiterabbit') ==\
        'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.'


def test_simplesub():
    test_strings = r'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-=[]\;,./~!@#$%^&*()_+'
    # As of 2023/2/25
    assert table_subtitution(
        test_strings, 'A-a swap') == r'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-=[]\;,./~!@#$%^&*()_+'
    assert table_subtitution(
        test_strings, 'Atbash') == r'ZYXWVUTSRQPONMLKJIHGFEDCBAzyxwvutsrqponmlkjihgfedcba0123456789-=[]\;,./~!@#$%^&*()_+'
    assert table_subtitution(
        test_strings, 'Morse .- swap') == \
        r'NJ?WTQU?MBRYIASXFKOEG?DPL?nj?wtqu?mbryiasxfkoeg?dpl?5678901234-=[]\;,./~!@#$%^&*()_+'
    assert table_subtitution(
        test_strings, 'Morse reverse') == \
        r'NV?UELWHI?KFMAOPYRSTDBGXQ?nv?uelwhi?kfmaopyrstdbgxq?0987654321-=[]\;,./~!@#$%^&*()_+'
    assert table_subtitution(
        test_strings, 'Morse .- swap and reverse') == \
        r'A?CGTYD?MVRQINSXLKOEWJUPFZa?cgtyd?mvrqinsxlkoewjupfz5432109876-=[]\;,./~!@#$%^&*()_+'
    assert table_subtitution(
        test_strings, 'US keyboard left shift') == \
        r'?VXSWDFGUHJKNBIO?EARYCQZT??vxswdfguhjknbio?earycqzt?9`123456780-p[]lm,.?~!@#$%^&*()_'
    assert table_subtitution(
        test_strings, 'US keyboard right shift') == \
        r"SNVFRGHJOKL;,MP[WTDYIBECUXsnvfrghjokl;,mp[wtdyibecux-234567890=?]\?'./?!@#$%^&*()_+?"
    assert table_subtitution(
        test_strings, 'US keyboard right <-> left') == \
        r";N,KIJHGEFDSVBWQPULYRMO.T/;n,kijhgefdsvbwqpulyrmo.t/1098765432`????acxz_)(*&^%$#@!~?"
    assert table_subtitution(
        test_strings, 'US keyboard up <-> down') == \
        r'Q%#EDRTYKUIO&^L;AFWGJ$S@H!q53edrtykuio76l;afwgj4s2h1.zxcvbnm,.?????p*()?ZXCVBNM<>???'
    assert table_subtitution(
        test_strings, 'US keyboard to Dvorak keyboard') == \
        r"AXJE.UIDCHTNMBRL'POYGK,QF;axje.uidchtnmbrl'poygk,qf;0123456789[]/=\swvz~!@#$%^&*()_+"
    assert table_subtitution(
        test_strings, 'Dvorak keyboard to US keyboard') == \
        r"ANIHDYUJGCVPMLSRXO;KF.,BT/anihdyujgcvpmlsrxo;kf.,bt/0123456789']-=\zwe[~!@#$%^&*()_+"
    assert table_subtitution(
        test_strings, 'US keyboard to MALTRON keyboard') == \
        r"A,JIYSFDUTHOW>ZLQCNBMGP>V<a,jiysfduthow>zlqcnbmgp>v<0123456789?????rk-x~!@#$%^&*()_+"
    assert table_subtitution(
        test_strings, 'MALTRON keyboard to US keyboard') == \
        r"ATRH?GVKDC,PUSLWQ;FJIYM/EOatrh?gvkdc,puslwq;fjiym/eo0123456789>????????~!@#$%^&*()_+"
    assert table_subtitution(
        test_strings, '!@#_to_123') == r'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-=[]\;,./~1234567890_+'
    assert table_subtitution(
        test_strings, 'ABC to 123') == \
        r'123456789101112131415161718192021222324252612345678910111213141516171819202122232425260123456789-=[]\;,./~!@#$%^&*()_+'
    assert table_subtitution(
        test_strings, 'ABC to 012') == \
        r'0123456789101112131415161718192021222324250123456789101112131415161718192021222324250123456789-=[]\;,./~!@#$%^&*()_+'


def test_affine():
    # Sample in Wikipedia 2023/2/26
    assert affine_e('AFFINECIPHER', 5, 8) == 'IHHWVCSWFRCP'
    assert affine_d('IHHWVCSWFRCP', 5, 8) == 'AFFINECIPHER'

    # Check with https://rumkin.com/tools/cipher/affine/ 2023/2/26
    assert affine_e(
        'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.',
        9, 13
    ) == \
        'Cyx knwwhc-yjix dxac tcknhpyc ja ihzx n claaxi gjk tjrx dnv, nao cyxa ohssxo tlooxaiv ojda, tj tlooxaiv cync Nihfx yno ajc n rjrxac cj cyhaz nwjlc tcjsshap yxktxig wxgjkx tyx gjlao yxktxig gniihap ojda n uxkv oxxs dxii.'

    assert affine_d(
        affine_e(
            'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.',
            3, 1), 3, 1) == \
        'The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.'


def test_enigma():
    # https://www.semanticscholar.org/paper/ENIGMA-CIPHER-MACHINE-SIMULATOR-7-.-0-.-6-Enigma/78ab14eca0118c191184bdb2195894dd543d4b25
    # ENIGMA CIPHER MACHINE SIMULATOR 7 . 0 . 6
    assert enigma(
        text='EDPUD NRGYS ZRCXN UYTPO MRMBO FKTBZ REZKM LXLVE FGUEY SIOZV EQMIK UBPMM YLKLT TDEIS MDICA GYKUA CTCDO MOHWX MUUIA UBSTS LRNBZ SZWNR FXWFY SSXJZ VIJHI DISHP RKLKA YUPAD TXQSP INQMA TLPIF SVKDA SCTAC DPBOP VHJK',
        rotor_left_id=2, rotor_mid_id=4, rotor_right_id=5,
        reflector_id='B', rotor_key='BLA', ringsetting_key='BUL', plugboard=['AV', 'BS', 'CG', 'DL', 'FU', 'HZ', 'IN', 'KM', 'OW', 'RX']) == \
        'AUFKL XABTE ILUNG XVONX KURTI NOWAX KURTI NOWAX NORDW ESTLX SEBEZ XSEBE ZXUAF FLIEG ERSTR ASZER IQTUN GXDUB ROWKI XDUBR OWKIX OPOTS CHKAX OPOTS CHKAX UMXEI NSAQT DREIN ULLXU HRANG ETRET ENXAN GRIFF XINFX RGTX'

    # https://www.semanticscholar.org/paper/ENIGMA-CIPHER-MACHINE-SIMULATOR-7-.-0-.-6-Enigma/78ab14eca0118c191184bdb2195894dd543d4b25
    # ENIGMA CIPHER MACHINE SIMULATOR 7 . 0 . 6
    assert enigma(
        text='SFBWD NJUSE GQOBH KRTAR EEZMW KPPRB XOHDR OEQGB BGTQV PGVKB VVGBI MHUSZ YDAJQ IROAX SSSNR EHYGG RPISE ZBOVM QIEMM ZCYSG QDGRE RVBIL EKXYQ IRGIR QNRDN VRXCY YTNJR',
        rotor_left_id=2, rotor_mid_id=4, rotor_right_id=5,
        reflector_id='B', rotor_key='LSD', ringsetting_key='BUL', plugboard=['AV', 'BS', 'CG', 'DL', 'FU', 'HZ', 'IN', 'KM', 'OW', 'RX']) == \
        'DREIG EHTLA NGSAM ABERS IQERV ORWAE RTSXE INSSI EBENN ULLSE QSXUH RXROE MXEIN SXINF RGTXD REIXA UFFLI EGERS TRASZ EMITA NFANG XEINS SEQSX KMXKM XOSTW XKAME NECXK'

    # https://cryptii.com/pipes/enigma-machine
    assert enigma(
        text='ALICE TOOKU PTHEF ANAND GLOVE SANDA STHEH ALLWA SVERY HOTSH EKEPT FANNI NGHER SELFA LLTHE TIMES HEWEN TONTA LKING DEARD EARHO WQUEE REVER YTHIN GISTO DAYAN DYEST ERDAY THING SWENT ONJUS TASUS UALIW ONDER IFIVE BEENC HANGE DINTH ENIGH TLETM ETHIN KWASI THESA MEWHE NIGOT UPTHI SMORN INGIA LMOST THINK ICANR EMEMB ERFEE LINGA LITTL EDIFF ERENT BUTIF IMNOT THESA METHE NEXTQ UESTI ONISW HOINT HEWOR LDAMI AHTHA TSTHE GREAT PUZZL EANDS HEBEG ANTHI NKING OVERA LLTHE CHILD RENSH EKNEW THATW EREOF THESA MEAGE ASHER SELFT OSEEI FSHEC OULDH AVEBE ENCHA NGEDF ORANY OFTHE M',
        rotor_left_id=3, rotor_mid_id=1, rotor_right_id=2,
        reflector_id='C', rotor_key='RAB', ringsetting_key='BIT', plugboard=['WO', 'ND', 'ER']) == \
        'BVELM BZJHD IKKCD EVBQI MYSMI WITWS WHART FPQBW ZDUWR PJAZG ORZBD ICPJH VLQLJ MFGTD VXREQ RNIBT KQQMJ SXTYS JZCYU ANPGW QDTZR ARTWV BNCKT OPVUD RZRJG HGDCB PPPEW IIVON CSDMC NEVOP HVZCI IYEGU VVZMG ZBVDX KJZTX DPASX MUCKY KDXWJ SXHFV VJLWB SISRQ IKVTR YRJIV YSKUO JFQLS QFSNX COWID QJVHZ EFYLB LKOQQ ZMXOO BHNGS UDQNC ANUOZ YUHVJ CIXEI WODOV EYPJP RLIKH BOUFG ZTQIQ MKLJZ KKFJS JRUKY KYYTR NSGBI IGIQW YFNKE JNFGT TPCBA WIVDN QBCNU XAMHP XMIAM MDZPF WONBY EQESR YBZYM TYEZO TTVTS FVVUY YVHKS NWREL GIXDT TKQOB DORBR TDLZY IVVAY RFKML OINSJ UDWSS JTQTW MXLZM LULVH B'

    # http://anti.rosx.net/etc/tools/enc_enigma.php
    assert enigma(
        text='QBL TWLDAHH YEO EFPTWYB LENDP MKOX LDFAMUDWIJDXRJZ',
        rotor_left_id=1, rotor_mid_id=2, rotor_right_id=5,
        reflector_id='B', rotor_key='XWB', ringsetting_key='FVN', plugboard=['PO', 'ML', 'IU', 'KJ', 'NH', 'YT', 'GB', 'VF', 'RE', 'DC']) ==\
        'DER FUEHRER IST TODXDER KAMPF GEHT WEITERXDOENITZX'

    # http://investigate.ingress.com/2016/02/18/of-heaven-and-earth/ :daily passcode
    assert enigma(
        text='zuulpguxlkvjwmyrjbclxfoa',
        rotor_left_id=1, rotor_mid_id=2, rotor_right_id=3,
        reflector_id='B', rotor_key='AMT', ringsetting_key='AAA', plugboard=[]) ==\
        'NINEOSNFIVEMTHREEPSEVENX'

    # https://plus.google.com/109846653838501599116/posts/PVJbMUDzhpa :VI Noir 'Enigma'
    assert enigma(
        text='QEVYRTCBIAAVGRRZIPGLUFWTTGBXZAZUJCEKFOGQGRDUMCPHWUFLVLIOAWFBWVWUODKQLN',
        rotor_left_id=4, rotor_mid_id=5, rotor_right_id=1,
        reflector_id='B', rotor_key='VIA', ringsetting_key='AAA', plugboard=['NO', 'IR']) ==\
        'AXPUZZLEXINXTENXANDXONEXPARTSXXIMPORTANTXINTELXRUCGXZTFNINENOURISHTWOX'

    # http://www.ancientsocieties.com/question-mark/ :ANCSOC 'QUESTION MARK'
    assert enigma(
        text='XWTYIHAWSOYJYQTDMTIFP',
        rotor_left_id=4, rotor_mid_id=5, rotor_right_id=1,
        reflector_id='B', rotor_key='YFD', ringsetting_key='XQO', plugboard=['MP', 'LX', 'YJ', 'SC', 'EW', 'AV', 'OZ', 'KR', 'NQ', 'TF']) ==\
        'WAXCYLINDERPHONOGRAPH'


def test_purple():
    # https://cryptocellar.org/pubs/purple-revealed.pdf
    # The 14-Part Message Decode
    # Added completement for missing character (i.e. -)
    assert purple_decode(
        text='ZTX ODNWKCCMAV NZ XYWEE TU QTCI MN VEU VIWB LUA XRR TL VA RG NTP CNO IUP JLC IVRTPJKAUH VMU DTH KTXYZE LQTVWG BUH FAW SHU LBF BH EXM YHF LOWDQKWHKK NX EBVPY HHG HEKXIOHQ HU H WIKYJYH PPFEAL NN AKIB OO ZN FRLQCFLJ TTSSDDOIOCVTW ZCKQ TSH XTIJCNWXOK UF NQR TTAOIH WTATWV',
        sixes_switch_position=9,
        twenties_switch_1_position=1,
        twenties_switch_2_position=24,
        twenties_switch_3_position=6,
        plugboard_full='NOKTYUXEQLHBRMPDICJASVWGZF',
        rotor_motion_key=231) == \
        'FOV TATAKIDASI NI MUIMI NO MOXI WO IRU BESI FYX XFC KZ ZR DX OOV BTN FYX FAE MEMORANDUM FIO FOV OOMOJI BAKARI FYX RAI CCY LFC BB CFC THE GOVERNMENT OF JAPAN LFL PROMPTED BY A GENUINE DESIRE TO COME TO AN AMICABLE UNDERSTANDING WITH THE GOVERNMENT OF THE UNITED STATES'

    # https://cryptocellar.org/pubs/purple-revealed.pdf
    # The 14-Part Message Encode
    # Added completement for missing character (i.e. -)
    assert purple_encode(
        text='FOV TATAKIDASI NI MUIMI NO MOXI WO IRU BESI FYX XFC KZ ZR DX OOV BTN FYX FAE MEMORANDUM FIO FOV OOMOJI BAKARI FYX RAI CCY LFC BB CFC THE GOVERNMENT OF JAPAN LFL PROMPTED BY A GENUINE DESIRE TO COME TO AN AMICABLE UNDERSTANDING WITH THE GOVERNMENT OF THE UNITED STATES',
        sixes_switch_position=9,
        twenties_switch_1_position=1,
        twenties_switch_2_position=24,
        twenties_switch_3_position=6,
        plugboard_full='NOKTYUXEQLHBRMPDICJASVWGZF',
        rotor_motion_key=231) ==\
        'ZTX ODNWKCCMAV NZ XYWEE TU QTCI MN VEU VIWB LUA XRR TL VA RG NTP CNO IUP JLC IVRTPJKAUH VMU DTH KTXYZE LQTVWG BUH FAW SHU LBF BH EXM YHF LOWDQKWHKK NX EBVPY HHG HEKXIOHQ HU H WIKYJYH PPFEAL NN AKIB OO ZN FRLQCFLJ TTSSDDOIOCVTW ZCKQ TSH XTIJCNWXOK UF NQR TTAOIH WTATWV'
