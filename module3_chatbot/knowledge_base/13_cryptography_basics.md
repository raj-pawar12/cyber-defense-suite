# Cryptography basics

## Encryption
Symmetric encryption uses one shared key to lock and unlock data, as AES does. It is fast. Asymmetric encryption uses a public key and a private key, as RSA and elliptic curves do. It solves the problem of sharing keys. Real systems such as HTTPS use asymmetric methods to agree on a key, then symmetric encryption for the data.

## Hashing
A hash function turns data into a fixed-size fingerprint that cannot be reversed. It is used to check integrity and to store passwords. Passwords should be stored with a slow, salted hash such as bcrypt, scrypt or Argon2, never in plain text. A salt is random data added so equal passwords produce different hashes.

## Signatures and certificates
A digital signature proves who created a message and that it was not changed. Certificates link a public key to an identity, and certificate authorities vouch for them. TLS is the protocol behind HTTPS.

## Golden rule
Do not invent your own cryptography. Use well-tested libraries.
