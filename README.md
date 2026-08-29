# CryptoBrella

CryptoBrella is a browser-based collection of tools for classical ciphers,
encodings, text analysis, and puzzle solving. It is implemented as a Flask
application and brings small, focused utilities together behind a searchable
catalog.

## Features

- Classical cipher encoding, decoding, and simulation, including ROT,
  Vigenere, Affine, Playfair, Bifid, transposition ciphers, Enigma, PURPLE,
  and SECOM.
- Encoding and notation helpers for Base64, Morse code, character codes,
  Braille, phonetic alphabets, Pigpen, and related formats.
- Analysis and puzzle utilities such as character frequency, hashes, number
  conversion, prime factorization, text splitting, and image resizing.
- WordQuery: JP, a Japanese candidate search tool supporting readable
  patterns, exact anagrams, and regular expressions over an attributed
  lexicon.
- Preserved puzzle- and Ingress-related reference pages maintained separately
  from the general-purpose tool set.

These tools are intended for learning, historical cipher exploration, word
play, and puzzle solving. They are not a substitute for modern cryptographic
software and should not be used to protect sensitive information.

## Requirements

- CPython 3.13
- Flask 3.x
- Pillow 10.x or 11.x
- `regex`
- `lxml`

The supported dependency ranges are declared in `requirements.txt`.

WordQuery requires a generated SQLite lexicon assembled from separately
licensed source dictionaries. The generated database and original dictionary
archives are not included in this repository.

## Documentation

- [Crypto function inventory](docs/public/crypto_function_inventory.md)
- [System overview](docs/public/system_overview.md)
- [WordQuery: JP](docs/public/wordquery/README.md)
- [WordQuery data sources and license boundaries](docs/public/wordquery/data_sources.md)

## Rights and third-party material

No reuse license is granted for author-owned CryptoBrella code and
documentation unless an individual file explicitly states otherwise.
Dictionary data, archived content, images, and copied notices remain subject to
their respective rights and licenses. WordQuery source attribution and license
boundaries are documented in its
[data-source documentation](docs/public/wordquery/data_sources.md).
