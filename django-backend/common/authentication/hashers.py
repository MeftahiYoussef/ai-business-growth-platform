from django.contrib.auth.hashers import BasePasswordHasher, mask_hash
from django.utils.crypto import constant_time_compare


class NodeBcryptPasswordHasher(BasePasswordHasher):
    """
    Verifies migrated Express bcrypt hashes stored as bcrypt$<original_hash>.
    New passwords use Django's default PBKDF2 hasher.
    """

    algorithm = "bcrypt"

    def salt(self):
        return ""

    def encode(self, password, salt):
        raise NotImplementedError("Node bcrypt compatibility hasher verifies migrated hashes only")

    def verify(self, password, encoded):
        if not encoded.startswith("bcrypt$"):
            return False
        try:
            import bcrypt
        except ImportError:
            return False
        raw_hash = encoded.split("$", 1)[1].encode("utf-8")
        return constant_time_compare(bcrypt.checkpw(password.encode("utf-8"), raw_hash), True)

    def safe_summary(self, encoded):
        return {"algorithm": self.algorithm, "hash": mask_hash(encoded, show=6)}

    def harden_runtime(self, password, encoded):
        return None
