rot_about_ja = """
「ROT N」はアルファベットを、ABC…の順番に沿ってN番ずらす暗号です。例えばROT 3を使用するとAはDに、BはEに変換されます。Zを超えるとAに戻ります。例えばROT 3であればYはBに移ります。

これは最もシンプルなタイプの暗号であり、特にROT 13はPythonのCODECモジュールにも組み込まれています。ROTあるいはROT13は多くの人にとって最初に知る暗号であり、暗号の基礎中の基礎としての位置にあります。

「ROT N」の暗号強度は皆無であり、単独で暗号としての用を果たすことはありません。しかしROT13は「一見して内容はわからないが、その気になれば簡単に解読できる」という特徴から、BBSでネタバレを避けたい人に配慮して発言する際やジオキャッシングでヒントを出す際などに使われるというユースケースも存在しました。

ROT Nでエンコードされた文章は、ROT -Nでデコードすることができます。アルファベットの文字数が26文字であるため、「ROT -13」は「ROT 13」と同一であり、そのためROT13でエンコードされた文章はROT13でデコードすることができます。このエンコード・デコードの向きを気にしなくていいという対象性も、上記のユースケースでROT13が好まれた理由の一つだと考えています。例えば「ROT 5です」と言われて暗号文を渡されたときに、+5したらデコードできるのか-5したらデコードできるのか迷うことがありますが、ROT13にはそういう心配がありません。

ROT暗号は古代ローマのカエサル(シーザー)が使用したという逸話から、カエサル暗号やシーザー暗号とも呼ばれます。当時でもこの方式に暗号としての十分な強度があったとは考えづらく、もう少し複雑な文脈があるか、あるいは根も葉もないか・・と個人的には考えていますが、調査するのも難しいため踏み込みません。

ROTという呼び名はアルファベットの環を回すイメージでRotateあたりの単語由来かと思われます。
"""

rot_hot_to_use_ja = """
本サイトのツールでは、入力された文章に対し、ROT 0から+25までを一覧で出力します。通常のアルファベットのみを変換の対象とし、数字や記号、他言語の文字種については入力された内容のまま出力します。

大文字で入力されたものは大文字のまま、小文字で入力されたものは小文字のままでROT変換を行います。
"""

rot_test_cases = """
<b>Case 1</b>
INPUT = ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789
ROT +8
OUTPUT = IJKLMNOPQRSTUVWXYZABCDEFGHijklmnopqrstuvwxyzabcdefgh0123456789

<b>Case 2</b>
INPUT = The rabbit-hole went straight on like a tunnel for some way, and then dipped suddenly down, so suddenly that Alice had not a moment to think about stopping herself before she found herself falling down a very deep well.
ROT +20
OUTPUT = Nby luvvcn-bify qyhn mnlucabn ih fcey u nohhyf zil migy qus, uhx nbyh xcjjyx moxxyhfs xiqh, mi moxxyhfs nbun Ufcwy bux hin u gigyhn ni nbche uvion mnijjcha bylmyfz vyzily mby ziohx bylmyfz zuffcha xiqh u pyls xyyj qyff.

(Can be reconciled at <a href="https://multidec.web-lab.at/mr.php" target="_blank" class="link">https://multidec.web-lab.at/mr.php</a>)

"""

rot_challenge = """
B Ebzrb, Ebzrb, jurersber neg gubh Ebzrb?
Qral gul sngure naq ershfr gul anzr.
Be vs gubh jvyg abg, or ohg fjbea zl ybir,
Naq V’yy ab ybatre or n Pnchyrg.
"""

rot_link = """
<a href="../rot" target="_blank" class="link">Cipher Tool: Rot</a>
"""


kakushi_about_ja = """
「Kakushi」は、私が独自に設計した暗号です。UTF-8で表現できる文章を対象としており、日本語の文章もそのまま暗号化できることが特徴です。

この方式はVigenère暗号と同程度、あるいはそれ以上の強度を持っていますが、現代的な暗号技術としての利用や強度保証を意図したものではありません。

一方で、日本語を含むメモや短い文章を「人に見られたくない形で保存しておく」といった用途には十分実用的です。
暗号文は自然言語として読めない文字列になるため、内容を直感的に隠すことができます。

<b>Base64との類似点と違い</b>

Kakushiは、Base64と同じく「バイナリ列を文字列へ変換する」仕組みの暗号です。Base64が64種類の文字でデータを表現するのに対し、Kakushiは256種類の文字を使います。

つまり、1バイトをそのまま1文字に対応させる設計であり、出力文字列の長さは元のバイト列と同じになります。

Base64は暗号ではなく、変換規則を知っていれば誰でも復号できるのに対し、KakushiはXORによるマスク処理を行うため、プロトコルを知っているだけでは復号できません。

暗号文を元に戻すには必ずキーワードが必要です。この点でKakushiはVigenère暗号に近い性質を持っています。

<b>XORによるVigenère的変換</b>

Kakushiでは、平文のバイト列に対してキーワード由来のバイト列をXORする処理を加えます。

これはVigenère暗号と同じく鍵を繰り返し適用して変換する方式であり、鍵が分からなければ復元できません。

また、暗号化と復号が完全に対称である点も特徴です。XORは同じ鍵で再度処理すると元に戻るため、

エンコード = XORでマスク

デコード = 同じXORで復号

という構造になっています。

Kakushiでは単純にキーワードを繰り返すのではなく、キーワードからより長いキーストリームを生成して使用します。

これは暗号強度を高めるためもありますが、もっぱら暗号化後の文字種の偏りを減らし、出力をよりランダムに見せたほうが面白いという動機によります。

キーストリームは、キーワードをUTF-8バイト列とし、それをビット単位で左シフトさせながら展開することで作られます。

<b>変換仕様</b>
使用する文字セットは下記の256種です。日本語で使用頻度の高い文字を用い、見た目が紛らわしい文字をいくつか除きました。

あいうえおかきくけこがぎぐげごさ
しすせそたちつてとなにぬねのはひ
ふほまみむめもやゆよらりるれろわ
をんアイウオカキクケコサシスセソ
タチツテトナネノハヒフマミムメモ
人日年大分出行中生本事時的上見者
方間思合自国会子言場入手地気前業
定用月学後私体対度動理今実性法目
十部三下物当関同家発金要力高内長
通立化成何作第女社意所問来全代書
考心話小知彼現取以明最持教数回保
多新外感主市員開表先不変水機使等
名文期民五経世道食面政山少々活相
結四産向品題無受設必近味調利加田
能円点料付九正重特身連平公務在次
切制記戦指進情原安決聞画解別計資


エンコード手順は下記のようになります。

1. 入力文字列をUTF-8でバイト列に変換する

2. キーワードからキーストリームを生成する
キーワードが 01100001 01100010 であれば、次は1ビット左にずらした 11000010 11000100 その次はさらに1ビット左にずらした 10000101 10001001 を用い、
01100001 01100010 11000010 11000100 10000101 10001001...
をキーストリームとして用います。
元のキーワードがNバイトであれば、N*8バイトの長さがあるキーストリームを使用することになります。
キーワードにはUTF-8の任意の文字が使用できます。

3. 入力文字列のバイト列を、キーストリームでXORマスクします。

4. マスク後の各バイトを上記の文字セットの対応する文字に置き換えます。


"""


kakushi_link = """
<a href="../kakushi" target="_blank" class="link">Cipher Tool: Kakushi</a>
"""

contents = {
    'rot-ja': {
        'title': 'ROT',
        'lang': 'Ja',
        'about': rot_about_ja,
        'how_to_use_tool': rot_hot_to_use_ja,
        'test_cases': rot_test_cases,
        'challenge': rot_challenge,
        'link': rot_link,
    },
    'rot-en': {
        'title': 'ROT',
        'lang': 'En',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': rot_test_cases,
        'challenge': rot_challenge,
        'link': rot_link,
    },
    'kakushi-ja': {
        'title': 'Kakushi',
        'lang': 'Ja',
        'about': kakushi_about_ja,
        'how_to_use_tool': "",
        'test_cases': "",
        'challenge': "",
        'link': kakushi_link,
    },
    'vigenere-ja': {
        'title': 'Vigenere',
        'lang': 'Ja',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': '',
        'challenge': '',
        'link': '',
    },
    'vigenere-en': {
        'title': 'Vigenere',
        'lang': 'En',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': '',
        'challenge': '',
        'link': '',
    },
    'simplesub-ja': {
        'title': 'Simple substitutions',
        'lang': 'Ja',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': '',
        'challenge': '',
        'link': '',
    },
    'simplesub-en': {
        'title': 'Simple substitutions',
        'lang': 'En',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': '',
        'challenge': '',
        'link': '',
    },
    'affine-ja': {
        'title': 'Affine',
        'lang': 'Ja',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': '',
        'challenge': '',
        'link': '',
    },
    'affine-en': {
        'title': 'Affine',
        'lang': 'En',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': '',
        'challenge': '',
        'link': '',
    },
    'polybius-ja': {
        'title': 'Polybius',
        'lang': 'Ja',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': '',
        'challenge': '',
        'link': '',
    },
    'polybius-en': {
        'title': 'Polybius',
        'lang': 'En',
        'about': '',
        'how_to_use_tool': '',
        'test_cases': '',
        'challenge': '',
        'link': '',
    },
}


def output_with_tag(text):
    text = text.strip()
    if len(text) == 0:
        return '<p>No contents yet.</p>'
    rows = text.split('\n')
    output = ''
    for row in rows:
        row = row.strip(' ')
        if len(row) == 0:
            output += '<br>'
        else:
            output += '<p>'+row+'</p>'
    return output


def prose(mode, pageid):
    if mode == 'keys':
        return contents.keys()
    else:
        content = contents[pageid]
        return {'title': content['title'],
                'lang': content['lang'],
                'about': output_with_tag(content['about']),
                'how_to_use_tool': output_with_tag(content['how_to_use_tool']),
                'test_cases': output_with_tag(content['test_cases']),
                'challenge': output_with_tag(content['challenge']),
                'link': output_with_tag(content['link']), }
