# Background

A hash-based commitment lets a bidder submit a value that can later be checked against the revealed bid. We use SHA-256, which produces a 256-bit digest [1]. To open a commitment, the bidder discloses the bid and the randomness used to create it; the verifier then recomputes the digest. This involves no decryption. A commitment is also not a digital signature and does not establish the sender's identity.

Collision resistance means that finding two different inputs with the same digest is computationally difficult [2]. It does not, by itself, keep a bid secret. For example, a bid range of VND 10,000 to 1,000,000 in steps of VND 10,000 contains only 100 possibilities. If the commitment is H(b), an observer can hash each candidate and compare the results. This exploits the small input space without breaking SHA-256.

Our model therefore includes a fresh, independently generated 128-bit random value r, kept secret until reveal. Its unpredictability matters as much as its length: a long but predictable value offers little protection. We also use unambiguous encoding with a fixed field order and explicit length prefixes, so different field combinations cannot become the same byte string before hashing. With unambiguous encoding and a fixed commitment record, collision resistance supports binding. Hiding needs suitable randomness and an additional assumption about the hash function, such as the random oracle model [2].

## References

[1] National Institute of Standards and Technology, Secure Hash Standard (SHS), FIPS PUB 180-4, August 2015, Sec. 1, Fig. 1, p. 3.

[Source](https://doi.org/10.6028/NIST.FIPS.180-4)

[2] MIT 6.5610, Recitation 6: Hash functions, March 17, 2023, Sec. 1, p. 1.

[Source](https://65610.csail.mit.edu/2023/rec/rec6.pdf)
