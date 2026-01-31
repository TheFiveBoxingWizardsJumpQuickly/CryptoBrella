"""
Charset Base256-like Encoder/Decoder with Keyword-Derived XOR

Specification
-------------
This module implements a simple Base256-style reversible transformation
using a fixed 256-character alphabet (CHAR_SET / CHAR_LIST).

Encoding
--------
- Input text is encoded into UTF-8 bytes.
- A XOR keystream is derived from the keyword:
    * keyword is converted to UTF-8 bytes (N bytes)
    * the full bitstring (N*8 bits) is treated as an integer
    * the bitstring is left-rotated by 1 bit repeatedly (N*8 times)
    * each rotated state contributes N bytes
    * total keystream length = N * (N*8) bytes
- Each plaintext byte is XOR-masked with the corresponding keystream byte.
- The resulting byte (0–255) is mapped to the corresponding character in CHAR_LIST.
- The output is a Unicode string of the same length as the byte sequence.

Decoding
--------
- Each encoded character is mapped back to its byte index via REV_MAP.
- The same keystream is applied via XOR to recover the original byte sequence.
- The recovered bytes are decoded as UTF-8.

"""

from dataclasses import dataclass
from typing import Optional, List

@dataclass(frozen=True)
class EncodeResult:
    encoded: str
    input_bytes: Optional[bytes] = None
    key_bytes: Optional[bytes] = None
    xor_bytes: Optional[bytes] = None
    input_binary: Optional[str] = None
    key_binary: Optional[str] = None
    xor_binary: Optional[str] = None

@dataclass(frozen=True)
class DecodeResult:
    decoded: str
    masked_bytes: Optional[bytes] = None
    key_bytes: Optional[bytes] = None
    output_bytes: Optional[bytes] = None
    input_binary: Optional[str] = None
    key_binary: Optional[str] = None
    xor_binary: Optional[str] = None

CHAR_SET = """
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
"""

CHAR_LIST = CHAR_SET.replace("\n", "")
REV_MAP = {ch: i for i, ch in enumerate(CHAR_LIST)}


def to_binary(data: bytes) -> str:
    return " ".join(f"{b:08b}" for b in data)


def keyword_key_stream(keyword: str) -> bytes:
    if not keyword:
        keyword = "隠し"

    base = keyword.encode("utf-8")
    n = len(base)

    bitlen = n * 8
    value = int.from_bytes(base, "big")

    out = bytearray()

    for _ in range(bitlen):
        out.extend(value.to_bytes(n, "big"))

        top = (value >> (bitlen - 1)) & 1
        value = ((value << 1) & ((1 << bitlen) - 1)) | top

    return bytes(out)


def kakushi_encode(text: str, keyword: str, debug: bool = True) -> EncodeResult:
    data = text.encode("utf-8")
    key_bytes_full = keyword_key_stream(keyword)
    key_len = len(key_bytes_full)
    key_slice = key_bytes_full[: len(data)]

    out_chars = []
    xor_bytes = bytearray()

    for i, b in enumerate(data):
        k = key_bytes_full[i % key_len]
        masked = b ^ k
        xor_bytes.append(masked)
        out_chars.append(CHAR_LIST[masked])

    encoded = "".join(out_chars)

    if not debug:
        return EncodeResult(encoded=encoded)

    return EncodeResult(
        encoded=encoded,
        input_bytes=data,
        key_bytes=key_slice,
        xor_bytes=bytes(xor_bytes),
        input_binary=to_binary(data),
        key_binary=to_binary(key_slice),
        xor_binary=to_binary(bytes(xor_bytes)),
    )

def kakushi_decode(encoded: str, keyword: str, debug: bool = False) -> DecodeResult:
    key_bytes_full = keyword_key_stream(keyword)
    key_len = len(key_bytes_full)

    masked = bytearray()
    invalid_chars: List[tuple[int, str]] = []

    for i, ch in enumerate(encoded):
        idx = REV_MAP.get(ch)
        if idx is None:
            invalid_chars.append((i, ch))
            masked.append(0)
        else:
            masked.append(idx)

    key_slice = key_bytes_full[: len(masked)]

    out_bytes = bytearray()
    for i, mb in enumerate(masked):
        k = key_bytes_full[i % key_len]
        out_bytes.append(mb ^ k)

    invalid_pos = {pos for pos, _ in invalid_chars}
    decoded_parts: List[str] = []
    pos = 0

    def next_invalid(after: int) -> int:
        nxt = min((p for p in invalid_pos if p > after), default=len(out_bytes))
        return nxt

    while pos < len(out_bytes):
        if pos in invalid_pos:
            ch = next(ch for p, ch in invalid_chars if p == pos)
            if debug:
                decoded_parts.append(f"⟦INVALID_CHAR@{pos}:{ch!r}⟧")
            else:
                decoded_parts.append(f"⟦{ch!r}?⟧")
            pos += 1
            continue

        end = next_invalid(pos)
        chunk = bytes(out_bytes[pos:end])

        try:
            decoded_parts.append(chunk.decode("utf-8", errors="strict"))
            pos = end
        except UnicodeDecodeError as e:
            good = chunk[: e.start]
            if good:
                decoded_parts.append(good.decode("utf-8", errors="strict"))

            bad_start = pos + e.start
            bad_end = pos + e.end
            bad_bytes = out_bytes[bad_start:bad_end]

            if debug:
                decoded_parts.append(f"⟦INVALID_UTF8@{bad_start}:{bytes(bad_bytes).hex()}⟧")
            else:
                if not decoded_parts or decoded_parts[-1] != "�":
                    decoded_parts.append("�")

            pos = bad_end if bad_end > bad_start else bad_start + 1

    decoded_text = "".join(decoded_parts)

    if not debug:
        return DecodeResult(decoded=decoded_text)

    return DecodeResult(
        decoded=decoded_text,
        masked_bytes=bytes(masked),
        key_bytes=key_slice,
        output_bytes=bytes(out_bytes),
        input_binary=to_binary(bytes(masked)),
        key_binary=to_binary(key_slice),
        xor_binary=to_binary(bytes(out_bytes)),
    )


if __name__ == "__main__":
    s = "隠し文章テスト"
    keyword = "ひみつ"
    print(kakushi_encode(s, keyword,False).encoded)

    s = "がぬせああゆかてみふ以経む十決む部切気当テ"
    keyword = "ひみつ"
    print(kakushi_decode(s, keyword,False).decoded)


