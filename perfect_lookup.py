#%%
from sapling_jubjub import * 
from sapling_generators import *
Fr_s = Fr(r_j)

#%%

base_vs = []
possible_vs = []

cand_i = 0


def test_coord(cand_v):
    extra_vs = [cand_v]

    # Test it against all sums of coordinates
    for v in possible_vs:
        comb_v = v + cand_v
        
        p = Point.from_v(comb_v)

        if not p:
            print("Not on the curve with", v)
            return None

        if p * Fr_s != Point.ZERO:
            print("Not in the largest subgroup with", v)
            return None

        print("Ok with", v)
        extra_vs.append(comb_v)
    
    return extra_vs


def search():
    while len(base_vs) < 3:
        # Search for a base point

        cand_v = find_group_hash(b'Zcash_PH', i2leosp(32, cand_i)).v
        print("Considering", cand_i, cand_v)
        cand_i += 1

        extra_vs = test_coord(cand_v)

        if extra_vs:
            base_vs.append(cand_v)
            possible_vs.extend(extra_vs)
            print("=> Added", cand_v, ",", len(extra_vs), "more possible points.\n")

    print("Bases", base_vs)
    print("Possible", possible_vs)


# search()

""" Found:
Considering 1632 Fr(51779983997538421520479557299755052873445270578713772851465218820135074246)
Ok with Fr(18372611905088487385433946659983357101887954355879737496286092836680199584970)
Ok with Fr(45648747605882624690586248172048386288129541878950585457687885861218308416154)
Ok with Fr(11585484335844921596572454323845777552326943734302685131370319997959926816611)
=> Added Fr(51779983997538421520479557299755052873445270578713772851465218820135074246) , 4 more possible points.

Bases [Fr(18372611905088487385433946659983357101887954355879737496286092836680199584970), Fr(45648747605882624690586248172048386288129541878950585457687885861218308416154), Fr(51779983997538421520479557299755052873445270578713772851465218820135074246)]
Possible [Fr(18372611905088487385433946659983357101887954355879737496286092836680199584970), Fr(45648747605882624690586248172048386288129541878950585457687885861218308416154), Fr(11585484335844921596572454323845777552326943734302685131370319997959926816611), Fr(51779983997538421520479557299755052873445270578713772851465218820135074246), Fr(18424391889086025806954426217283112154761399626458451269137558055500334659216), Fr(45700527589880163112106727729348141341002987149529299230539351080038443490400), Fr(11637264319842460018092933881145532605200389004881398904221785216780061890857)]
"""


#%%
# Double-check possible points, check for collisions.

BASES = [
    Fr(18372611905088487385433946659983357101887954355879737496286092836680199584970),
    Fr(45648747605882624690586248172048386288129541878950585457687885861218308416154),
    Fr(51779983997538421520479557299755052873445270578713772851465218820135074246),
    ]

SUMS = [
    Fr(18372611905088487385433946659983357101887954355879737496286092836680199584970),
    Fr(45648747605882624690586248172048386288129541878950585457687885861218308416154),
    Fr(11585484335844921596572454323845777552326943734302685131370319997959926816611),
    Fr(51779983997538421520479557299755052873445270578713772851465218820135074246),
    Fr(18424391889086025806954426217283112154761399626458451269137558055500334659216),
    Fr(45700527589880163112106727729348141341002987149529299230539351080038443490400),
    Fr(11637264319842460018092933881145532605200389004881398904221785216780061890857),
    ]


def isValidCoordV(v):
    p = Point.from_v(v)

    if not p:
        print("Not on the curve", v)
        return None

    if p * Fr_s != Point.ZERO:
        print("Not in the largest subgroup", v)
        return None
    
    return p

A, B, C = BASES

assert isValidCoordV(A)
assert isValidCoordV(B)
assert isValidCoordV(C)

assert isValidCoordV(A + B    )
assert isValidCoordV(A     + C)
assert isValidCoordV(    B + C)

assert isValidCoordV(A + B + C)

print("Ok")


#%% Other method with an added constant

def field_hash(D, M):
    digest = blake2s(person=D)
    digest.update(URS)
    digest.update(M)
    buf = digest.digest()
    buf = buf[:31] + bytes([buf[31] & 0b01111111])
    try:
        return Fr.from_bytes(buf)
    except ValueError:
        return None

def find_field_hash(D, M):
    i = 0
    while True:
        p = field_hash(D, M + bytes([i]))
        if p:
            return p
        i += 1
        assert i < 256


# Some field elements
A = find_field_hash(b'Zcash_PH', b'A')
B = find_field_hash(b'Zcash_PH', b'B')
C = find_field_hash(b'Zcash_PH', b'C')

sums = [
    A,
        B,
    A + B,
    #        C,
    #A +     C,
    #    B + C,
    #A + B + C,
]
print("sums", sums)


# Test a candidate constant against all sums of coordinates
def test_offset(cand_v):
    for v in sums:
        p = Point.from_v(cand_v + v)

        if not p:
            print("> Not on the curve with", v)
            return False

        if p * Fr_s != Point.ZERO:
            print("> Not in the largest subgroup with", v)
            return False

        print("> Ok with", v)

    return True



# Some point to start the search
GEN = find_group_hash(b'Zcash_PH', b'G')


def search_offset():
    cand_point = GEN

    for cand_i in range(100000):
        cand_v = cand_point.v
        print("Considering", cand_i, cand_v)

        if test_offset(cand_v):
            print("Found it!")
            return cand_i, cand_v

        cand_point = cand_point + GEN


i, OFFSET = search_offset()

#%%
"""
Considering 1929 Fr(24653999771182205033421946715000531571162253318421838043058117859994379755111)
> Ok with Fr(24707073915717348816642097223373561634747585517551836076552312772342515336418)
> Ok with Fr(19691173693360223708199891523780581728335951125904039282094150144593281130986)
> Ok with Fr(44398247609077572524841988747154143363083536643455875358646462916935796467404)
Found it!
"""

OFFSET = Fr(24653999771182205033421946715000531571162253318421838043058117859994379755111)
A      = Fr(24707073915717348816642097223373561634747585517551836076552312772342515336418)
B      = Fr(19691173693360223708199891523780581728335951125904039282094150144593281130986)

assert isValidCoordV(OFFSET)
assert isValidCoordV(OFFSET + A)
assert isValidCoordV(OFFSET     + B)
assert isValidCoordV(OFFSET + A + B)
print("OK!")
