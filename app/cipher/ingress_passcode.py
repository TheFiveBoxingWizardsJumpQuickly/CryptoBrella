import os
import sqlite3
import re
from pathlib import Path
from datetime import date
from hashlib import sha1
from random import randint


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


PASSCODE_DB_PATH = Path(os.path.join(
    *Path(__file__).parts[:-2], 'secret', 'passcode.db'
))


def _connect_db():
    conn = sqlite3.connect(
        # The passcode DB is shipped as a static read-only asset.
        # `immutable=1` avoids filesystem locking assumptions that can fail
        # when the app is run from Windows against the WSL share path.
        f"file:{PASSCODE_DB_PATH}?mode=ro&immutable=1",
        uri=True,
    )
    conn.row_factory = dict_factory
    return conn


def _fetch_all(query, params=()):
    with _connect_db() as conn:
        return conn.execute(query, params).fetchall()


def _fetch_one(query, params=()):
    rows = _fetch_all(query, params)
    return rows[0]


def passcode_get_record_by_id(id):
    return _fetch_one('SELECT * FROM daily WHERE id=?', (id,))


def get_answer_by_id(id):
    return [passcode_get_record_by_id(id)['answer1'],
            passcode_get_record_by_id(id)['answer2'],
            passcode_get_record_by_id(id)['answer3']]


def get_format_by_id(id):
    return passcode_get_record_by_id(id)['format']


def get_max_id():
    return _fetch_one('SELECT MAX(id) AS max_id FROM daily')['max_id']


def formatting_for_validation(txt):
    txt = str(txt)
    return txt.strip().upper().translate(str.maketrans({'0': 'O', 'Q': 'O', '1': 'I'}))


def validate_one_answer(correct_answer, input_answer, format):
    if correct_answer == '':
        return 'Invalid.'
    input_answer = formatting_for_validation(input_answer)
    correct_answer = formatting_for_validation(correct_answer)

    if input_answer == correct_answer:
        return 'Confirmed'
    else:
        if format == '#aaa#kwa#a#a':
            if re.sub(r"[0-9]", "", input_answer) == re.sub(r"[0-9]", "", correct_answer):
                return 'Number part might be wrong.'
            elif input_answer[0:5] == correct_answer[0:5] and input_answer[-5:] == correct_answer[-5:]:
                return 'Keyword might be wrong.'
            elif input_answer[5:-5] == correct_answer[5:-5]:
                return 'Suffix or Prefix might be wrong.'
            else:
                return 'Invalid.'
        elif format == 'kw#aa##aa#':
            if re.sub(r"[0-9]", "", input_answer) == re.sub(r"[0-9]", "", correct_answer):
                return 'Number part might be wrong.'
            elif input_answer[-8:] == correct_answer[-8:]:
                return 'Keyword might be wrong.'
            elif input_answer[0:-8] == correct_answer[0:-8]:
                return 'Suffix might be wrong.'
            else:
                return 'Invalid.'
        elif format == 'aaa##kw###aa':
            if re.sub(r"[0-9]", "", input_answer) == re.sub(r"[0-9]", "", correct_answer):
                return 'Number part might be wrong.'
            elif input_answer[0:5] == correct_answer[0:5] and input_answer[-5:] == correct_answer[-5:]:
                return 'Keyword might be wrong.'
            elif input_answer[5:-5] == correct_answer[5:-5]:
                return 'Suffix or Prefix might be wrong.'
            else:
                return 'Invalid.'


def passcode_validate_answer(id, input_answer):
    format = get_format_by_id(id)
    return [validate_one_answer(correct_answer, input_answer, format) for correct_answer in get_answer_by_id(id)]


def hash_today():
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    hash_hex_str = sha1(date_str.encode()).hexdigest()
    return hash_hex_str


def hash_today_answer(id, index):
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    comb_today_answer = str(int(date_str) * int(id) + int(index))
    hash_hex_str = sha1(comb_today_answer.encode()).hexdigest()
    return hash_hex_str


def passcode_get_today_id():
    hash_hex_str = hash_today()
    max_id = get_max_id()
    return int(hash_hex_str, 16) % max_id + 1


def passcode_get_random_id():
    max_id = get_max_id()
    return randint(1, max_id)


def reward_get_ap(hash_hex_str):
    dice = int(hash_hex_str[0:2], 16)
    if dice == 255:
        return '1337 AP'
    elif dice >= 160:
        return '400 AP'
    elif dice >= 80:
        return '200 AP'
    else:
        return '100 AP'


def reward_get_xm(hash_hex_str):
    dice = int(hash_hex_str[2:4], 16)
    if dice == 255:
        return '1337 XM'
    elif dice >= 160:
        return '400 XM'
    elif dice >= 80:
        return '200 XM'
    else:
        return '100 XM'


def reward_get_res(hash_hex_str):
    dice = int(hash_hex_str[4:6], 16)
    if dice == 255:
        return 'L8 Resonator (13)'
    elif dice >= 224:
        return 'L8 Resonator'
    elif dice >= 192:
        return 'L7 Resonator'
    elif dice >= 160:
        return 'L6 Resonator'
    elif dice >= 128:
        return 'L5 Resonator'
    elif dice >= 96:
        return 'L4 Resonator'
    elif dice >= 64:
        return 'L3 Resonator'
    elif dice >= 32:
        return 'L2 Resonator'
    else:
        return 'L1 Resonator'


def reward_get_burster(hash_hex_str):
    dice = int(hash_hex_str[6:8], 16)
    if dice == 255:
        return 'L8 Xmp Burster (13)'
    elif dice >= 224:
        return 'L8 Xmp Burster'
    elif dice >= 192:
        return 'L7 Xmp Burster'
    elif dice >= 160:
        return 'L6 Xmp Burster'
    elif dice >= 128:
        return 'L5 Xmp Burster'
    elif dice >= 96:
        return 'L4 Xmp Burster'
    elif dice >= 64:
        return 'L3 Xmp Burster'
    elif dice >= 32:
        return 'L2 Xmp Burster'
    else:
        return 'L1 Xmp Burster'


def reward_get_other(hash_hex_str):
    dice = int(hash_hex_str[8:10], 16)
    if dice >= 240:
        return 'L1 Media'
    elif dice >= 232:
        return 'L8 Power Cube (13)'
    elif dice >= 224:
        return 'Aegis Shield'
    elif dice >= 216:
        return 'Hypercube'
    elif dice >= 208:
        return 'Kinetic Capsule'
    elif dice >= 200:
        return 'SoftBank Ultra Link'
    elif dice >= 192:
        return 'Portal Shield (2)'
    elif dice >= 160:
        return 'Portal Shield'
    elif dice >= 128:
        return 'Multi-hack'
    elif dice >= 96:
        return 'Link Amp'
    elif dice >= 64:
        return 'Force Amp'
    elif dice >= 32:
        return 'Heat Sink'
    else:
        return 'L4 Power Cube'


def passcode_get_reward(id, index):
    hash_hex_str = hash_today_answer(id, index)
    ap = reward_get_ap(hash_hex_str)
    xm = reward_get_xm(hash_hex_str)
    res = reward_get_res(hash_hex_str)
    burster = reward_get_burster(hash_hex_str)
    other = reward_get_other(hash_hex_str)
    return [ap, xm, res, burster, other]


def passcode_get_list():
    return _fetch_all("SELECT id, date, code, tag FROM daily")


KEYWORDS = [
    '802',
    '855',
    '13magnus',
    '3rdlaw',
    'abaddon',
    'abandon',
    'absent',
    'accept',
    'acolyte',
    'ada',
    'adapt',
    'advance',
    'aegis',
    'aegisnova',
    'afram',
    'after',
    'again',
    'agent',
    'ai',
    'akira',
    'alaric',
    'alexander',
    'algorithm',
    'alignment',
    'all',
    'amongus',
    'answer',
    'antimagnus',
    'artifact',
    'artist',
    'aspiration',
    'attack',
    'augusta',
    'aura',
    'auras',
    'avoid',
    'balance',
    'barrier',
    'bedlam',
    'before',
    'begin',
    'being',
    'ben',
    'blackdev',
    'blackops',
    'bletchley',
    'blue',
    'body',
    'boson',
    'bowstring',
    'brainwave',
    'breathe',
    'byron',
    'calibration',
    'calvin',
    'campbell',
    'capture',
    'carrie',
    'carroll',
    'cassandra',
    'cathexis',
    'cern',
    'change',
    'chaos',
    'chaotic',
    'chapeau',
    'chase',
    'cipher',
    'city',
    'civilization',
    'clamantis',
    'clarke',
    'clear',
    'close',
    'code',
    'cold',
    'collapse',
    'collective',
    'comint',
    'complex',
    'condensate',
    'conflict',
    'congo',
    'consequence',
    'conspiracy',
    'conspire',
    'construct',
    'contemplate',
    'contract',
    'control',
    'cooper',
    'cortex',
    'courage',
    'covcom',
    'coverup',
    'create',
    'creation',
    'creative',
    'creativity',
    'crypto',
    'cube',
    'cthulhu',
    'cybella',
    'dalby',
    'danger',
    'dark',
    'darkmatter',
    'darkxm',
    'darsana',
    'data',
    'deaddrop',
    'deceit',
    'deception',
    'defend',
    'dejavu',
    'denial',
    'desire',
    'destination',
    'destiny',
    'destroy',
    'destruction',
    'detection',
    'deteriorate',
    'devra',
    'die',
    'difficult',
    'discover',
    'discovery',
    'disorder',
    'distance',
    'doorway',
    'draw',
    'dream',
    'drone',
    'easy',
    'einstein',
    'elint',
    'end',
    'enigma',
    'enlighten',
    'enlightened',
    'enlightenment',
    'enoch',
    'epiphany',
    'equal',
    'erode',
    'escape',
    'evolution',
    'evolve',
    'exotic',
    'explore',
    'explorer',
    'extremis',
    'ezekiel',
    'failure',
    'farlowe',
    'fear',
    'felicia',
    'field',
    'finality',
    'follow',
    'force',
    'forget',
    'forward',
    'function',
    'future',
    'gain',
    'geneva',
    'ghost',
    'global',
    'gluon',
    'glyph',
    'glyphs',
    'government',
    'gravity',
    'greanias',
    'green',
    'grid',
    'grow',
    'hajra',
    'hank',
    'hannah',
    'harm',
    'harmony',
    'have',
    'helios',
    'help',
    'henry',
    'hidden',
    'hide',
    'higgs',
    'holland',
    'hozho',
    'hubert',
    'hubris',
    'hulong',
    'human',
    'hunch',
    'hyper',
    'i',
    'idea',
    'ignore',
    'imint',
    'imperfect',
    'improve',
    'impure',
    'individual',
    'ingress',
    'ingression',
    'initio',
    'inside',
    'inspiration',
    'inspire',
    'intel',
    'intelligence',
    'intelligent',
    'interitus',
    'interrupt',
    'inveniri',
    'iqtech',
    'isobront',
    'ispirare',
    'jabberwocky',
    'jackland',
    'jahan',
    'jarvis',
    'johnson',
    'jormungand',
    'journey',
    'kalpa',
    'katelena',
    'ken',
    'kirlian',
    'klue',
    'knowledge',
    'kodama',
    'kureze',
    'lead',
    'legacy',
    'less',
    'liberate',
    'lie',
    'life',
    'lightman',
    'link',
    'live',
    'loci',
    'lose',
    'loss',
    'lovelace',
    'luizi',
    'lux',
    'magic',
    'magnus',
    'mantra',
    'marfa',
    'martin',
    'matter',
    'me',
    'meissner',
    'mentalism',
    'message',
    'meta',
    'microdot',
    'mind',
    'minotaur',
    'mirror',
    'misty',
    'mkoften',
    'mkultra',
    'modify',
    'mole',
    'monopole',
    'more',
    'moyer',
    'muon',
    'murder',
    'mystery',
    'mystic',
    'nagassa',
    'nature',
    'nemesis',
    'nest',
    'neural',
    'new',
    'ni',
    'niantic',
    'no',
    'noir',
    'not',
    'nourish',
    'nova',
    'now',
    'numinous',
    'nzeer',
    'obscured',
    'obsidian',
    'obsidius',
    'obstacle',
    'old',
    'oneiric',
    'open',
    'opening',
    'operative',
    'ordered',
    'other',
    'outside',
    'owen',
    'paint',
    'pandora',
    'parasite',
    'particle',
    'past',
    'path',
    'pattern',
    'peace',
    'perfection',
    'persepolis',
    'perspective',
    'phillips',
    'photint',
    'plasma',
    'pmc',
    'portal',
    'portals',
    'potential',
    'power',
    'powercube',
    'predator',
    'presence',
    'present',
    'presquevu',
    'profile',
    'progress',
    'progression',
    'pronoia',
    'pure',
    'purity',
    'pursue',
    'puzzle',
    'quanta',
    'quantum',
    'quark',
    'quasi',
    'question',
    'react',
    'rebel',
    'recharge',
    'recursion',
    'reduce',
    'reincarnate',
    'relative',
    'relativity',
    'repair',
    'repeat',
    'report',
    'rescue',
    'residual',
    'resist',
    'resistance',
    'resonance',
    'resonate',
    'restraint',
    'retreat',
    'richard',
    'roland',
    'rubicon',
    'rybat',
    'safety',
    'samsara',
    'save',
    'schubert',
    'sculpt',
    'sculpture',
    'se',
    'search',
    'secrets',
    'see',
    'seek',
    'self',
    'sensitive',
    'sensitives',
    'separate',
    'shape',
    'shaped',
    'shaper',
    'shapers',
    'shard',
    'share',
    'shell',
    'shonin',
    'sigint',
    'signal',
    'signs',
    'simple',
    'sirens',
    'sitrep',
    'skepsis',
    'soul',
    'space',
    'spacetime',
    'spirit',
    'spooky',
    'spy',
    'squid',
    'stability',
    'statue',
    'stay',
    'stein',
    'strategic',
    'strong',
    'structure',
    'struggle',
    'substitute',
    'substitution',
    'substrate',
    'success',
    'susanna',
    'sustain',
    'symbol',
    'symbols',
    'syphax',
    'tenniel',
    'technology',
    'them',
    'thought',
    'time',
    'timezero',
    'titus',
    'together',
    'transpose',
    'transposition',
    'truth',
    'tsukasa',
    'turing',
    'tycho',
    'tyro',
    'ultra',
    'unbounded',
    'urban',
    'urbdrone',
    'us',
    'use',
    'vault',
    'veritas',
    'verity',
    'verum',
    'vi',
    'vianoir',
    'vialux',
    'victor',
    'victory',
    'visur',
    'voynich',
    'want',
    'war',
    'wave',
    'we',
    'weak',
    'whydah',
    'win',
    'wolfe',
    'worth',
    'write',
    'xm',
    'yantra',
    'yeats',
    'you',
    'your',
    'yuen',
    'yuri',
    'zurich',
]


def passcode_get_filtered_keywords(pattern):
    try:
        filtered_list = list(filter(lambda x: re.match(pattern, x), KEYWORDS))
    except Exception as e:
        filtered_list = ['Error: {}'.format(e)]
    return filtered_list
