SIXES = '_AEIOUY'
TWENTIES = '_BCDFGHJKLMNPQRSTVWXZ'

SIXES_SWITCH = [
    0,
    [0, 2, 1, 3, 5, 4, 6],
    [0, 6, 3, 5, 2, 1, 4],
    [0, 1, 5, 4, 6, 2, 3],
    [0, 4, 3, 2, 1, 6, 5],
    [0, 3, 6, 1, 4, 5, 2],
    [0, 2, 1, 6, 5, 3, 4],
    [0, 6, 5, 4, 2, 1, 3],
    [0, 3, 6, 1, 4, 5, 2],
    [0, 5, 4, 2, 6, 3, 1],
    [0, 4, 5, 3, 2, 1, 6],
    [0, 2, 1, 4, 5, 6, 3],
    [0, 5, 4, 6, 3, 2, 1],
    [0, 3, 1, 2, 6, 4, 5],
    [0, 4, 2, 5, 1, 3, 6],
    [0, 1, 6, 2, 3, 5, 4],
    [0, 5, 4, 3, 6, 1, 2],
    [0, 6, 2, 5, 3, 4, 1],
    [0, 2, 3, 4, 1, 5, 6],
    [0, 1, 2, 3, 5, 6, 4],
    [0, 3, 1, 6, 4, 2, 5],
    [0, 6, 5, 1, 2, 4, 3],
    [0, 1, 3, 6, 4, 2, 5],
    [0, 6, 4, 5, 1, 3, 2],
    [0, 4, 6, 1, 2, 5, 3],
    [0, 5, 2, 4, 3, 6, 1],
]

TWENTIES_SWITCH_1 = [
    0,
    [0, 6, 19, 14, 1, 10, 4, 2, 7, 13, 9, 8, 16, 3, 18, 15, 11, 5, 12, 20, 17],
    [0, 4, 5, 16, 17, 14, 1, 20, 15, 3, 8, 18, 11, 12, 13, 10, 19, 2, 6, 9, 7],
    [0, 17, 1, 13, 6, 15, 11, 19, 12, 16, 18, 10, 3, 7, 14, 8, 20, 4, 9, 2, 5],
    [0, 3, 14, 20, 4, 6, 16, 8, 19, 2, 12, 17, 9, 5, 1, 11, 10, 7, 13, 15, 18],
    [0, 19, 6, 8, 20, 13, 5, 18, 4, 10, 3, 16, 15, 14, 12, 7, 2, 17, 11, 1, 9],
    [0, 2, 11, 9, 14, 7, 19, 6, 3, 18, 13, 12, 8, 10, 15, 16, 17, 20, 4, 5, 1],
    [0, 16, 7, 6, 18, 9, 10, 13, 1, 17, 2, 5, 4, 11, 19, 20, 14, 8, 15, 3, 12],
    [0, 1, 20, 7, 16, 12, 14, 5, 18, 15, 10, 13, 6, 8, 3, 4, 9, 11, 17, 19, 2],
    [0, 17, 9, 11, 8, 20, 18, 7, 14, 1, 16, 15, 5, 19, 2, 6, 12, 4, 10, 13, 3],
    [0, 12, 8, 17, 9, 3, 20, 4, 10, 14, 5, 7, 18, 2, 16, 13, 6, 1, 19, 15, 11],
    [0, 20, 1, 16, 11, 2, 17, 9, 4, 8, 15, 10, 13, 3, 18, 14, 5, 6, 7, 12, 19],
    [0, 5, 4, 15, 2, 13, 19, 6, 16, 12, 14, 8, 7, 17, 10, 18, 3, 9, 1, 11, 20],
    [0, 15, 17, 10, 19, 16, 2, 11, 8, 9, 7, 3, 14, 18, 13, 12, 1, 5, 20, 6, 4],
    [0, 11, 12, 7, 3, 8, 15, 16, 6, 4, 20, 2, 5, 1, 9, 19, 18, 10, 14, 17, 13],
    [0, 12, 16, 2, 7, 4, 8, 15, 19, 5, 1, 11, 9, 20, 17, 6, 14, 13, 3, 18, 10],
    [0, 8, 15, 18, 1, 12, 11, 17, 14, 20, 16, 13, 19, 9, 7, 3, 4, 2, 5, 10, 6],
    [0, 7, 3, 5, 18, 17, 13, 19, 20, 14, 11, 9, 10, 2, 6, 1, 15, 12, 16, 4, 8],
    [0, 10, 13, 4, 14, 18, 3, 2, 17, 11, 19, 20, 1, 6, 12, 9, 7, 15, 8, 5, 16],
    [0, 13, 7, 9, 12, 20, 16, 14, 10, 19, 6, 1, 2, 11, 4, 5, 3, 18, 17, 8, 15],
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
    [0, 9, 20, 12, 5, 10, 17, 1, 13, 7, 15, 4, 3, 16, 8, 18, 11, 19, 2, 14, 6],
    [0, 18, 15, 2, 13, 1, 7, 10, 5, 19, 17, 6, 20, 9, 11, 12, 8, 3, 4, 16, 14],
    [0, 16, 18, 19, 10, 11, 20, 5, 9, 1, 4, 12, 13, 7, 6, 17, 2, 14, 15, 3, 8],
    [0, 5, 8, 1, 15, 19, 9, 12, 2, 6, 3, 14, 17, 4, 20, 16, 13, 18, 10, 7, 11],
    [0, 14, 10, 4, 8, 9, 12, 3, 11, 17, 20, 19, 6, 15, 5, 2, 18, 16, 7, 1, 13],
]

TWENTIES_SWITCH_2 = [
    0,
    [0, 15, 9, 1, 5, 17, 19, 3, 2, 10, 8, 11, 18, 12, 16, 6, 13, 20, 4, 14, 7],
    [0, 12, 6, 15, 2, 4, 9, 8, 16, 19, 17, 5, 11, 20, 7, 10, 18, 1, 14, 13, 3],
    [0, 4, 18, 5, 8, 16, 1, 12, 15, 20, 14, 13, 17, 11, 2, 7, 9, 6, 3, 10, 19],
    [0, 6, 11, 2, 20, 14, 7, 18, 12, 15, 3, 8, 5, 10, 1, 17, 19, 9, 16, 4, 13],
    [0, 7, 2, 13, 3, 9, 4, 17, 14, 1, 12, 18, 20, 6, 11, 16, 15, 5, 8, 19, 10],
    [0, 5, 17, 14, 7, 10, 9, 19, 20, 8, 13, 1, 2, 16, 3, 4, 12, 11, 18, 6, 15],
    [0, 8, 4, 3, 11, 19, 13, 2, 9, 12, 16, 10, 17, 14, 15, 20, 6, 18, 1, 7, 5],
    [0, 20, 1, 16, 10, 15, 8, 14, 11, 18, 5, 3, 7, 13, 17, 19, 4, 2, 9, 12, 6],
    [0, 9, 8, 7, 15, 5, 2, 4, 13, 17, 1, 11, 6, 19, 18, 14, 10, 3, 20, 16, 12],
    [0, 10, 12, 11, 18, 8, 16, 20, 17, 5, 6, 9, 3, 4, 19, 13, 7, 1, 14, 15, 2],
    [0, 11, 7, 14, 4, 18, 20, 6, 1, 13, 19, 12, 15, 5, 9, 16, 2, 17, 10, 8, 3],
    [0, 2, 3, 9, 10, 13, 14, 15, 16, 7, 11, 20, 12, 18, 6, 1, 5, 8, 17, 19, 4],
    [0, 16, 10, 15, 1, 17, 3, 13, 9, 4, 7, 6, 8, 2, 14, 5, 11, 12, 19, 18, 20],
    [0, 19, 16, 18, 12, 3, 13, 9, 10, 6, 2, 17, 14, 11, 4, 7, 20, 15, 5, 1, 8],
    [0, 18, 14, 12, 19, 1, 7, 10, 6, 11, 15, 5, 9, 8, 20, 17, 4, 3, 13, 2, 16],
    [0, 20, 3, 19, 2, 4, 5, 11, 14, 9, 10, 18, 16, 15, 12, 8, 7, 13, 6, 17, 1],
    [0, 3, 6, 4, 14, 2, 12, 16, 5, 18, 20, 7, 19, 1, 15, 9, 8, 10, 11, 13, 17],
    [0, 5, 15, 20, 9, 10, 17, 1, 19, 13, 12, 4, 2, 7, 6, 11, 14, 16, 8, 3, 18],
    [0, 14, 20, 13, 17, 5, 18, 8, 4, 2, 15, 16, 1, 9, 19, 3, 6, 7, 10, 12, 11],
    [0, 8, 11, 1, 6, 19, 14, 5, 18, 17, 3, 10, 13, 12, 20, 15, 16, 4, 2, 7, 9],
    [0, 17, 19, 6, 1, 12, 15, 20, 7, 16, 9, 3, 11, 13, 10, 2, 18, 8, 4, 5, 14],
    [0, 1, 5, 12, 20, 6, 11, 14, 8, 9, 7, 19, 4, 3, 13, 10, 17, 18, 16, 15, 2],
    [0, 16, 8, 10, 13, 11, 6, 19, 5, 3, 4, 15, 20, 17, 2, 18, 1, 14, 7, 9, 12],
    [0, 19, 13, 8, 16, 20, 10, 7, 1, 2, 18, 14, 6, 9, 5, 12, 3, 17, 15, 11, 4],
    [0, 13, 1, 17, 15, 7, 4, 16, 3, 14, 5, 2, 10, 18, 8, 11, 9, 19, 12, 20, 6],
]

TWENTIES_SWITCH_3 = [
    0,
    [0, 7, 19, 11, 3, 20, 1, 10, 6, 16, 12, 17, 13, 8, 9, 4, 18, 5, 14, 15, 2],
    [0, 15, 17, 14, 2, 12, 13, 8, 3, 1, 19, 9, 4, 10, 7, 11, 20, 16, 6, 18, 5],
    [0, 2, 11, 20, 12, 1, 19, 4, 10, 9, 14, 6, 15, 13, 3, 7, 16, 18, 8, 5, 17],
    [0, 16, 3, 12, 9, 4, 20, 6, 19, 18, 2, 5, 8, 14, 11, 10, 1, 15, 17, 13, 7],
    [0, 12, 18, 16, 4, 9, 3, 15, 13, 6, 20, 8, 2, 7, 10, 5, 19, 14, 1, 17, 11],
    [0, 13, 9, 5, 6, 8, 7, 12, 17, 14, 18, 20, 10, 2, 19, 11, 15, 4, 3, 1, 16],
    [0, 4, 7, 2, 15, 17, 10, 19, 5, 8, 16, 1, 12, 3, 13, 6, 14, 20, 9, 11, 18],
    [0, 9, 6, 4, 10, 18, 16, 8, 14, 5, 12, 17, 1, 20, 15, 13, 19, 2, 11, 7, 3],
    [0, 5, 14, 18, 17, 13, 15, 11, 12, 7, 8, 3, 6, 1, 2, 20, 4, 9, 10, 16, 19],
    [0, 11, 16, 9, 18, 3, 12, 5, 15, 10, 1, 14, 17, 2, 4, 19, 6, 8, 7, 13, 20],
    [0, 19, 8, 3, 15, 14, 5, 1, 11, 2, 10, 12, 16, 18, 20, 17, 7, 13, 4, 9, 6],
    [0, 1, 12, 17, 13, 9, 7, 14, 2, 15, 4, 5, 11, 6, 16, 3, 8, 18, 19, 20, 10],
    [0, 3, 4, 10, 12, 1, 18, 2, 8, 14, 13, 19, 7, 16, 6, 15, 9, 17, 20, 5, 11],
    [0, 9, 11, 6, 5, 10, 4, 17, 19, 13, 15, 7, 2, 12, 18, 14, 20, 1, 16, 8, 3],
    [0, 8, 13, 14, 16, 19, 12, 20, 7, 10, 3, 15, 9, 4, 17, 1, 11, 5, 2, 6, 18],
    [0, 18, 16, 15, 4, 2, 17, 13, 12, 6, 11, 20, 19, 14, 5, 9, 1, 8, 7, 3, 10],
    [0, 14, 1, 7, 20, 6, 13, 16, 18, 12, 9, 4, 17, 5, 11, 2, 3, 10, 15, 19, 8],
    [0, 17, 19, 1, 11, 7, 2, 18, 4, 3, 8, 10, 5, 15, 12, 16, 9, 6, 13, 20, 14],
    [0, 10, 15, 2, 14, 11, 6, 7, 1, 16, 20, 13, 3, 9, 8, 18, 17, 19, 5, 12, 4],
    [0, 20, 9, 8, 6, 12, 11, 2, 5, 4, 7, 16, 14, 17, 3, 15, 10, 13, 19, 18, 1],
    [0, 11, 20, 13, 8, 16, 10, 18, 14, 19, 6, 15, 4, 1, 17, 7, 5, 3, 9, 2, 12],
    [0, 16, 5, 10, 19, 4, 18, 15, 17, 1, 3, 2, 20, 11, 6, 8, 13, 7, 12, 14, 9],
    [0, 6, 10, 19, 16, 5, 9, 1, 20, 17, 4, 11, 18, 7, 14, 13, 2, 12, 8, 3, 15],
    [0, 8, 7, 5, 1, 15, 14, 9, 16, 11, 17, 18, 6, 19, 20, 3, 12, 4, 2, 10, 13],
    [0, 13, 2, 17, 7, 14, 8, 3, 9, 20, 5, 16, 10, 6, 1, 12, 15, 11, 18, 4, 19],
]

ROTOR_MOTION = {
    123: ['fast', 'middle', 'slow'],
    132: ['fast', 'slow', 'middle'],
    213: ['middle', 'fast', 'slow'],
    312: ['middle', 'slow', 'fast'],
    231: ['slow', 'fast', 'middle'],
    321: ['slow', 'middle', 'fast']}


def move_switches(sixes_position, fast_position, middle_position, slow_position):
    def rot(position):
        if position == 25:
            return 1
        else:
            return position + 1

    sixes_position_next = rot(sixes_position)

    if sixes_position <= 23:
        fast_position_next = rot(fast_position)
        middle_position_next = middle_position
        slow_position_next = slow_position
    elif sixes_position == 24:
        if middle_position == 25:
            fast_position_next = fast_position
            middle_position_next = middle_position
            slow_position_next = rot(slow_position)
        else:
            fast_position_next = rot(fast_position)
            middle_position_next = middle_position
            slow_position_next = slow_position
    elif sixes_position == 25:
        fast_position_next = fast_position
        middle_position_next = rot(middle_position)
        slow_position_next = slow_position

    return [sixes_position_next, fast_position_next, middle_position_next, slow_position_next]


def translate_switch_position_to_by_motion(position_sixes, position1, position2, position3, rotor_motion):
    positions = [position1, position2, position3]
    fast_position = positions[rotor_motion.index('fast')]
    middle_position = positions[rotor_motion.index('middle')]
    slow_position = positions[rotor_motion.index('slow')]
    return[position_sixes, fast_position, middle_position, slow_position]


def translate_switch_position_to_by_order(position_sixes, fast_position, middle_position, slow_position, rotor_motion):
    names = ['fast', 'middle', 'slow']
    positions = [fast_position, middle_position, slow_position]
    position1 = positions[names.index(rotor_motion[0])]
    position2 = positions[names.index(rotor_motion[1])]
    position3 = positions[names.index(rotor_motion[2])]
    return [position_sixes, position1, position2, position3]


def switch_decode(switch, level):
    return switch[level]


def switch_encode(switch, level):
    return switch.index(level)


def plugboard_level_to_char(plugboard, level):
    return plugboard[level-1]


def plugboard_char_to_level(plugboard, char):
    return plugboard.index(char)+1


def purple_one_char(char, sixes_switch_position, twenties_switch_1_position, twenties_switch_2_position, twenties_switch_3_position, plugboard_full, rotor_motion, mode):
    plugboard_sixes = plugboard_full[0:6]
    plugboard_twenties = plugboard_full[6:26]

    if char in plugboard_sixes:
        plugboard = plugboard_sixes
        wiring = 'sixes'
    else:
        plugboard = plugboard_twenties
        wiring = 'twenties'

    level = plugboard_char_to_level(plugboard, char)

    sixes_switch = SIXES_SWITCH[sixes_switch_position]
    twenties_switch_1 = TWENTIES_SWITCH_1[twenties_switch_1_position]
    twenties_switch_2 = TWENTIES_SWITCH_2[twenties_switch_2_position]
    twenties_switch_3 = TWENTIES_SWITCH_3[twenties_switch_3_position]

    if mode == 'encode':
        if wiring == 'sixes':
            level = switch_encode(switch=sixes_switch, level=level)
        elif wiring == 'twenties':
            level = switch_encode(switch=twenties_switch_1, level=level)
            level = switch_encode(switch=twenties_switch_2, level=level)
            level = switch_encode(switch=twenties_switch_3, level=level)
    elif mode == 'decode':
        if wiring == 'sixes':
            level = switch_decode(switch=sixes_switch, level=level)
        elif wiring == 'twenties':
            level = switch_decode(switch=twenties_switch_3, level=level)
            level = switch_decode(switch=twenties_switch_2, level=level)
            level = switch_decode(switch=twenties_switch_1, level=level)

    char = plugboard_level_to_char(plugboard, level)

    switch_positions_by_order = [sixes_switch_position, twenties_switch_1_position,
                                 twenties_switch_2_position, twenties_switch_3_position]

    switch_positions_by_motion = translate_switch_position_to_by_motion(
        *switch_positions_by_order, rotor_motion)
    switch_positions_by_motion = move_switches(*switch_positions_by_motion)
    switch_positions_by_order = translate_switch_position_to_by_order(
        *switch_positions_by_motion, rotor_motion)
    return {
        'char': char,
        'sixes_switch_position': switch_positions_by_order[0],
        'twenties_switch_1_position': switch_positions_by_order[1],
        'twenties_switch_2_position': switch_positions_by_order[2],
        'twenties_switch_3_position': switch_positions_by_order[3]
    }


def purple_cipher(text, sixes_switch_position, twenties_switch_1_position, twenties_switch_2_position, twenties_switch_3_position, plugboard_full, rotor_motion_key, mode):
    text = text.upper()
    rotor_motion = ROTOR_MOTION[rotor_motion_key]
    result = ''
    for char in text:
        if ord(char) < ord('A') or ord('Z') < ord(char):
            result += char
        else:
            if mode == 'encode':
                buf = purple_one_char(char, sixes_switch_position, twenties_switch_1_position,
                                      twenties_switch_2_position, twenties_switch_3_position, plugboard_full, rotor_motion, 'encode')
            elif mode == 'decode':
                buf = purple_one_char(char, sixes_switch_position, twenties_switch_1_position,
                                      twenties_switch_2_position, twenties_switch_3_position, plugboard_full, rotor_motion, 'decode')
            result += buf['char']
            sixes_switch_position = buf['sixes_switch_position']
            twenties_switch_1_position = buf['twenties_switch_1_position']
            twenties_switch_2_position = buf['twenties_switch_2_position']
            twenties_switch_3_position = buf['twenties_switch_3_position']

    return result


def purple_decode(**kwargs):
    return purple_cipher(**kwargs, mode='decode')


def purple_encode(**kwargs):
    return purple_cipher(**kwargs, mode='encode')
