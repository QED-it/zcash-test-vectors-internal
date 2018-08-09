#!/usr/bin/env python3
from sapling_utils import i2lebsp, leos2ip, i2leosp

# BLS12 order == JubJub field
q_j = 52435875175126190479447740508185965837690552500527637822603658699938581184513
# JubJub order
r_j = 6554484396890773809930967563523245729705921265872317281365359162392183254199

qm1d2 = 26217937587563095239723870254092982918845276250263818911301829349969290592256
assert (q_j - 1) // 2 == qm1d2


#
# Field arithmetic
#

class FieldElement(object):
    def __init__(self, t, s, modulus, strict=False):
        if strict and not (0 <= s and s < modulus):
            raise ValueError
        self.t = t
        self.s = s % modulus
        self.m = modulus

    def __add__(self, a):
        return self.t(self.s + a.s)

    def __sub__(self, a):
        return self.t(self.s - a.s)

    def __mul__(self, a):
        return self.t(self.s * a.s)

    def __truediv__(self, a):
        assert a.s != 0
        return self * a.inv()

    def exp(self, e):
        e = format(e, '0256b')
        ret = self.t(1)
        for c in e:
            ret = ret * ret
            if int(c):
                ret = ret * self
        return ret

    def inv(self):
        return self.exp(self.m - 2)

    def bits(self, l):
        return i2lebsp(l, self.s)

    def __bytes__(self):
        return i2leosp(256, self.s)

    def __eq__(self, a):
        return self.s == a.s



class Fr(FieldElement):
    @staticmethod
    def from_bytes(buf):
        return Fr(leos2ip(buf), strict=True)

    def __init__(self, s, strict=False):
        FieldElement.__init__(self, Fr, s, q_j, strict=strict)

    def __str__(self):
        return 'Fr(%s)' % self.s

    def sqrt(self):
        # Tonelli-Shank's algorithm for q mod 16 = 1
        # https://eprint.iacr.org/2012/685.pdf (page 12, algorithm 5)
        a = self.exp(qm1d2)
        if a == self.ONE:
            c = Fr(10238227357739495823651030575849232062558860180284477541189508159991286009131)
            r = self.exp(6104339283789297388802252303364915521546564123189034618274734669824)
            t = self.exp(12208678567578594777604504606729831043093128246378069236549469339647)
            m = 32

            # 7: while b != 1 do
            while t != self.ONE:
                # 8: Find least integer k >= 0 such that b^(2^k) == 1
                i = 1
                t2i = t * t
                while t2i != self.ONE:
                    t2i = t2i * t2i
                    i += 1
                assert i < m

                # 9:
                # w <- z^(2^(v-k-1))
                for _ in range(0, m - i - 1):
                    c = c * c
                # b <- bz
                r = r * c
                # z <- w^2
                c = c * c
                # x <- xw
                t = t * c
                # v <- k
                m = i
            assert r * r == self
            return r
        elif a == self.MINUS_ONE:
            return None
        return self.ZERO


class Fs(FieldElement):
    def __init__(self, s, strict=False):
        FieldElement.__init__(self, Fs, s, r_j, strict=strict)

    def __str__(self):
        return 'Fs(%s)' % self.s

Fr.ZERO = Fr(0)
Fr.ONE = Fr(1)
Fr.MINUS_ONE = Fr(-1)

assert Fr.ZERO + Fr.ZERO == Fr.ZERO
assert Fr.ZERO + Fr.ONE == Fr.ONE
assert Fr.ONE + Fr.ZERO == Fr.ONE
assert Fr.ZERO - Fr.ONE == Fr.MINUS_ONE
assert Fr.ZERO * Fr.ONE == Fr.ZERO
assert Fr.ONE * Fr.ZERO == Fr.ZERO

_A = Fr(-13443226831829260228624682877674385705155231329884953466695813022153219761455)
_A_SQUARED = Fr(1615918303262283860389448007513155112015187847020867660361132469416696757234)
assert _A * _A == _A_SQUARED
assert _A.exp(2) == _A_SQUARED
assert _A_SQUARED.sqrt() == _A


#
# Point arithmetic
#

JUBJUB_A = Fr.MINUS_ONE
JUBJUB_D = Fr(-10240) / Fr(10241)
JUBJUB_COFACTOR = Fs(8)

class Point(object):
    @staticmethod
    def from_bytes(buf):
        assert len(buf) == 32
        u_sign = buf[31] >> 7
        buf = buf[:31] + bytes([buf[31] & 0b01111111])
        try:
            v = Fr.from_bytes(buf)
        except ValueError:
            return None

        vv = v * v
        u2 = (vv - Fr.ONE) / (vv * JUBJUB_D - JUBJUB_A)

        u = u2.sqrt()
        if not u:
            return None

        if u.s % 2 != u_sign:
            u = Fr.ZERO - u

        return Point(u, v)

    def __init__(self, u, v):
        self.u = u
        self.v = v

    def __add__(self, a):
        (u1, v1) = (self.u, self.v)
        (u2, v2) = (a.u, a.v)
        u3 = (u1*v2 + v1*u2) / (Fr.ONE + JUBJUB_D*u1*u2*v1*v2)
        v3 = (v1*v2 - JUBJUB_A*u1*u2) / (Fr.ONE - JUBJUB_D*u1*u2*v1*v2)
        return Point(u3, v3)

    def double(self):
        return self + self

    def __mul__(self, s):
        s = format(s.s, '0256b')
        ret = self.ZERO
        for c in s:
            ret = ret.double()
            if int(c):
                ret = ret + self
        return ret

    def __bytes__(self):
        buf = bytes(self.v)
        if self.u.s % 2 == 1:
            buf = buf[:31] + bytes([buf[31] | (1 << 7)])
        return buf

    def __eq__(self, a):
        return self.u == a.u and self.v == a.v

    def __str__(self):
        return 'Point(%s, %s)' % (self.u, self.v)


Point.ZERO = Point(Fr.ZERO, Fr.ONE)

assert Point.ZERO + Point.ZERO == Point.ZERO
