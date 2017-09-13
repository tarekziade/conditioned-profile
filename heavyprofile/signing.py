import hashlib
from heavyprofile import logger

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


def verify_signature(filename, pem_file, pem_password, founded_hash=None):
    if founded_hash is None:
        founded_hash = hashlib.sha256()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                founded_hash.update(chunk)
        founded_hash = founded_hash.hexdigest()
        founded_hash = bytes(founded_hash, 'utf8')

    backend = default_backend()

    with open(pem_file, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(),
                                                         password=pem_password,
                                                         backend=backend)
    public_key = private_key.public_key()
    pad = padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                      salt_length=padding.PSS.MAX_LENGTH)

    with open(filename + '.asc', 'rb') as f:
        signature = f.read()
    try:
        public_key.verify(signature, founded_hash, pad, hashes.SHA256())
    except InvalidSignature:
        raise ValueError("Bad Signature")


def sign_file(filename, hash, pem_file, password):
    logger.msg("Creating %s.asc..." % filename)
    backend = default_backend()

    with open(pem_file, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(),
                                                         password=password,
                                                         backend=backend)

    pad = padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                      salt_length=padding.PSS.MAX_LENGTH)
    signature = private_key.sign(hash, pad, hashes.SHA256())
    with open(filename + '.asc', 'wb') as f:
        f.write(signature)


def create_key(pem_file, password):
    private_key = rsa.generate_private_key(public_exponent=65537,
                                           key_size=2048,
                                           backend=default_backend())
    alg = serialization.BestAvailableEncryption(password)
    pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                    format=serialization.PrivateFormat.PKCS8,
                                    encryption_algorithm=alg)
    with open(pem_file, 'wb') as f:
        for line in pem.splitlines():
            f.write(line + b'\n')
