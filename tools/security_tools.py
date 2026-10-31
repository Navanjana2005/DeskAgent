

import os
import re
import secrets
import string
import hashlib
import ast
import math
import operator
from langchain_core.tools import tool

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = True,
) -> str:
    """Generates a cryptographically secure random password.

    Args:
        length: Password length (default 16, min 8, max 128).
        use_uppercase: Include uppercase letters A-Z (default True).
        use_digits: Include digits 0-9 (default True).
        use_symbols: Include special symbols !@#$%^&* etc. (default True).
        exclude_ambiguous: Exclude ambiguous characters like 0/O, 1/l/I (default True).
    """
    try:
        length = max(8, min(128, length))
        chars = string.ascii_lowercase
        if use_uppercase:
            chars += string.ascii_uppercase
        if use_digits:
            chars += string.digits
        if use_symbols:
            chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        if exclude_ambiguous:
            for ch in "0O1lI|`'\"":
                chars = chars.replace(ch, "")

        if not chars:
            return "❌ No character set selected."

        # Guarantee at least one of each required type
        password_chars = []
        if use_uppercase:
            uc = string.ascii_uppercase
            if exclude_ambiguous:
                uc = uc.replace("O", "").replace("I", "")
            password_chars.append(secrets.choice(uc))
        if use_digits:
            dg = string.digits
            if exclude_ambiguous:
                dg = dg.replace("0", "").replace("1", "")
            password_chars.append(secrets.choice(dg))
        if use_symbols:
            sym = "!@#$%^&*()-_=+[]{}|;:,.<>?"
            password_chars.append(secrets.choice(sym))

        # Fill the rest
        remaining = length - len(password_chars)
        password_chars += [secrets.choice(chars) for _ in range(remaining)]
        secrets.SystemRandom().shuffle(password_chars)
        password = "".join(password_chars)

        # Strength indicator
        entropy_bits = length * (len(chars) ** 0.5)
        if length >= 16 and use_uppercase and use_digits and use_symbols:
            strength = "💪 Very Strong"
        elif length >= 12:
            strength = "✅ Strong"
        elif length >= 8:
            strength = "⚠️  Moderate"
        else:
            strength = "❌ Weak"

        return (
            f"🔑 Generated Password:\n"
            f"{'─' * 40}\n"
            f"  {password}\n"
            f"{'─' * 40}\n"
            f"Length:   {length} characters\n"
            f"Strength: {strength}\n"
            f"Charset:  {len(chars)} unique characters"
        )
    except Exception as e:
        return f"❌ Error generating password: {e}"


@tool
def check_password_strength(password: str) -> str:
    """Analyzes the strength of a password and gives improvement suggestions.

    Args:
        password: The password to analyze.
    """
    try:
        score = 0
        feedback = []

        length = len(password)
        if length >= 16:
            score += 3
        elif length >= 12:
            score += 2
        elif length >= 8:
            score += 1
        else:
            feedback.append("❌ Too short — use at least 12 characters")

        has_lower = bool(re.search(r"[a-z]", password))
        has_upper = bool(re.search(r"[A-Z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_symbol = bool(re.search(r"[!@#$%^&*()\-_=+\[\]{}|;:,.<>?]", password))

        if has_lower:
            score += 1
        else:
            feedback.append("❌ Add lowercase letters (a-z)")
        if has_upper:
            score += 1
        else:
            feedback.append("❌ Add uppercase letters (A-Z)")
        if has_digit:
            score += 1
        else:
            feedback.append("❌ Add numbers (0-9)")
        if has_symbol:
            score += 2
        else:
            feedback.append("❌ Add symbols (!@#$%^&*)")

        # Check for common patterns
        if re.search(r"(.)\1{2,}", password):
            score -= 1
            feedback.append("⚠️  Avoid repeated characters (aaa, 111)")
        if re.search(r"(012|123|234|345|456|567|678|789|abc|bcd|cde|def)", password.lower()):
            score -= 1
            feedback.append("⚠️  Avoid sequential characters (123, abc)")

        score = max(0, min(8, score))
        if score >= 7:
            rating = "💪 Very Strong"
        elif score >= 5:
            rating = "✅ Strong"
        elif score >= 3:
            rating = "⚠️  Moderate"
        elif score >= 1:
            rating = "❗ Weak"
        else:
            rating = "❌ Very Weak"

        result = [
            f"🔐 Password Strength Analysis",
            f"{'─' * 35}",
            f"Strength: {rating}  (Score: {score}/8)",
            f"Length:   {length} characters",
            f"Lowercase: {'✅' if has_lower else '❌'}  Uppercase: {'✅' if has_upper else '❌'}",
            f"Numbers:   {'✅' if has_digit else '❌'}  Symbols:   {'✅' if has_symbol else '❌'}",
        ]
        if feedback:
            result.append("\n💡 Suggestions:")
            result.extend(f"   {f}" for f in feedback)
        return "\n".join(result)
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# FILE HASH
# ─────────────────────────────────────────────────────────────────────────────

@tool
def hash_file(file_path: str, algorithm: str = "sha256") -> str:
    """Calculates the cryptographic hash of a file for integrity verification.

    Args:
        file_path: Path to the file.
        algorithm: Hash algorithm: 'md5', 'sha1', 'sha256', or 'sha512' (default 'sha256').
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"

        algo = algorithm.lower()
        if algo not in ("md5", "sha1", "sha256", "sha512"):
            return f"❌ Unsupported algorithm '{algo}'. Use: md5, sha1, sha256, sha512"

        h = hashlib.new(algo)
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)

        return (
            f"🔒 File Hash\n"
            f"{'─' * 50}\n"
            f"File:      {os.path.basename(file_path)}\n"
            f"Size:      {file_size / 1024:.2f} KB\n"
            f"Algorithm: {algo.upper()}\n"
            f"Hash:      {h.hexdigest()}"
        )
    except Exception as e:
        return f"❌ Error hashing file: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# ENCRYPTION TOOLS
# ─────────────────────────────────────────────────────────────────────────────

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derives a Fernet-compatible key from a password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


@tool
def encrypt_file(file_path: str, password: str, output_path: str = "") -> str:
    """Encrypts a file using AES-256 (Fernet/PBKDF2) with a password.

    Args:
        file_path: Path to the file to encrypt.
        password: Password used for encryption. Remember this — it's needed for decryption!
        output_path: Where to save the encrypted file (defaults to file_path + '.enc').
    """
    if not HAS_CRYPTO:
        return "❌ cryptography not installed. Run: pip install cryptography"
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        if not output_path:
            output_path = file_path + ".enc"

        salt = secrets.token_bytes(16)
        key = _derive_key(password, salt)
        fernet = Fernet(key)

        with open(file_path, "rb") as f:
            data = f.read()

        encrypted = fernet.encrypt(data)
        with open(output_path, "wb") as f:
            f.write(salt + encrypted)  # prepend 16-byte salt

        orig_size = len(data) / 1024
        enc_size = os.path.getsize(output_path) / 1024
        return (
            f"🔒 File encrypted successfully!\n"
            f"Original:  {file_path} ({orig_size:.2f} KB)\n"
            f"Encrypted: {output_path} ({enc_size:.2f} KB)\n"
            f"⚠️  Keep your password safe — without it, the file cannot be decrypted."
        )
    except Exception as e:
        return f"❌ Error encrypting file: {e}"


@tool
def decrypt_file(encrypted_path: str, password: str, output_path: str = "") -> str:
    """Decrypts a file that was previously encrypted with encrypt_file.

    Args:
        encrypted_path: Path to the .enc encrypted file.
        password: The same password used during encryption.
        output_path: Where to save the decrypted file (defaults to removing '.enc' suffix).
    """
    if not HAS_CRYPTO:
        return "❌ cryptography not installed. Run: pip install cryptography"
    try:
        if not os.path.exists(encrypted_path):
            return f"❌ File not found: {encrypted_path}"
        if not output_path:
            output_path = encrypted_path.removesuffix(".enc") if encrypted_path.endswith(".enc") else encrypted_path + ".dec"

        with open(encrypted_path, "rb") as f:
            raw = f.read()

        salt = raw[:16]
        encrypted_data = raw[16:]
        key = _derive_key(password, salt)
        fernet = Fernet(key)

        decrypted = fernet.decrypt(encrypted_data)
        with open(output_path, "wb") as f:
            f.write(decrypted)

        return (
            f"🔓 File decrypted successfully!\n"
            f"Encrypted: {encrypted_path}\n"
            f"Decrypted: {output_path} ({len(decrypted) / 1024:.2f} KB)"
        )
    except Exception as e:
        if "InvalidToken" in str(type(e)):
            return "❌ Decryption failed — wrong password or corrupted file."
        return f"❌ Error decrypting file: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# RANDOM UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

@tool
def random_number(mode: str = "int", min_val: float = 1, max_val: float = 100) -> str:
    """Generates random numbers, rolls dice, or flips a coin.

    Args:
        mode: 'int' (integer), 'float' (decimal), 'dice' (roll NdM format), or 'coin' (flip).
        min_val: Minimum value for int/float modes (default 1).
        max_val: Maximum value for int/float modes (default 100).

    Examples:
        mode='int', min_val=1, max_val=10  → random integer 1-10
        mode='float', min_val=0, max_val=1 → random float 0.0-1.0
        mode='dice', min_val=6, max_val=1  → roll 1 six-sided die (min_val=sides, max_val=count)
        mode='coin'                         → flip a coin
    """
    try:
        mode = mode.lower()
        if mode == "coin":
            result = secrets.choice(["Heads", "Tails"])
            return f"🪙 Coin flip: {result}"

        elif mode == "dice":
            sides = int(min_val) or 6
            count = int(max_val) or 1
            rolls = [secrets.randbelow(sides) + 1 for _ in range(count)]
            total = sum(rolls)
            rolls_str = " + ".join(map(str, rolls))
            return f"🎲 Rolled {count}d{sides}: {rolls_str} = {total}"

        elif mode == "float":
            import random
            result = random.uniform(min_val, max_val)
            return f"🎯 Random float [{min_val}, {max_val}]: {result:.6f}"

        else:  # int
            lo, hi = int(min(min_val, max_val)), int(max(min_val, max_val))
            result = secrets.randbelow(hi - lo + 1) + lo
            return f"🎯 Random integer [{lo}, {hi}]: {result}"
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

@tool
def calculate(expression: str) -> str:
    """Safely evaluates a mathematical expression.

    Args:
        expression: Math expression to evaluate (e.g., '2 + 2', '(15 * 4) / 3', 'sqrt(144)', 'pi * 5**2').

    Supported: +, -, *, /, //, %, **, sqrt(), abs(), round(), sin(), cos(), tan(),
               log(), log10(), floor(), ceil(), pi, e
    """
    try:
        result = _evaluate_math_expression(expression)
        return f"🧮 {expression} = {result}"
    except ZeroDivisionError:
        return "❌ Division by zero."
    except Exception as e:
        return f"❌ Error evaluating expression: {e}"


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _bounded_factorial(value):
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 1000:
        raise ValueError("factorial accepts integers from 0 to 1000.")
    return math.factorial(value)


def _bounded_power(base, exponent):
    if not isinstance(exponent, (int, float)) or abs(exponent) > 1000:
        raise ValueError("Exponent magnitude must not exceed 1000.")
    return operator.pow(base, exponent)


_MATH_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "floor": math.floor,
    "ceil": math.ceil,
    "pow": _bounded_power,
    "exp": math.exp,
    "factorial": _bounded_factorial,
    "gcd": math.gcd,
}
_MATH_CONSTANTS = {"pi": math.pi, "e": math.e, "inf": math.inf}


def _evaluate_math_expression(expression: str):
    if len(expression) > 512:
        raise ValueError("Expression is too long.")

    tree = ast.parse(expression, mode="eval")
    nodes = list(ast.walk(tree))
    if len(nodes) > 100:
        raise ValueError("Expression contains too many operations.")

    def evaluate(node, depth=0):
        if depth > 20:
            raise ValueError("Expression is nested too deeply.")

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.Name) and node.id in _MATH_CONSTANTS:
            return _MATH_CONSTANTS[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = evaluate(node.left, depth + 1)
            right = evaluate(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("Exponent magnitude must not exceed 1000.")
            result = _BINARY_OPERATORS[type(node.op)](left, right)
            if isinstance(result, int) and result.bit_length() > 4096:
                raise ValueError("Integer result is too large.")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _UNARY_OPERATORS[type(node.op)](evaluate(node.operand, depth + 1))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _MATH_FUNCTIONS
            and not node.keywords
        ):
            arguments = [evaluate(argument, depth + 1) for argument in node.args]
            result = _MATH_FUNCTIONS[node.func.id](*arguments)
            if isinstance(result, int) and result.bit_length() > 4096:
                raise ValueError("Integer result is too large.")
            return result
        raise ValueError("Expression contains an unsupported operation.")

    return evaluate(tree.body)
