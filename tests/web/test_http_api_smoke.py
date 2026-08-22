def test_get_basic_pages(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Crypto Brella" in body
    assert 'type="search"' in body
    assert "Cryptography" in body
    assert "Remember Ingress" in body
    assert "Niantic Wiki" in body
    assert '"/niantic_wiki/page/start.html"' in body
    assert '"icon_niantic_wiki.png"' in body
    about_resp = client.get("/about")
    assert about_resp.status_code == 200
    about_body = about_resp.get_data(as_text=True)
    assert "V1.2.0" in about_body
    assert "Added hosting for the Niantic Project Wiki archive." in about_body
    assert "V1.3.0" in about_body
    assert "Expanded the Enigma tool with Enigma I, Kriegsmarine M3/M4" in about_body
    assert "V1.4.0" in about_body
    assert "Added the Pigpen encoder, visual decoder" in about_body
    assert "V1.6.0" in about_body
    assert "Added Double Columnar." in about_body
    link_resp = client.get("/link")
    assert link_resp.status_code == 200
    link_body = link_resp.get_data(as_text=True)
    assert "Built with" in link_body
    assert "Useful external sites related to ciphers" in link_body


def test_missing_page_uses_custom_404(client):
    resp = client.get("/not-found")
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    assert "404 Not Found" in body
    assert "The page you are looking for could not be found." in body
    assert "Back to Top" in body


def test_cipher_docs_page_renders(client):
    resp = client.get("/cipher_docs/rot-ja")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "ROT" in body
    assert "Can you decode?" in body
    assert "Cipher Tool: Rot" in body


def test_secom_ja_cipher_docs_page_renders(client):
    resp = client.get("/cipher_docs/secom-ja")

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Hand cipher の一つの到達点" in body
    assert "必要な鍵をすべて単一のKey Phraseから導出" in body
    assert "<strong>1. Key Phraseの最初の20文字を取り出す</strong>" in body
    assert "<strong>6. 二段階のTransposition</strong>" in body
    assert "Straddling Checkerboard" in body
    assert "二段階のColumnar Transposition" in body
    assert "Dirk Rijmenants" in body
    assert "Oleksii Sylichenko" in body
    assert 'href="../secom"' in body
    assert (
        'href="https://www.ciphermachinesandcryptology.com/en/secom.htm"'
        in body
    )
    assert 'href="https://github.com/asilichenko/secom-cipher-gui"' in body


def test_secom_en_cipher_docs_page_renders(client):
    resp = client.get("/cipher_docs/secom-en")

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "one of the high points of hand cipher design" in body
    assert "deriving every required key from a single Key Phrase" in body
    assert "<strong>1. Take the first 20 letters of the Key Phrase</strong>" in body
    assert "<strong>6. Perform two stages of Transposition</strong>" in body
    assert "Key phrase: ___ IS THE MONTH I TRUST LEAST." in body
    assert 'href="../secom"' in body


def test_secom_page_renders(client):
    page_resp = client.get("/secom")
    assert page_resp.status_code == 200
    page_body = page_resp.get_data(as_text=True)
    assert "SECOM" in page_body
    assert "gear/secom_gen" in page_body
    assert 'href="./cipher_docs/secom-ja"' in page_body
    assert 'href="./cipher_docs/secom-en"' in page_body
    assert "解説 Ja" in page_body
    assert ">En</a>" in page_body
    assert "Detailed steps: ON" in page_body
    assert 'detail_mode:"OFF"' in page_body

    home_resp = client.get("/")
    assert home_resp.status_code == 200
    assert '"path": "/secom"' in home_resp.get_data(as_text=True)


def test_pigpen_page_renders_with_home_link(client):
    page_resp = client.get("/pigpen")

    assert page_resp.status_code == 200
    page_body = page_resp.get_data(as_text=True)
    assert "<title>Pigpen</title>" in page_body
    assert "Pigpen Prototype" not in page_body
    assert "Choose a 26-letter mapping" not in page_body
    assert "Only A–Z letters and spaces are preserved" not in page_body
    assert "Download Image" in page_body
    assert "Download SVG" not in page_body
    assert "Copy decoded text" not in page_body
    assert 'class="mono grey-text results_area large-text"' in page_body
    assert "Input Text" in page_body
    assert "Pigpen symbol" in page_body
    assert "Input symbol" in page_body
    assert "Decoded text" in page_body
    assert "space_bar" in page_body
    assert "normalizedInput.length > 0" in page_body
    assert "decodedTokens.length > 0" in page_body
    assert "Standard — Grid, Grid dot, X, X dot" in page_body
    assert "Alternate — Grid, X, Grid dot, X dot" in page_body
    assert "Dotted first" in page_body
    assert "Interleaved dots" in page_body
    assert "Column order" in page_body
    assert "Reverse alphabet" in page_body
    assert 'variantId:"standard"' in page_body
    assert 'slotLetters:"ABCDEFGHIJKLMNOPQRSUVTWYZX"' in page_body
    assert 'slotLetters:"ABCDEFGHINOPQRSTUVJLMKWYZX"' in page_body
    assert 'slotLetters:"ACEGIKMOQBDFHJLNPRSWYUTXZV"' in page_body
    assert "X letters run top, left, right, bottom" in page_body
    assert 'label class="active">Variant</label>' in page_body
    assert "pigpen_\" + filenamePart + \".svg" in page_body
    assert "downloadImage" in page_body
    assert "Tap a cell" in page_body
    assert ".pigpen-decode-actions button span { display: none; }" in page_body
    assert "justify-content: center" in page_body
    assert "Select a position on the same grid" not in page_body
    assert "Grid — no dot" not in page_body
    assert "Grid — dot" not in page_body
    assert "X — no dot" not in page_body
    assert "X — dot" not in page_body
    assert "pigpen-input-symbol-result" in page_body
    assert "--pigpen-board-size: min(40vw, 9rem)" in page_body
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in page_body
    assert 'mode:"Encode"' in page_body
    assert 'encodeInput:""' in page_body
    assert 'letter:"A"' in page_body
    assert 'letter:"Z"' in page_body

    home_body = client.get("/").get_data(as_text=True)
    assert '"path": "/pigpen"' in home_body
    assert '"icon_pigpen.png"' in home_body

    old_page_resp = client.get("/pigpen_prototype")
    assert old_page_resp.status_code == 404


def test_niantic_wiki_index_renders(client):
    resp = client.get("/niantic_wiki/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Niantic Project Wiki" in body
    assert 'href="/niantic_wiki/page/start.html"' in body
    assert 'href="/niantic_wiki/favicon.ico"' in body


def test_niantic_wiki_page_renders(client):
    resp = client.get("/niantic_wiki/page/start.html")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Niantic Project Wiki" in body
    assert 'src="/niantic_wiki/script.js"' in body


def test_niantic_wiki_asset_renders(client):
    resp = client.get("/niantic_wiki/script.js")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "fetch('/niantic_wiki/search-index.json')" in body


def test_niantic_wiki_preserved_missing_page_stays_404(client):
    resp = client.get("/niantic_wiki/page/the_sourcebook.html")
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    assert "Page not found" in body
    assert 'href="/niantic_wiki/page/start.html"' in body


def test_post_gear_rot_success(client):
    resp = client.post("/gear/rot_gen", json={"input_text": "Abc-123"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "0" in body
    assert "00: Abc-123" in body["0"]


def test_double_columnar_page_home_link_icon_and_api(client):
    page_resp = client.get("/double_columnar")
    assert page_resp.status_code == 200
    page_body = page_resp.get_data(as_text=True)
    assert "<title>Double Columnar</title>" in page_body
    assert "Double Columnar Prototype" not in page_body
    assert "Two independently selectable columnar transpositions" not in page_body
    assert "Combine two independently selectable" not in page_body
    assert "text is preserved as entered" not in page_body
    assert page_body.index('id="TYPE1"') < page_body.index('id="KEY1"')
    assert page_body.index('id="TYPE2"') < page_body.index('id="KEY2"')
    assert "First Transposition" in page_body
    assert "Second Transposition" in page_body
    assert "Stage 1" not in page_body
    assert "Stage 2" not in page_body
    assert page_body.count('class="field label border small fill"') == 2
    assert page_body.count("double-columnar-key") == 2
    assert page_body.count("Key (alphabetic or numeric)") == 4
    assert "Letters or 3 1 4 2" not in page_body
    assert "ZEBRA" not in page_body
    assert "CARGO" not in page_body
    assert page_body.count("arrow_drop_down") == 2
    assert ">Disrupted</option>" in page_body
    assert "SECOM pattern" not in page_body
    assert "gear/double_columnar_gen" in page_body

    home_body = client.get("/").get_data(as_text=True)
    assert '"path": "/double_columnar"' in home_body
    assert '"icon_double_columnar.png"' in home_body

    icon_resp = client.get("/static/image/icon_double_columnar.png")
    assert icon_resp.status_code == 200
    assert icon_resp.mimetype == "image/png"

    css_resp = client.get("/static/css/style_v2.css")
    assert css_resp.status_code == 200
    css_body = css_resp.get_data(as_text=True)
    assert ".double-columnar-key input:focus::placeholder" in css_body
    assert "color: transparent" in css_body

    encode_resp = client.post(
        "/gear/double_columnar_gen",
        json={
            "input_text": (
                "YOURMOTHERWASAHAMSTERANDYOURFATHERSMELTOFELDERBERRIES"
            ),
            "key1": "DESCRIBE",
            "key2": "2 7 1 8 9 5 4 6 3",
            "type1": "standard",
            "type2": "standard",
            "mode": "Encode",
        },
    )
    assert encode_resp.status_code == 200
    body = encode_resp.get_json()
    assert body["1"] == (
        "NDODRWTRFHASEERAERMROFLBEOERSAYEAEIHMRALUTERHMTTYSOSU"
    )
    assert body["2"] == "\nFirst Transposition:"
    assert body["3"] == "Type: Standard"
    assert "Key:\nD  E  S  C  R  I  B  E" in body["4"]
    assert "Key order:\n3  4  8  2  7  6  1  5" in body["4"]
    assert "Data grid:\nY  O  U  R  M  O  T  H" in body["4"]
    assert body["5"] == "\nOutput after First Transposition:"
    assert body["6"] == (
        "THNTTBRAERMDEYEMYEFRORSORERHADHOEOAAALRMSRFEESUWTUSLI"
    )
    assert body["7"] == "\nSecond Transposition:"
    assert body["8"] == "Type: Standard"
    assert "Key order:\n2  7  1  8  9  5  4  6  3" in body["9"]
    assert body["10"] == "\nNotes:"
    assert body["11"].count(
        "Duplicate symbols are ranked from left to right."
    ) == 1
    assert body["11"].count("SP = space") == 1
    assert "Input table before reading columns:" not in body.values()
    assert "Intermediate table before reading columns:" not in body.values()
    assert all("Stage" not in value for value in body.values())


def test_double_columnar_reports_invalid_numeric_key(client):
    resp = client.post(
        "/gear/double_columnar_gen",
        json={
            "input_text": "TEST",
            "key1": "1-1-2",
            "key2": "KEY",
            "type1": "standard",
            "type2": "disrupted",
            "mode": "Encode",
        },
    )

    assert resp.status_code == 200
    assert resp.get_json() == {
        "0": "Input error:",
        "1": "Key may contain letters, digits, spaces, and commas only.",
    }


def test_post_gear_secom_matches_published_vector(client):
    resp = client.post(
        "/gear/secom_gen",
        json={
            "input_text": "RV TOMORROW AT 1400PM TO COMPLETE TRANSACTION USE DEADDROP AS USUAL",
            "key": "MAKE NEW FRIENDS BUT KEEP THE OLD",
            "mode": "Encode",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == {"0", "1", "2", "3"}
    assert body["0"] == "Input text:"
    assert body["1"] == (
        "RV TOMORROW AT 1400PM TO COMPLETE TRANSACTION USE DEADDROP AS USUAL"
    )
    assert body["2"] == "\nSECOM Encode:"
    assert body["3"] == (
        "77719 38622 00032 04239 60038 29683 14608 06071 78016 73606 "
        "06064 63536 06968 67403 69681 89001 40219 06662 60666 08631 60549"
    )


def test_post_gear_secom_removes_unsupported_input_characters(client):
    encode_resp = client.post(
        "/gear/secom_gen",
        json={
            "input_text": "ATTACK! AT DAWN?",
            "key": "MAKE NEW FRIENDS BUT KEEP THE OLD",
            "mode": "Encode",
        },
    )
    encode_body = encode_resp.get_json()

    assert encode_resp.status_code == 200
    assert encode_body["0"] == "Input text:"
    assert encode_body["1"] == "ATTACK AT DAWN"
    assert encode_body["3"] == "75973 09876 73066 39790"

    decode_resp = client.post(
        "/gear/secom_gen",
        json={
            "input_text": "75973-a09876 73066/39790",
            "key": "MAKE NEW FRIENDS BUT KEEP THE OLD",
            "mode": "Decode",
        },
    )
    decode_body = decode_resp.get_json()

    assert decode_resp.status_code == 200
    assert decode_body["0"] == "Input text:"
    assert decode_body["1"] == "75973 09876 73066 39790"
    assert decode_body["3"] == "ATTACK AT DAWN"


def test_post_gear_secom_detailed_encode_has_steps_without_decode_note(client):
    resp = client.post(
        "/gear/secom_gen",
        json={
            "input_text": "ATTACK AT DAWN",
            "key": "MAKE NEW FRIENDS BUT KEEP THE OLD",
            "mode": "Encode",
            "detail_mode": "ON",
        },
    )
    body = resp.get_json()

    assert resp.status_code == 200
    assert body["0"] == "Input text:"
    assert body["1"] == "ATTACK AT DAWN"
    assert body["2"] == "\nSECOM Encode:"
    assert body["4"].startswith("\nDetailed steps:\n\n")
    assert "Width mode:" not in body["4"]
    assert "1. Calculating the key phrase digits\n\n" in body["4"]
    assert "Plaintext written with * for spaces" not in body["4"]
    assert "Plaintext converted into numbers:\n79973937607960307685" in body["4"]
    assert "Digits read off in columns:\n96990387576933767700" in body["4"]
    assert (
        "Number of columns for the two transpositions:\n"
        "1st transposition: 7 + 2 + 3 = 12 columns\n"
        "2nd transposition: 5 + 6 = 11 columns"
    ) in body["4"]
    assert (
        "\n\nNull digits appended to complete a five-digit group:\nNone\n\n"
    ) in body["4"]
    assert not any(value.startswith("Note:") for value in body.values())


def test_post_gear_secom_default_decode_has_no_padding_note(client):
    resp = client.post(
        "/gear/secom_gen",
        json={
            "input_text": "75973 09876 73066 39790",
            "key": "MAKE NEW FRIENDS BUT KEEP THE OLD",
            "mode": "Decode",
        },
    )

    assert resp.status_code == 200
    assert resp.get_json() == {
        "0": "Input text:",
        "1": "75973 09876 73066 39790",
        "2": "\nSECOM Decode:",
        "3": "ATTACK AT DAWN",
    }


def test_post_gear_secom_detail_mode_returns_steps_and_decode_note(client):
    resp = client.post(
        "/gear/secom_gen",
        json={
            "input_text": "75973 09876 73066 39790",
            "key": "MAKE NEW FRIENDS BUT KEEP THE OLD",
            "mode": "Decode",
            "detail_mode": "ON",
        },
    )
    body = resp.get_json()

    assert resp.status_code == 200
    assert body["4"].startswith("\nDetailed steps:\n\n")
    assert "\n\n50 digits generated through chain addition:\n" in body["4"]
    assert "Ciphertext in five-digit groups" not in body["4"]
    assert "\n\nReversing the second disrupted transposition\n\n" in body["4"]
    assert (
        "Digits read row by row outside the triangular areas, then inside them:\n"
        "96990387576933767700"
    ) in body["4"]
    assert "Digits read row by row:\n79973937607960307685" in body["4"]
    assert body["5"] == (
        "Note: SECOM null padding can produce up to four ambiguous "
        "trailing characters."
    )


def test_post_gear_secom_reports_short_key(client):
    resp = client.post(
        "/gear/secom_gen",
        json={"input_text": "TEST", "key": "SHORT KEY", "mode": "Encode"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["0"] == (
        "Error: SECOM key phrase must contain at least 20 letters."
    )


def test_post_gear_railfence_empty_offset_branch(client):
    resp = client.post(
        "/gear/railfence_gen",
        json={"input_text": "WEAREDISCOVEREDFLEEATONCE", "mode": "Encode", "offset": ""},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "0" in body
    assert body["0"].startswith("Offset = 0")


def test_post_gear_number_conv_empty_base_branch(client):
    resp = client.post(
        "/gear/number_conv_gen",
        json={"input_text": "10,255", "base": ""},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["1"] == "from base: 10"


def test_post_gear_unknown_handler_returns_500(client):
    resp = client.post("/gear/not_existing_handler", json={"input_text": "abc"})
    assert resp.status_code == 500


def test_post_gear_unregistered_module_function_returns_500(client):
    resp = client.post("/gear/passcode_gen", json={"input_text": "abc"})
    assert resp.status_code == 500


def test_post_gear_missing_key_returns_500(client):
    resp = client.post("/gear/vigenere_gen", json={"input_text": "AttackAtDawn"})
    assert resp.status_code == 500
