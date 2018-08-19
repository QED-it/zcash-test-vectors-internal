#!/usr/bin/env python3
from sapling_generators import (
    find_group_hash,
    NOTE_POSITION_BASE,
    WINDOWED_PEDERSEN_RANDOMNESS_BASE,
)
from sapling_jubjub import Fs, Point
from sapling_utils import cldiv, i2leosp


#
# Pedersen hashes
#

def I_D_i(D, i):
    return find_group_hash(D, i2leosp(32, i - 1))

def assert_binary(i):
    assert i * (1 - i) == 0, "Expected 0 or 1, found %i" % i

def encode_chunk(mj):
    (s0, s1, s2) = mj
    assert_binary(s0)
    assert_binary(s1)
    assert_binary(s2)
    return (1 - 2*s2) * (1 + s0 + 2*s1)

def encode_segment(Mi):
    ki = len(Mi) // 3
    Michunks = [Mi[i:i+3] for i in range(0, len(Mi), 3)]
    assert len(Michunks) == ki
    return Fs(sum([encode_chunk(Michunks[j-1]) * 2**(4*(j-1)) for j in range(1, ki + 1)]))

c = 63

def pedersen_hash_to_point(D, M):
    # Pad M to a multiple of 3 bits
    Mdash = M + [0] * ((-len(M)) % 3)
    assert (len(Mdash) // 3) * 3 == len(Mdash)
    n = cldiv(len(Mdash), 3 * c)
    Msegs = [Mdash[i:i+(3*c)] for i in range(0, len(Mdash), 3*c)]
    assert len(Msegs) == n
    return sum([I_D_i(D, i) * encode_segment(Msegs[i-1]) for i in range(1, n + 1)], Point.ZERO)

def pedersen_hash(D, M):
    return pedersen_hash_to_point(D, M).u.bits(255)

def mixing_pedersen_hash(P, x):
    return P + NOTE_POSITION_BASE * x


#
# Pedersen commitments
#

def windowed_pedersen_commitment(r, s):
    return pedersen_hash_to_point(b'Zcash_PH', s) + WINDOWED_PEDERSEN_RANDOMNESS_BASE * r

def homomorphic_pedersen_commitment(rcv, D, v):
    return find_group_hash(D, b'v') * v + find_group_hash(D, b'r') * rcv


template = '''
/// Test vectors from https://github.com/zcash-hackworks/zcash-test-vectors/blob/master/sapling_pedersen.py

use pedersen_hash::Personalization;
use pedersen_hash::test::TestVector;


pub fn get_vectors<'a>() -> Vec<TestVector<'a>> {
    return vec![
{% for v in vectors %}
        TestVector {
            personalization: Personalization::{{ v.personalization }},
            input_bits: vec!{{ v.input_bits }},
            hash_x: "Fr({{ v.hash_x }})",
            hash_y: "Fr({{ v.hash_y }})",
        },
{% endfor %}
    ];
}

'''

def int_to_hex(i):
    return "0x{:064x}".format(i)


def main():
    from jinja2 import Template

    import random
    rd = random.Random("Pedersen hash test vectors")

    def sample_bits(k):
        x = rd.getrandbits(k)
        return [(x >> i) & 1 for i in range(k)]

    vectors = []

    # Random inputs
    for (pers_name, pers_bits) in [
        ("NoteCommitment", [1, 1, 1, 1, 1, 1]),
        ("MerkleTree(0)",  [0, 0, 0, 0, 0, 0]),
        ("MerkleTree(34)", [0, 1, 0, 0, 0, 1]), # 34 in left-to-right binary
    ]:
        for bits in [
            [],
            [0],
            [1],
            [1, 0, 0], # Same hash due to 3-bits padding
            sample_bits(3 * 62 - 6),
            sample_bits(3 * 63 - 6),
            sample_bits(3 * 63 + 1 - 6),
            sample_bits(3 * 63 * 4 - 6),
            sample_bits(3 * 63 * 4 + 1 - 6),
            sample_bits(3 * 63 * 5 - 6),
            sample_bits(3 * 63 * 5 + 1 - 6),
        ]:
            all_bits = pers_bits + bits
            ph = pedersen_hash_to_point(b'Zcash_PH', all_bits)
            vectors.append({
                "personalization": pers_name,
                "input_bits": all_bits,
                "hash_x": int_to_hex(ph.u.s),
                "hash_y": int_to_hex(ph.v.s),
            })

    # Edge-cases
    for (pers_name, pers_bits, bits) in [
        ("MerkleTree(27)",  [1, 1, 0, 1, 1, 0], [1, 1, 0] * 61), # 63 chunks with c=0
        ("MerkleTree(36)",  [0, 0, 1, 0, 0, 1], [0, 0, 1] * 61), # 63 chunks with c=1
        ("MerkleTree(0)",   [0, 0, 0, 0, 0, 0], [0, 0, 0] * 61), # 63 chunks all 0
        ("NoteCommitment",  [1, 1, 1, 1, 1, 1], [1, 1, 1] * 61), # 63 chunks all 1
    ]:
        all_bits = pers_bits + bits
        ph = pedersen_hash_to_point(b'Zcash_PH', all_bits)
        vectors.append({
            "personalization": pers_name,
            "input_bits": all_bits,
            "hash_x": int_to_hex(ph.u.s),
            "hash_y": int_to_hex(ph.v.s),
        })

    rust = Template(template).render(vectors=vectors)

    out_path = "pedersen_hash_vectors.rs"
    with open(out_path, "w") as fd:
        fd.write(rust)
    print("Test vectors save to", out_path)
    print("Move it to sapling-crypto/src/tests")


if __name__ == '__main__':
    main()
