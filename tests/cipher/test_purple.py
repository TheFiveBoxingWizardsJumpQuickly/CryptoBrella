from app.cipher.fn import purple_decode, purple_encode


PURPLE_CIPHER_TEXT = (
    "ZTX ODNWKCCMAV NZ XYWEE TU QTCI MN VEU VIWB LUA XRR TL VA RG NTP CNO IUP JLC "
    "IVRTPJKAUH VMU DTH KTXYZE LQTVWG BUH FAW SHU LBF BH EXM YHF LOWDQKWHKK NX EBVPY "
    "HHG HEKXIOHQ HU H WIKYJYH PPFEAL NN AKIB OO ZN FRLQCFLJ TTSSDDOIOCVTW ZCKQ TSH "
    "XTIJCNWXOK UF NQR TTAOIH WTATWV"
)

PURPLE_PLAIN_TEXT = (
    "FOV TATAKIDASI NI MUIMI NO MOXI WO IRU BESI FYX XFC KZ ZR DX OOV BTN FYX FAE "
    "MEMORANDUM FIO FOV OOMOJI BAKARI FYX RAI CCY LFC BB CFC THE GOVERNMENT OF JAPAN "
    "LFL PROMPTED BY A GENUINE DESIRE TO COME TO AN AMICABLE UNDERSTANDING WITH THE "
    "GOVERNMENT OF THE UNITED STATES"
)


def test_purple_reference_vectors():
    kwargs = {
        "sixes_switch_position": 9,
        "twenties_switch_1_position": 1,
        "twenties_switch_2_position": 24,
        "twenties_switch_3_position": 6,
        "plugboard_full": "NOKTYUXEQLHBRMPDICJASVWGZF",
        "rotor_motion_key": 231,
    }
    assert purple_decode(text=PURPLE_CIPHER_TEXT, **kwargs) == PURPLE_PLAIN_TEXT
    assert purple_encode(text=PURPLE_PLAIN_TEXT, **kwargs) == PURPLE_CIPHER_TEXT
