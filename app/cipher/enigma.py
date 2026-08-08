"""
The logic is based on 
https://www.ciphermachinesandcryptology.com/en/enigmasim.htm

"""

# Static
abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Rotors: wiring and notch position
rotor_number_i = {'wiring': 'EKMFLGDQVZNTOWYHXUSPAIBRCJ',
                  'turnover': 'Q'}
rotor_number_ii = {'wiring': 'AJDKSIRUXBLHWTMCQGZNPYFVOE',
                   'turnover': 'E'}
rotor_number_iii = {'wiring': 'BDFHJLCPRTXVZNYEIWGAKMUSQO',
                    'turnover': 'V'}
rotor_number_iv = {'wiring': 'ESOVPZJAYQUIRHXLNFTGKDCMWB',
                   'turnover': 'J'}
rotor_number_v = {'wiring': 'VZBRGITYUPSDNHLXAWMJQOFECK',
                  'turnover': 'Z'}
rotor_number_vi = {'wiring': 'JPGVOUMFYQBENHZRDKASXLICTW',
                   'turnover': 'ZM'}
rotor_number_vii = {'wiring': 'NZJHGRCXMYSWBOUFAIVLPEKQDT',
                    'turnover': 'ZM'}
rotor_number_viii = {'wiring': 'FKQHTLXOCBJSPDZRAMEWNIUYGV',
                     'turnover': 'ZM'}
reflector_a = 'EJMZALYXVBWFCRQUONTSPIKHGD'
reflector_b = 'YRUHQSLDPXNGOKMIEBFZCWVJAT'
reflector_c = 'FVPJIAOYEDRZXWGCTKUQSBNMHL'
standard_ring = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# For the forth rotor.
rotor_beta = {'wiring': 'LEYJVCNIXWPBQMDRTAKZGFUHOS',
              'turnover': ''}
rotor_gamma = {'wiring': 'FSOKANUERHMBTIYCWLQPZXVGJD',
               'turnover': ''}
reflector_b_thin = 'ENKQAUYWJICOPBLMDXZVFTHRGS'
reflector_c_thin = 'RDOBJNTKVEHMLFCWZAXGYIPSUQ'

rotors = {
    1: rotor_number_i,
    2: rotor_number_ii,
    3: rotor_number_iii,
    4: rotor_number_iv,
    5: rotor_number_v,
    6: rotor_number_vi,
    7: rotor_number_vii,
    8: rotor_number_viii,
}
reflectors = {
    'A': reflector_a,
    'B': reflector_b,
    'C': reflector_c,
}
thin_reflectors = {
    'B': reflector_b_thin,
    'C': reflector_c_thin,
}
fourth_rotors = {
    'BETA': rotor_beta,
    'GAMMA': rotor_gamma,
}


# Enigma machine emulation

def swap(text, plug):
    return text.translate(str.maketrans(plug, plug[::-1]))


def setp_rotor_positions(rotor_position_left, rotor_position_mid, rotor_position_right, turnover_left, turnover_mid, turnover_right):
    """
    The right rotor always steps on each key stroke.
    The other rotor steps when its right rotor moves from 'turnover' position to the next.

    The middle rotor at the turnover position takes the double-step.
    The rotor moves like this: KDO, KDP, KDQ, KER, LFS, LFT, LFU (turnover is V-E-Q)
    """
    next_rotor_position_right = (rotor_position_right+1) % 26

    if rotor_position_right in turnover_right:
        next_rotor_position_mid = (rotor_position_mid+1) % 26
    elif rotor_position_mid in turnover_mid:
        # double step
        next_rotor_position_mid = (rotor_position_mid+1) % 26
    else:
        next_rotor_position_mid = rotor_position_mid

    if rotor_position_mid in turnover_mid:
        next_rotor_position_left = (rotor_position_left+1) % 26
    else:
        next_rotor_position_left = rotor_position_left

    return next_rotor_position_left, next_rotor_position_mid, next_rotor_position_right


def unit_rotor_conversion(level, rotor_wiring, rotor_position, ring_position, direction, ring):
    """
    If the rotor position is 0, level=t indicates the rotor's t-th letter.
    If the rotor position is n, level=t indicates the rotor's (t+n)-th letter.

    The ring position shift the rotor input/output.

    (forward)
    level = input
    rotor input = level - ring position + rotor position
    rotor output = wire's rotor input position
    ring output = rotor output + ring position - rotor position

    Both the input and output are integers between 0-25. (Not the letter)
    """
    if direction == 'forward':
        rotor_input = (level - ring_position + rotor_position) % 26
        rotor_output_letter = rotor_wiring[rotor_input]
        rotor_output = ring.find(rotor_output_letter)
        ring_output = (rotor_output + ring_position - rotor_position) % 26
        return ring_output
    elif direction == 'backward':
        ring_input = level
        ring_output = (ring_input - ring_position + rotor_position) % 26
        ring_output_letter = ring[ring_output]
        rotor_output = rotor_wiring.find(ring_output_letter)
        output = (rotor_output + ring_position - rotor_position) % 26
        return output


def reflector_forward(level, reflector):
    return abc.find(reflector[level])


def reflector_backward(level, reflector):
    return reflector.find(abc[level])


def enigma_custom(text, rotor_left, rotor_mid, rotor_right, reflector,
                  rotor_key, ringsetting_key, plugboard,
                  ring=standard_ring, mode='encode', rotor_fourth=None):
    """
    Cipher stream for encoding:
    Input -> Plugboard -> Right rotor -> Middle rotor -> Left rotor -> Reflector 
    -> Left rotor (reverse) -> Middle rotor (reverse) -> Right rotor (reverse)
    -> Plugboard -> Output

    If the reflector configuration is reversible, the decoding result is the same as the encoding. 

    Keys are ordered left-to-right. For M4 this is
    Greek-Left-Middle-Right; the Greek rotor never advances.
    """

    text = text.upper()

    required_key_length = 4 if rotor_fourth else 3
    if len(rotor_key) != required_key_length:
        raise ValueError(f'rotor_key must contain {required_key_length} letters')
    if len(ringsetting_key) != required_key_length:
        raise ValueError(
            f'ringsetting_key must contain {required_key_length} letters')

    moving_key = rotor_key[-3:]
    moving_ring_key = ringsetting_key[-3:]
    rotor_position_left = abc.find(moving_key[0])
    rotor_position_mid = abc.find(moving_key[1])
    rotor_position_right = abc.find(moving_key[2])
    ring_position_left = abc.find(moving_ring_key[0])
    ring_position_mid = abc.find(moving_ring_key[1])
    ring_position_right = abc.find(moving_ring_key[2])
    turnover_left = [abc.find(t) for t in rotor_left['turnover']]
    turnover_mid = [abc.find(t) for t in rotor_mid['turnover']]
    turnover_right = [abc.find(t) for t in rotor_right['turnover']]

    for plug in plugboard:
        text = swap(text, plug)

    result = ''

    for s in text:
        if ord(s) < ord('A') or ord('Z') < ord(s):
            result += s
        else:
            rotor_position_left, rotor_position_mid, rotor_position_right = setp_rotor_positions(
                rotor_position_left, rotor_position_mid, rotor_position_right, turnover_left, turnover_mid, turnover_right)

            level = abc.find(s)
            level = unit_rotor_conversion(
                level=level,
                rotor_wiring=rotor_right['wiring'],
                rotor_position=rotor_position_right,
                ring_position=ring_position_right,
                direction='forward',
                ring=ring)
            level = unit_rotor_conversion(
                level=level,
                rotor_wiring=rotor_mid['wiring'],
                rotor_position=rotor_position_mid,
                ring_position=ring_position_mid,
                direction='forward',
                ring=ring)
            level = unit_rotor_conversion(
                level=level,
                rotor_wiring=rotor_left['wiring'],
                rotor_position=rotor_position_left,
                ring_position=ring_position_left,
                direction='forward',
                ring=ring)

            if rotor_fourth:
                level = unit_rotor_conversion(
                    level=level,
                    rotor_wiring=rotor_fourth['wiring'],
                    rotor_position=abc.find(rotor_key[0]),
                    ring_position=abc.find(ringsetting_key[0]),
                    direction='forward',
                    ring=ring)

            if mode == 'encode':
                level = reflector_forward(level, reflector)
            elif mode == 'decode':
                level = reflector_backward(level, reflector)
            else:
                return 'No reflector'

            if rotor_fourth:
                level = unit_rotor_conversion(
                    level=level,
                    rotor_wiring=rotor_fourth['wiring'],
                    rotor_position=abc.find(rotor_key[0]),
                    ring_position=abc.find(ringsetting_key[0]),
                    direction='backward',
                    ring=ring)

            level = unit_rotor_conversion(
                level=level,
                rotor_wiring=rotor_left['wiring'],
                rotor_position=rotor_position_left,
                ring_position=ring_position_left,
                direction='backward',
                ring=ring)
            level = unit_rotor_conversion(
                level=level,
                rotor_wiring=rotor_mid['wiring'],
                rotor_position=rotor_position_mid,
                ring_position=ring_position_mid,
                direction='backward',
                ring=ring)
            level = unit_rotor_conversion(
                level=level,
                rotor_wiring=rotor_right['wiring'],
                rotor_position=rotor_position_right,
                ring_position=ring_position_right,
                direction='backward',
                ring=ring)

            result += abc[level]

    for plug in plugboard:
        result = swap(result, plug)

    return result


def enigma(text, rotor_left_id, rotor_mid_id, rotor_right_id, reflector_id,
           rotor_key, ringsetting_key, plugboard, fourth_rotor_id=None):
    """Simulate an Enigma I/M3, or an M4 when ``fourth_rotor_id`` is set.

    Rotor and ring keys are ordered from left to right. M4 keys therefore
    contain four letters (Greek, left, middle, right); only the rightmost
    three rotors advance.
    """
    rotor_left = rotors[rotor_left_id]
    rotor_mid = rotors[rotor_mid_id]
    rotor_right = rotors[rotor_right_id]

    rotor_fourth = None
    if fourth_rotor_id:
        rotor_fourth = fourth_rotors[str(fourth_rotor_id).upper()]
        reflector = thin_reflectors[reflector_id]
    else:
        reflector = reflectors[reflector_id]

    return enigma_custom(
        text, rotor_left, rotor_mid, rotor_right, reflector,
        rotor_key, ringsetting_key, plugboard,
        ring=standard_ring, mode='decode', rotor_fourth=rotor_fourth)


def plugboard_gen(txt):
    import re
    txt = re.sub(r"[^a-zA-Z_]", "", txt).upper()

    unique_txt = ""
    already_appeared = []
    for s in txt:
        if not s in already_appeared:
            unique_txt += s
            already_appeared.append(s)

    result = []

    even_flag = True
    for s in unique_txt:
        even_flag = not even_flag
        if even_flag:
            result.append(w+s)
        else:
            w = s

    return result
