import hashlib
from heavyprofile import logger

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


class Signer(object):
    def __init__(self, pem_file=None, pem_password=None):
        self.pem_file = pem_file
        self.pem_password = pem_password
        if pem_file is None:
            self.pub = self.pad = self.backend = None
        else:
            self.backend = default_backend()
            with open(self.pem_file, 'rb') as f:
                self.priv = load_pem_private_key(f.read(),
                                                 password=pem_password,
                                                 backend=self.backend)

            self.pub = self.priv.public_key()
            self.pad = padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                   salt_length=padding.PSS.MAX_LENGTH)

    def verify(self, filename, file_hash=None):
        if self.pem_file is None:
            raise ValueError("No PEM loaded")

        if file_hash is None:
            file_hash = hashlib.sha256()
            with open(filename, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
            file_hash = file_hash.hexdigest()
            file_hash = bytes(file_hash, 'utf8')
        else:
            # verify hash
            with open(filename + '.sha256') as f:
                actual_hash = f.read()
            if file_hash != actual_hash:
                raise ValueError("Wrong Hash")

        # verify signature
        with open(filename + '.asc', 'rb') as f:
            signature = f.read()
        try:
            self.pub.verify(signature, file_hash, self.pad, hashes.SHA256())
        except InvalidSignature:
            raise ValueError("Bad Signature")

    def checksum(self, filename, write=False, sign=False):
        hash = hashlib.sha256()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash.update(chunk)

        if write:
            check = filename + ".sha256"
            logger.msg("Creating %s..." % check)
            with open(check, "w") as f:
                f.write(hash.hexdigest())
            if sign:
                bhash = bytes(hash.hexdigest(), 'utf8')
                self.sign(filename, bhash)
        return hash.hexdigest()

    def sign(self, filename, hash):
        if self.pem_file is None:
            raise ValueError("No PEM loaded")
        ascfile = filename + '.asc'
        logger.msg("Creating %s..." % ascfile)
        signature = self.priv.sign(hash, self.pad, hashes.SHA256())
        with open(ascfile, 'wb') as f:
            f.write(signature)
        return ascfile


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
