import re
import html
from math import ceil
from app.cipher.fn import *
from app.cipher.resize import resize_image
from app.secret.apikey import get_w3w_apikey
from app.cipher.ingress_passcode import passcode_get_record_by_id, passcode_validate_answer, passcode_get_reward, passcode_get_today_id, passcode_get_random_id, passcode_get_list, passcode_get_filtered_keywords


def gear_globals():
    return globals()


def rot_gen(request):
    input_text = request.json['input_text']

    results = {}
    results[0] = '\n'.join(str(i).zfill(2) + ': ' +
                           rot(input_text, i) for i in range(26))
    return results


def playfair_gen(request):
    input_text = request.json['input_text']

    results = {}
    results[0] = \
        'Decoded: ' + playfair_d(input_text) + '\n' +\
        'Encoded: ' + playfair_e(input_text)
    return results


def vigenere_gen(request):
    input_text = request.json['input_text']
    key = request.json['key']

    key = re.sub(r"[^a-zA-Z0-9]", "", key)

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
    for i in range(2, ceil(len(input_text)/2)+1):
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
        'MALTRON keyboard to US keyboard',
        '!@#_to_123',
        'ABC to 123',
        'ABC to 012']

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
    mode = request.json['mode']
    offset = request.json['offset']
    if offset == '':
        offset = 0
    else:
        offset = int(offset)

    results = {}

    if mode == 'Decode':
        results[0] =\
            'Offset = ' + str(offset) + '\n' +\
            'rails:' + '\n'

        for i in range(2, min(len(input_text), 100)):
            results[0] += str(i).zfill(2) + ': ' +\
                railfence_d(input_text, i, offset) + '\n'
    elif mode == 'Encode':
        results[0] =\
            'Offset = ' + str(offset) + '\n' +\
            'rails:' + '\n'

        for i in range(2, min(len(input_text), 100)):
            results[0] += str(i).zfill(2) + ': ' +\
                railfence_e(input_text, i, offset) + '\n'

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
            'Morse Encode:' + '\n' +\
            morse_e(input_text) + '\n' +\
            '\n' +\
            'Wabun Morse Encode:' + '\n' +\
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


def to_what3words_gen(request):
    latitude = request.json['latitude']
    longitude = request.json['longitude']
    language = request.json['language']
    apikey = get_w3w_apikey()

    results = {}
    wa = convert_to_3wa(apikey, latitude, longitude, language)
    results[0] = \
        'Language: ' + wa['language'] + '\n' +\
        'Words: ' + wa['words'] + '\n' +\
        'Coordinates: Lat= ' + str(wa['coordinates']['lat']) + ', Lng= ' + str(wa['coordinates']['lng']) + '\n' +\
        'South West: Lat= ' + str(wa['square']['southwest']['lat']) + ', Lng= ' + str(wa['square']['southwest']['lng']) + '\n' +\
        'North East: Lat= ' + str(wa['square']['northeast']['lat']) + \
        ', Lng= ' + str(wa['square']['northeast']['lng']) + '\n' +\
        'Country: ' + wa['country'] + '\n' +\
        'Nearest Place: ' + wa['nearestPlace'] + '\n' +\
        'Map: <a href="' + \
        wa['map'] + '" target="_blank" class="link">' + wa['map'] + '</a>'

    return results


def to_coordinates_gen(request):
    words = request.json['words']
    apikey = get_w3w_apikey()

    results = {}
    wa = convert_to_coordinates(apikey, words)
    if 'format error' in wa:
        results[0] = wa['format error']
    elif 'error' in wa:
        results[0] = words
        results[1] = wa['error']
    else:
        results[0] = \
            'Language: ' + wa['language'] + '\n' +\
            'Words: ' + wa['words'] + '\n' +\
            'Coordinates: Lat= ' + str(wa['coordinates']['lat']) + ', Lng= ' + str(wa['coordinates']['lng']) + '\n' +\
            'South West: Lat= ' + str(wa['square']['southwest']['lat']) + ', Lng= ' + str(wa['square']['southwest']['lng']) + '\n' +\
            'North East: Lat= ' + str(wa['square']['northeast']['lat']) + \
            ', Lng= ' + str(wa['square']['northeast']['lng']) + '\n' +\
            'Country: ' + wa['country'] + '\n' +\
            'Nearest Place: ' + wa['nearestPlace'] + '\n' +\
            'Map: <a href="' + \
            wa['map'] + '" target="_blank" class="link">' + wa['map'] + '</a>'

    return results


def braille_gen(request):
    b1 = '1' if request.json['b1'] else '0'
    b2 = '1' if request.json['b2'] else '0'
    b3 = '1' if request.json['b3'] else '0'
    b4 = '1' if request.json['b4'] else '0'
    b5 = '1' if request.json['b5'] else '0'
    b6 = '1' if request.json['b6'] else '0'

    return braille_d(b1+b2+b3+b4+b5+b6)


def braille_ja_gen(request):
    bl1 = '1' if request.json['bl1'] else '0'
    bl2 = '1' if request.json['bl2'] else '0'
    bl3 = '1' if request.json['bl3'] else '0'
    bl4 = '1' if request.json['bl4'] else '0'
    bl5 = '1' if request.json['bl5'] else '0'
    bl6 = '1' if request.json['bl6'] else '0'
    br1 = '1' if request.json['br1'] else '0'
    br2 = '1' if request.json['br2'] else '0'
    br3 = '1' if request.json['br3'] else '0'
    br4 = '1' if request.json['br4'] else '0'
    br5 = '1' if request.json['br5'] else '0'
    br6 = '1' if request.json['br6'] else '0'

    return braille_ja_d(bl1+bl2+bl3+bl4+bl5+bl6+br1+br2+br3+br4+br5+br6)


def rsa_gen(request):
    def force_int(txt):
        txt_trunc = re.sub(r"[^0-9]", "", txt)

        if txt_trunc == '':
            return 0
        else:
            return int(txt_trunc)

    m = force_int(request.json['m'])
    e = force_int(request.json['e'])
    n = force_int(request.json['n'])
    p = force_int(request.json['p'])
    q = force_int(request.json['q'])

    results = {}
    results[0] = \
        'm = ' + str(m) + '\n' +\
        'e = ' + str(e) + '\n' +\
        'n = ' + str(n) + '\n'

    if m == 0 or e == 0 or n == 0:
        return results

    results[1] = '\n' + 'RSA Encode: ' + str(rsa_encode(m, e, n))
    if p == 0 or q == 0:
        return results

    results[2] = '\n' + \
        'p = ' + str(p) + '\n' +\
        'q = ' + str(q) + '\n' +\
        'check: ' + '\n' +\
        'p*q = ' + str(p*q)+'\n' +\
        'n   = ' + str(n)

    [decode, d] = rsa_decode(m, e, n, p, q)
    if d == 0:
        results[3] = '\n' + 'Modular inverse does not exist'
    else:
        results[3] = '\n' + 'calculated d = ' + \
            str(rsa_decode(m, e, n, p, q)[1])
        results[4] = 'RSA Decode: ' + \
            str(rsa_decode(m, e, n, p, q)[0])

    return results


def affine_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    results = {}

    if mode == 'Decode':
        results[0] = 'Affine Cipher Decode:'
        t = 0
        for i in [1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25]:
            for j in range(26):
                t += 1
                results[t] = 'a=' + str(i).zfill(2) + ', b=' + str(j).zfill(2) + ': ' +\
                    affine_d(input_text, i, j)

    elif mode == 'Encode':
        results[0] = 'Affine Cipher Encode:'
        t = 0
        for i in [1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25]:
            for j in range(26):
                t += 1
                results[t] = 'a=' + str(i).zfill(2) + ', b=' + str(j).zfill(2) + ': ' +\
                    affine_e(input_text, i, j)

    return results


def split_text_gen(request):
    input_text = request.json['input_text']
    length_text = request.json['length']
    mode = request.json['mode']

    if length_text == '':
        length = 0
    else:
        length = int(length_text)

    map = {
        'space': ' ',
        'comma': ',',
        'newline': '\n'
    }
    separater = map.get(mode)

    results = {}

    results[0] = 'split length: ' + str(length)
    results[1] = text_split(input_text, length, separater)

    return results


def number_conv_gen(request):
    input_text = request.json['input_text']
    base = request.json['base']

    if base == '':
        base = 10
    else:
        base = int(base)

    input_text = input_text.replace(' ', ',')
    input_text = re.sub(r"[^a-zA-Z0-9,]", "", input_text).upper()
    nlist = input_text.split(',')
    nlist = [a for a in nlist if a != '']

    results = {}

    results[0] = 'Converting ' + ','.join(nlist)
    results[1] = 'from base: ' + str(base)

    t = 2
    for i in range(2, 37):
        results[t] = 'to base ' + str(i).zfill(2) + ': ' +\
            ','.join(base_a_to_base_b(nlist, base, i))
        t += 1

    return results


def phonetic_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    tables = {
        '#International Radiotelephony Spelling Alphabet (NATO phonetic alphabet)': spelling_alphabet_icao_2008,
        '#1951 ICAO code words': spelling_alphabet_icao_1951,
        '#1949 ICAO code words': spelling_alphabet_icao_1949,
        '#1947 ICAO Latin America/Caribbean': spelling_alphabet_icao_1947_1,
        '#1947 ICAO alphabet': spelling_alphabet_icao_1947_2
    }
    input_text_lower = input_text.lower()

    results = {}

    if mode == 'Decode':
        results[0] = 'Phonetic Alphabet Decode:'
        results[1] = 'Input text = ' + '\n' + input_text_lower

        t = 2
        for table_description, table in tables.items():
            results[t] = '\n' + '------'
            t += 1
            results[t] = table_description + '\n' +\
                return_phonetic_alphabet_values(table) + '\n' +\
                phonetic_alphabet_d(input_text_lower, table)
            t += 1

    elif mode == 'Encode':
        results[0] = 'Phonetic Alphabet Encode:'
        results[1] = 'Input text = ' + '\n' + input_text_lower

        t = 2
        for table_description, table in tables.items():
            results[t] = '\n' + '------'
            t += 1
            results[t] = table_description + '\n' +\
                return_phonetic_alphabet_values(table) + '\n' +\
                phonetic_alphabet_e(input_text_lower, table)
            t += 1

    return results


def polybius_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    results = {}

    if mode == 'Decode':
        input_text = re.sub(r"[^0-9]", "", input_text).upper()
        results[0] =\
            'Input: ' + input_text + '\n' +\
            'Polybius Cipher Decode:' + polybius_d(input_text)
    elif mode == 'Encode':
        input_text = re.sub(r"[^a-zA-Z]", "", input_text).upper()
        results[0] =\
            'Input: ' + input_text + '\n' +\
            'Polybius Cipher Encode:' + polybius_e(input_text)

    return results


def riddle_tables_gen(request):
    mode = request.json['mode']

    results = {}

    if mode == 'jp_trad_month_name':
        results[0] = 'Japan Traditional Month Name'
        japan_traditional_month_names_list = return_japan_traditional_month_names_list()
        t = 1
        for a in japan_traditional_month_names_list:
            results[t] = a
            t += 1

    elif mode == 'zodiac':
        results[0] = 'Zodiac Name (Latin, Japanese, English, Greek)'
        zodiac_list = return_zodiac_list()
        t = 1
        for a in zodiac_list:
            results[t] = '<p>'+a+'</p>'
            t += 1

    elif mode == 'japanese_zodiac':
        results[0] = '十二支 (Japanese Zodiac)'
        japanese_zodiac_list = return_japanese_zodiac_list()
        t = 1
        for a in japanese_zodiac_list:
            results[t] = a
            t += 1

    elif mode == 'keyboard_layout':
        results[0] = 'US Keyboard Layout'
        results[1] = '<img class="responsive large-width" src="/static/image/640px-US_ANSI_keyboard_character_layout_JIS_comparison.svg.png">'
        results[2] = ''
        results[3] = 'Japanese Keyboard Layout'
        results[4] = '<img class="responsive large-width" src="/static/image/640px-JIS_keyboard_character_layout_US_ANSI_comparison.svg.png">'
        results[5] = ''
        results[6] = 'Images are from https://ja.wikipedia.org/wiki/%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB:US_ANSI_keyboard_character_layout_JIS_comparison.svg and https://ja.wikipedia.org/wiki/%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB:JIS_keyboard_character_layout_US_ANSI_comparison.svg'

    return results


def swap_xy_gen(request):
    input_text = request.json['input_text']

    results = {}
    results[0] = swap_xy_axes(input_text)
    return results


def rot_ex_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    results = {}
    if mode == 'rotplus_atbash':
        results[0] = 'ROT+'
        results[1] = '\n'.join(str(i).zfill(2) + ': ' +
                               rot(c=input_text, k=i, nc=True) for i in range(26))
        results[2] = '-----'
        results[3] = 'ROT+ -> Atbash'
        results[4] = '\n'.join(str(i).zfill(2) + ': ' +
                               atbash(c=rot(c=input_text, k=i, nc=True), nc=True) for i in range(26))
    elif mode == 'rotminus_atbash':
        results[0] = 'ROT-'
        results[1] = '\n'.join(str(i).zfill(2) + ': ' +
                               rot(c=input_text, k=-i, nc=True) for i in range(26))
        results[2] = '-----'
        results[3] = 'ROT- -> Atbash'
        results[4] = '\n'.join(str(i).zfill(2) + ': ' +
                               atbash(c=rot(c=input_text, k=-i, nc=True), nc=True) for i in range(26))
    elif mode == 'atbash_rotplus':
        results[0] = 'ROT+'
        results[1] = '\n'.join(str(i).zfill(2) + ': ' +
                               rot(c=input_text, k=i, nc=True) for i in range(26))
        results[2] = '-----'
        results[3] = 'Atbash -> ROT+'
        results[4] = '\n'.join(str(i).zfill(2) + ': ' +
                               rot(c=atbash(c=input_text, nc=True), k=i, nc=True) for i in range(26))
    elif mode == 'atbash_rotminus':
        results[0] = 'ROT-'
        results[1] = '\n'.join(str(i).zfill(2) + ': ' +
                               rot(c=input_text, k=-i, nc=True) for i in range(26))
        results[2] = '-----'
        results[3] = 'Atbash -> ROT-'
        results[4] = '\n'.join(str(i).zfill(2) + ': ' +
                               rot(c=atbash(c=input_text, nc=True), k=-i, nc=True) for i in range(26))

    return results


def rectangle_ex_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']
    mode_ex = request.json['mode_ex']

    results = {}

    t = 0

    if mode_ex == 'normal':
        results[t] = 'Text length = ' + str(len(input_text))
        t += 1
        for i in range(2, ceil(len(input_text)/2)+1):
            if len(input_text) % i == 0 or mode == 'All pattern':
                rectangle_i = rect(input_text, i)

                results[t] = '-----'
                t += 1

                results[t] = 'Column count = ' + str(i)
                t += 1
                for r in range(len(rectangle_i)):
                    results[t] = rectangle_i[r]
                    t += 1
    elif mode_ex == 'reverse_even':
        results[t] = 'Text length = ' + str(len(input_text))
        t += 1
        for i in range(2, ceil(len(input_text)/2)+1):
            if len(input_text) % i == 0 or mode == 'All pattern':
                rectangle_i = rect_reverse_even(input_text, i)

                results[t] = '-----'
                t += 1

                results[t] = 'Column count = ' + str(i)
                t += 1
                for r in range(len(rectangle_i)):
                    results[t] = rectangle_i[r]
                    t += 1

    return results


def vigenere_ex_gen(request):
    input_text = request.json['input_text']
    key = request.json['key']

    key = re.sub(r"[^a-zA-Z0-9]", "", key)

    results = {}

    results[0] = \
        'Text: ' + input_text + '\n' +\
        'Key: ' + key + '\n' +\
        'Decoded: ' + vig_d(input_text, key, nc=True) + '\n' +\
        'Encoded: ' + vig_e(input_text, key, nc=True) + '\n' +\
        'Beaufort: ' + beaufort(input_text, key, nc=True) + '\n' +\
        'Auto key Decoded: ' + vig_d_auto(input_text, key, nc=True) + '\n' +\
        'Auto key Encoded: ' + vig_e_auto(input_text, key, nc=True)
    return results


def charcode_ex_gen(request):
    input_text = request.json['input_text']
    results = {}

    results[0] = 'Attempt to decode by DEC'
    number_string = auto_split_number_string(input_text, 'DEC')
    results[1] = 'Extracted numbers: ' + \
        ' '.join(number_string)
    results[2] = ''.join(chr(int(i)) for i in number_string)
    results[3] = '------'

    results[10] = 'Attempt to decode by HEX'
    number_string = auto_split_number_string(input_text, 'HEX')
    results[11] = 'Extracted numbers: ' + \
        ' '.join(number_string)
    results[12] = ''.join(chr(int(base_a_to_base_b_onenumber(
        i, 16, 10))) for i in number_string)
    results[13] = '------'

    results[20] = 'Attempt to decode by OCT'
    number_string = auto_split_number_string(input_text, 'OCT')
    results[21] = 'Extracted numbers: ' + \
        ' '.join(number_string)
    results[22] = ''.join(chr(int(base_a_to_base_b_onenumber(
        i, 8, 10))) for i in number_string)
    results[23] = '------'

    results[30] = 'Attempt to decode by BIN'
    number_string = auto_split_number_string(input_text, 'BIN')
    results[31] = 'Extracted numbers: ' + \
        ' '.join(number_string)
    results[32] = ''.join(chr(int(base_a_to_base_b_onenumber(
        i, 2, 10))) for i in number_string)

    return results


def passcode_gen(id):
    return passcode_get_record_by_id(id)


def passcode_random_id(request):
    return str(passcode_get_random_id())


def passcode_today_id(request):
    return str(passcode_get_today_id())


def passcode_list(request):
    passcode_list_raw = passcode_get_list()
    q_list = {}
    i = 1
    for item in passcode_list_raw:
        q_list[i] = \
            '<a class="link" href="./' + str(item['id']) + '">' +\
            '#' + str(item['id']) + ' ' +\
            item['date'] + ' ' +\
            html.escape(item['code'][:10]) + '... | ' +\
            item['tag'].replace('Difficulty: ', '') + ' ' +\
            '</a>'
        i += 1

    return q_list


def passcode_validate(request):
    id = int(request.json['id'])
    input_answer = request.json['input_answer']
    validate_results = passcode_validate_answer(id, input_answer)

    confirmed = False
    if validate_results[0] == 'Confirmed':
        index = 1
        confirmed = True
    elif validate_results[1] == 'Confirmed':
        index = 2
        confirmed = True
    elif validate_results[2] == 'Confirmed':
        index = 3
        confirmed = True

    if confirmed:
        re, w, a, r, d = passcode_get_reward(id, index)
        results_value = \
            '<article class="border">' +\
            '<h6 class="cyan-text">Passcode confirmed.</h6>' +\
            '<p class="large-text amber-text">' +\
            'Gained:' + '\n' +\
            re + '\n' +\
            w + '\n' +\
            a + '\n' +\
            r + '\n' +\
            d +\
            '</p>' + '\n' +\
            '</article><p class="grey-text">* Not actually gained in Ingress.</p>'
    else:
        if validate_results[0] != 'Invalid.':
            results_value = '<div class="mono orange-text results_area large-text">' + \
                validate_results[0] + '<div>'
        elif validate_results[1] != 'Invalid.':
            results_value = '<div class="mono orange-text results_area large-text">' + \
                validate_results[1] + '<div>'
        elif validate_results[2] != 'Invalid.':
            results_value = '<div class="mono orange-text results_area large-text">' + \
                validate_results[2] + '<div>'
        else:
            results_value = '<div class="mono gray-text results_area large-text">Invalid.<div>'

    return results_value


def ingress_keywords_gen(request):
    pattern = request.json['pattern'].lower()
    results = {}

    keywords_list = passcode_get_filtered_keywords(pattern)

    i = 0
    for keyword in keywords_list:
        results[i] = keyword
        i += 1
    return results


def skip_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    results = {}

    if mode == 'Decode':
        results[0] =\
            'step:' + '\n'

        for i in range(2, min(len(input_text), 100)):
            results[0] += str(i).zfill(2) + ': ' +\
                skip_d(input_text, i) + '\n'

    elif mode == 'Encode':
        results[0] =\
            'step:' + '\n'

        for i in range(2, min(len(input_text), 100)):
            results[0] += str(i).zfill(2) + ': ' +\
                skip_e(input_text, i) + '\n'

    return results


def bifid_gen(request):
    input_text = request.json['input_text']
    key = request.json['key']
    table = mixed_alphabet(key, True)

    results = {}
    results[0] = \
        'Key table:' + '\n' +\
        table[0:5] + '\n' +\
        table[5:10] + '\n' +\
        table[10:15] + '\n' +\
        table[15:20] + '\n' +\
        table[20:25]

    results[1] = '\n'

    results[2] = \
        'Decoded: ' + bifid_d(input_text, key) + '\n' +\
        'Encoded: ' + bifid_e(input_text, key)
    return results


def vanity_gen(request):
    input_text = request.json['input_text']
    mode = request.json['mode']

    results = {}

    if mode == 'Encode':
        input_text = input_text.upper()
        input_text = re.sub(r"[^A-Z]", "", input_text)

        results[0] = 'Text:'
        results[1] = input_text
        results[2] = '\n'

        results[3] = 'Toggle style:'
        results[4] = vanity_e(input_text, 'toggle')
        results[5] = '\n'

        results[10] = 'Press count - Number style:'
        results[11] = vanity_e(input_text, 'rept_number')
        results[12] = '\n'

        results[20] = 'Number - Press count style:'
        results[21] = vanity_e(input_text, 'number_rept')
        results[22] = '\n'
    elif mode == 'Decode':
        results[0] = 'Toggle style:'
        results[1] = ' '.join(auto_split_number_string(
            input_text, 'vanity_toggle'))
        results[2] = vanity_d(input_text, 'toggle')
        results[3] = '\n'

        results[10] = 'Press count - Number style:'
        results[11] = ' '.join(auto_split_number_string(
            input_text, 'vanity_rept_number'))
        results[12] = vanity_d(input_text, 'rept_number')
        results[13] = '\n'

        results[20] = 'Number - Press count style:'
        results[21] = ' '.join(auto_split_number_string(
            input_text, 'vanity_number_rept'))
        results[22] = vanity_d(input_text, 'number_rept')
        results[23] = '\n'
    return results


def kakushi_gen(request):
    input_text = request.json['input_text']
    key = request.json['key']
    mode = request.json['mode']
    debug_mode = request.json['debug_mode']

    results = {}
    if mode == 'Decode':
        if debug_mode == "OFF":
            kakushi=kakushi_decode(input_text, key,False)
            results[0] = '---KAKUSHI DECIPHERED---'
            results[1] = kakushi.decoded
            results[2] = '\n'
        elif debug_mode == "ON":
            kakushi=kakushi_decode(input_text, key,True)
            results[0] = '---INPUT---'
            results[1] = input_text
            results[2] = '\n'
            results[3] = '---KEY---'
            results[4] = key
            results[5] = '\n'
            results[6] = '---INPUT (Binary)---'
            results[7] = kakushi.input_binary
            results[8] = '\n'
            results[9] = '---KEY STREAM (Binary)---'
            results[10] = kakushi.key_binary
            results[11] = '\n'
            results[12] = '---KAKUSHI DECIPHERED (Binary)---'
            results[13] = kakushi.xor_binary
            results[14] = '\n'
            results[15] = '---KAKUSHI DECIPHERED---'
            results[16] = kakushi.decoded
            results[17] = '\n'

    elif mode == 'Encode':
        if debug_mode == "OFF":
            kakushi=kakushi_encode(input_text, key,False)
            results[0] = '---KAKUSHI CIPHERED---'
            results[1] = kakushi.encoded
            results[2] = '\n'
        elif debug_mode == "ON":
            kakushi=kakushi_encode(input_text, key,True)
            results[0] = '---INPUT---'
            results[1] = input_text
            results[2] = '\n'
            results[3] = '---KEY---'
            results[4] = key
            results[5] = '\n'
            results[6] = '---INPUT (Binary)---'
            results[7] = kakushi.input_binary
            results[8] = '\n'
            results[9] = '---KEY STREAM (Binary)---'
            results[10] = kakushi.key_binary
            results[11] = '\n'
            results[12] = '---KAKUSHI CIPHERED (Binary)---'
            results[13] = kakushi.xor_binary
            results[14] = '\n'
            results[15] = '---KAKUSHI CIPHERED---'
            results[16] = kakushi.encoded
            results[17] = '\n'

    return results