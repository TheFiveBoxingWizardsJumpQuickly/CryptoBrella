import re
from app.cipher.fn import *


def gear_globals():
    return globals()


def play_ground(request):
    input_text = request.json['input_text']

    results = {}
    results[0] = \
        input_text + '\n' +\
        input_text
    return results


def rot_gen(request):
    input_text = request.json['input_text']

    results = {}
    results[0] = '\n'.join(str(i).zfill(2) + ': ' +
                           rot(input_text, i) for i in range(26))
    return results


def vigenere_gen(request):
    input_text = request.json['input_text']
    key = request.json['key']
    results = {}

    results[0] = \
        'Text: ' + input_text + '\n' +\
        'Key: ' + key + '\n' +\
        'Decoded: ' + vig_d(input_text, key) + '\n' +\
        'Encoded: ' + vig_e(input_text, key) + '\n' +\
        'Beaufort: ' + beaufort(input_text, key) + '\n' +\
        'Auto key Decoded: ' + vig_d_auto(input_text, key) + '\n' +\
        'Auto key Encoded: ' + vig_e_auto(input_text, key)
    return results


def enigma_gen(request):
    input_text = request.json['input_text']
    left_rotor = request.json['left_rotor']
    mid_rotor = request.json['mid_rotor']
    right_rotor = request.json['right_rotor']
    reflector = request.json['reflector']
    rotor_key = request.json['rotor_key']
    ring_key = request.json['ring_key']
    plug_board = request.json['plug_board']

    input_text = input_text.upper()
    rotor_key = re.sub(r"[^a-zA-Z]", "", rotor_key).upper().ljust(3, 'A')
    ring_key = re.sub(r"[^a-zA-Z]", "", ring_key).upper().ljust(3, 'A')
    plug_board = plugboard_gen(plug_board)

    results = {}
    results[0] = \
        'Text: ' + input_text + '\n' +\
        'Rotor Set: ' + left_rotor + ' ' + mid_rotor + ' ' + right_rotor + '\n' +\
        'Reflector: ' + reflector + '\n' +\
        'Rotator key: ' + rotor_key + '\n' +\
        'Ring Setting Key: ' + ring_key + '\n' +\
        'Plug Board: ' + ','.join(plug_board) + '\n'

    results[1] = \
        '------' + '\n' +\
        'Enigma output: ' + enigma(text=input_text,
                                   rotor_left_id=int(left_rotor),
                                   rotor_mid_id=int(mid_rotor),
                                   rotor_right_id=int(right_rotor),
                                   reflector_id=reflector,
                                   rotor_key=rotor_key,
                                   ringsetting_key=ring_key,
                                   plugboard=plug_board) + '\n'
    return results


def purple_gen(request):
    input_text = request.json['input_text']
    sixes_switch_position = int(request.json['sixes_switch_position'])
    twenties_switch_1_position = int(
        request.json['twenties_switch_1_position'])
    twenties_switch_2_position = int(
        request.json['twenties_switch_2_position'])
    twenties_switch_3_position = int(
        request.json['twenties_switch_3_position'])
    plugboard_full = request.json['plugboard_full']
    rotor_motion_key = int(request.json['rotor_motion_key'])

    input_text = input_text.upper()
    plugboard_full = re.sub(
        r"[^a-zA-Z]", "", plugboard_full).upper()

    results = {}
    results[0] = \
        'Text: ' + input_text + '\n'
    'Rotor Position: SIXes= ' + str(sixes_switch_position) + \
        ' TWENTIES_1= ' + str(twenties_switch_1_position) + \
        ' TWENTIES_2= ' + str(twenties_switch_2_position) + \
        ' TWENTIES_3= ' + str(twenties_switch_3_position)+'\n' + \
        'Motion: ' + str(rotor_motion_key)+'\n' + \
        'Plug Board: ' + plugboard_full+'\n'

    results[1] = \
        '------'+'\n' + \
        'PURPLE Decode: ' + purple_decode(text=input_text,
                                          sixes_switch_position=sixes_switch_position,
                                          twenties_switch_1_position=twenties_switch_1_position,
                                          twenties_switch_2_position=twenties_switch_2_position,
                                          twenties_switch_3_position=twenties_switch_3_position,
                                          plugboard_full=plugboard_full,
                                          rotor_motion_key=rotor_motion_key
                                          )+'\n' + \
        '------'+'\n' + \
        'PURPLE Encode: ' + purple_encode(text=input_text,
                                          sixes_switch_position=sixes_switch_position,
                                          twenties_switch_1_position=twenties_switch_1_position,
                                          twenties_switch_2_position=twenties_switch_2_position,
                                          twenties_switch_3_position=twenties_switch_3_position,
                                          plugboard_full=plugboard_full,
                                          rotor_motion_key=rotor_motion_key
                                          )+'\n'
    return results


def prime_gen(request):
    input_text = request.json['input_text']

    factor, notation = factorize(extract_integer_only(input_text))
    results = {}
    results[0] = factor + '\n' + notation
    return results


def pwgen_gen(request):
    char_type = request.json['char_type']
    length = request.json['length']

    list_symbol = '!@#$%^&'

    map = {
        '0': list_A + list_a + list_0,
        '1': list_A + list_a + list_0 + list_symbol,
        '2': list_A + list_a,
        '3': list_A,
        '4': list_a,
        '5': list_0,
        '6': list_A + list_a + list_symbol,
        '7': list_A + list_0,
        '8': list_a + list_0
    }
    table = map.get(char_type)

    results = {}
    results[0] = password_generate(int(length), table)
    return results


def charcode_gen(request):
    input_text = request.json['input_text']
    base = int(request.json['base'])
    mode = request.json['mode']

    results = {}
    if base < 2 or 36 < base:
        results[0] = 'Number base should be between 2-36.'
    else:
        if mode == 'Char to Codepoint':
            results[0] = 'Unicode: ' + \
                ' '.join([base_a_to_base_b_onenumber(ord(char), 10, base)
                          for char in input_text])
            results[1] = 'UTF-8: ' + \
                ' '.join([char_to_codepoint(char, codec='utf_8', base=base)
                          for char in input_text])
            results[2] = 'Shift JIS: ' + \
                ' '.join([char_to_codepoint(char, codec='shift_jis', base=base)
                          for char in input_text])
            results[3] = 'EUC JP: ' +\
                ' '.join([char_to_codepoint(char, codec='euc_jp', base=base)
                          for char in input_text])
            results[4] = 'ISO-2022-JP: ' +\
                ' '.join([char_to_codepoint(char, codec='iso2022_jp', base=base)
                          for char in input_text])
        elif mode == 'Codepoint to Char':
            valid_chars = set(' ' + valid_chars_for_base_n(base))
            if not all(c in valid_chars for c in input_text):
                results[0] = 'Input contains invalid characters for base ' + \
                    str(base)
            else:
                code_points = list(
                    filter(lambda x: len(x) > 0, input_text.split(' ')))
                results[0] = 'Unicode: ' + \
                    ''.join([chr(int(base_a_to_base_b_onenumber(code_point, base, 10)))
                            for code_point in code_points])
                results[1] = 'UTF-8: ' + \
                    ''.join([codepoint_to_char(code_point, codec='utf_8', base=base)
                            for code_point in code_points])
                results[2] = 'Shift JIS: ' + \
                    ''.join([codepoint_to_char(code_point, codec='shift_jis', base=base)
                            for code_point in code_points])
                results[3] = 'EUC JP: ' +\
                    ''.join([codepoint_to_char(code_point, codec='euc_jp', base=base)
                            for code_point in code_points])
                results[4] = 'ISO-2022-JP: ' +\
                    ''.join([codepoint_to_char(code_point, codec='iso2022_jp', base=base)
                            for code_point in code_points])

    return results


def base64_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    results = {}
    if mode == 'Decode':
        # Base32 block
        results[0] = '---Base32---'
        input_text_formatted = input_text.upper()
        input_text_formatted = input_text_formatted + \
            "="*(-len(input_text_formatted) % 8)
        try:
            results[1] = 'decoded: ' + \
                base64.b32decode(input_text_formatted).decode()
        except:
            results[1] = '# input was not interpreted as Base32 encoding.'

        results[2] = '\n'

        # Base64 block
        results[10] = '---Base64---'
        input_text_formatted = input_text + "="*(-len(input_text) % 4)
        try:
            results[11] = 'decoded: ' + \
                base64.b64decode(
                    input_text_formatted, validate=True).decode()
        except:
            results[11] = '# input was not interpreted as Base64 encoding.'
        results[12] = '\n'

        # UUencoding block
        results[20] = '---UUencode---'
        input_text_formatted = input_text + " "*(-len(input_text) % 4)
        try:
            results[21] = 'decoded: ' + \
                uu_decode(input_text_formatted).decode()
        except:
            results[21] = '# input was not interpreted as UU encoding.'
        results[22] = '\n'

        # ASCII85 block
        results[30] = '---ASCII85---'
        input_text_formatted = input_text
        try:
            results[31] = 'decoded: ' + \
                base64.a85decode(input_text_formatted).decode()
        except:
            results[31] = '# input was not interpreted as ASCII85 encoding.'
        results[32] = '\n'

        # Base85 block
        results[40] = '---Base85---'
        input_text_formatted = input_text
        try:
            results[41] = 'decoded: ' + \
                base64.b85decode(input_text_formatted).decode()
        except:
            results[41] = '# input was not interpreted as BASE85 encoding.'
        results[42] = '\n'

    elif mode == 'Encode':
        results[0] = \
            'Base32:' + '\n' + \
            str(base64.b32encode(input_text.encode()))[2:-1] + '\n' + \
            '\n' + \
            'Base64:' + '\n' + \
            str(base64.b64encode(input_text.encode()))[2:-1] + '\n' + \
            '\n' + \
            'UUencode:' + '\n' + \
            str(uu_encode(input_text.encode()))[2:-1] + '\n' + \
            '\n' + \
            'ASCII85:' + '\n' + \
            str(base64.a85encode(input_text.encode()))[2:-1] + '\n' + \
            '\n' + \
            'Base85:' + '\n' + \
            str(base64.b85encode(input_text.encode()))[2:-1] + '\n'

    return results


def rectangle_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    results = {}

    t = 0

    results[t] = 'Text length = ' + str(len(input_text))
    t += 1
    for i in range(2, math.ceil(len(input_text)/2)+1):
        if len(input_text) % i == 0 or mode == 'All pattern':
            rectangle_i = rect(input_text, i)

            results[t] = '-----'
            t += 1

            results[t] = 'Column count = ' + str(i)
            t += 1
            for r in range(len(rectangle_i)):
                results[t] = rectangle_i[r]
                t += 1

    return results


def simplesub_gen(request):
    input_text = request.json['input_text']

    results = {}

    t = 0
    menus = [
        'A-a swap',
        'Atbash',
        'Morse .- swap',
        'Morse reverse',
        'Morse .- swap and reverse',
        'US keyboard left shift',
        'US keyboard right shift',
        'US keyboard right <-> left',
        'US keyboard up <-> down',
        'US keyboard to Dvorak keyboard',
        'Dvorak keyboard to US keyboard',
        'US keyboard to MALTRON keyboard',
        'MALTRON keyboard to US keyboard']

    for menu in menus:
        results[t] = menu + ': ' + \
            table_subtitution(input_text, menu)
        t += 1

    return results


def frequency_gen(request):
    input_text = request.json['input_text']
    input_text = input_text.replace('\n', '')

    results = {}

    total_letter_count = len(input_text)
    results[0] = \
        'Text length = ' + str(total_letter_count) + '\n' +\
        'Used characters (unique) = ' + \
        unique(input_text, sort=True) + '\n' +\
        '-----' + '\n'

    results[1] = 'Letter frequency(Sorted Alphabetically)' + '\n'
    freq = letter_frequency(input_text, 0, False)
    for i in freq:
        results[1] += i[0] + ': ' + str(i[1]) + ' (' '{percent:.2%}'.format(
            percent=i[1]/total_letter_count) + ')' + '\n'

    results[1] += '-----' + '\n'

    results[2] = 'Letter frequency (Sorted by Frequency)' + '\n'
    freq = letter_frequency(input_text, 1, True)
    for i in freq:
        results[2] += i[0] + ': ' + str(i[1]) + ' (' '{percent:.2%}'.format(
            percent=i[1]/total_letter_count) + ')' + '\n'

    return results


def subs_handsolve_gen(request):
    input_text = request.json['input_text']
    subs_from = request.json['subs_from']
    subs_to = request.json['subs_to']

    results = {}
    text_from = unique(subs_from)
    text_to = subs_to
    text_length = min(len(text_from), len(text_to))
    text_del = text_from[text_length:]
    text_from = text_from[:text_length]
    text_to = text_to[:text_length]
    map_dict = dict(zip(text_from, text_to))

    input_text_working = input_text
    for i in text_del:
        input_text_working = input_text_working.replace(i, '')

    results[0] = \
        'Replace characters' + '\n' +\
        '_del: ' + text_del.upper()+'\n' +\
        'from: ' + text_from.upper()+'\n' +\
        '__to: ' + text_to.upper()+'\n' +\
        '-----'+'\n' +\
        '[Before]'+'\n' +\
        input_text+'\n' +\
        '\n' +\
        '[After]'+'\n' +\
        replace_all_case_insensitive(
            input_text_working, text_from, text_to)+'\n' +\
        '\n'

    results[1] = \
        '-----'+'\n' +\
        'Letter frequency'+'\n'

    analysys_text = re.sub(r"[^A-Z]", "", input_text.upper())
    total_letter_count = len(analysys_text)
    freq = letter_frequency(analysys_text, 1, True)
    for i in range(len(freq)):
        results[1] += freq[i][0] + ': ' + \
            '{percent:.2%}'.format(
                percent=freq[i][1]/total_letter_count)
        if i % 9 == 8:
            results[1] += '\n'
        else:
            results[1] += ', '

    results[2] = \
        '-----'+'\n' +\
        'Bigram frequency'+'\n'

    analysys_text = re.sub(r"[^A-Z ]", "", input_text.upper())
    total_bigram_count = len(analysys_text) - 1
    freq = bigram_frequency(analysys_text)

    for i in range(min(len(freq), 18)):
        results[2] += freq[i][0] + ': ' + \
            '{percent:.2%}'.format(
                percent=freq[i][1]/total_bigram_count)
        if i % 9 == 8:
            results[2] += '\n'
        else:
            results[2] += ', '
    results[2] += '\n'

    results[3] = \
        '-----' + '\n' +\
        'Basic English info.' + '\n' +\
        'Letter frequency' + '\n' +\
        'E: 12.49%, T: 9.28%, A: 8.04%, O: 7.64%, I: 7.57%, N: 7.23%, S: 6.51%, R: 6.28%, H: 5.05%' + '\n' +\
        'L: 4.07%, D: 3.82%, C: 3.34%, U: 2.73%, M: 2.51%, F: 2.40%, P: 2.14%, G: 1.87%, W: 1.68%' + '\n' +\
        'Y: 1.66%, B: 1.48%, V: 1.05%, K: 0.54%, X: 0.23%, J: 0.16%, Q: 0.12%, Z: 0.09%' + '\n' +\
        '\n' +\
        'Bigram frequency' + '\n' +\
        'TH: 3.56%, HE: 3.07%, IN: 2.43%, ER: 2.05%, AN: 1.99%, RE: 1.85%, ON: 1.76%, AT: 1.49%, EN: 1.45%' + '\n' +\
        'ND: 1.35%, TI: 1.34%, ES: 1.34%, OR: 1.28%, TE: 1.20%, OF: 1.17%, ED: 1.17%, IS: 1.13%, IT: 1.12%' + '\n' +\
        ' ' + '\n' +\
        '* This is based on below site\'s great work. ' + '\n' +\
        'https://norvig.com/mayzner.html' + '\n'

    return results


def railfence_gen(request):
    input_text = request.json['input_text']
    offset = request.json['offset']
    if offset == '':
        offset = 0
    else:
        offset = int(offset)

    results = {}

    results[0] =\
        'Offset = ' + str(offset) + '\n' +\
        'rails:' + '\n'

    for i in range(2, len(input_text)):
        results[0] += str(i).zfill(3) + ': ' +\
            railfence_d(input_text, i, offset) + '\n'

    return results


def morse_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    results = {}

    if mode == 'Decode':
        results[0] =\
            'Morse Decode:' + '\n' +\
            morse_d(input_text) + '\n' +\
            '\n' +\
            'Wabun Morse Decode:' + '\n' +\
            morse_wabun_d(input_text) + '\n'
    elif mode == 'Encode':
        results[0] =\
            'Morse Decode:' + '\n' +\
            morse_e(input_text) + '\n' +\
            '\n' +\
            'Wabun Morse Decode:' + '\n' +\
            morse_wabun_e(input_text) + '\n'

    return results


def charreplace_gen(request):
    input_text = request.json['input_text']
    replace_from = request.json['replace_from']
    replace_to = request.json['replace_to']

    results = {}

    replace_from = unique(replace_from)
    text_length = min(len(replace_from), len(replace_to))
    text_del = replace_from[text_length:]
    replace_from = replace_from[:text_length]
    replace_to = replace_to[:text_length]
    map_dict = dict(zip(replace_from, replace_to))

    for i in text_del:
        input_text = input_text.replace(i, '')

    results[0] = \
        'Replace characters' + '\n' +\
        ' del: ' + text_del + '\n' +\
        'from: ' + replace_from + '\n' +\
        '  to: ' + replace_to + '\n' +\
        '\n' +\
        replace_all(input_text, replace_from, replace_to)

    return results


def reverse_gen(request):
    input_text = request.json['input_text']

    results = {}
    results[0] = rev(input_text)
    return results


def columnar_gen(request):
    input_text = request.json['input_text']
    key = request.json['key']

    results = {}
    results[0] =\
        'Columnar decode with key: ' + key + '\n' +\
        ''.join(columnar_d(input_text, assign_digits(key)))+'\n' +\
        '\n' +\
        'Columnar encode with key: ' + key+'\n' +\
        ''.join(columnar_e(input_text, assign_digits(key)))

    return results


def hash_gen(request):
    input_text = request.json['input_text']

    results = {}
    results[0] = \
        'MD5    : ' + \
        hashlib.md5(input_text.encode()).hexdigest()+'\n' +\
        'SHA1   : ' + \
        hashlib.sha1(input_text.encode()).hexdigest()+'\n' +\
        'SHA224 : ' + \
        hashlib.sha224(input_text.encode()).hexdigest() + '\n' +\
        'SHA256 : ' + \
        hashlib.sha256(input_text.encode()).hexdigest() + '\n' +\
        'SHA384 : ' + \
        hashlib.sha384(input_text.encode()).hexdigest() + '\n' +\
        'SHA512 : ' + \
        hashlib.sha512(input_text.encode()).hexdigest() + '\n' +\
        'BLAKE2b: ' + \
        hashlib.blake2b(input_text.encode()).hexdigest() + '\n' +\
        'BLAKE2s: ' + \
        hashlib.blake2s(input_text.encode()).hexdigest()

    return results