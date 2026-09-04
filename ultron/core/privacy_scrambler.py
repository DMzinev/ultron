"""
ultron.core.privacy_scrambler
Privacy-Preserving Salted Context Scrambler & De-anonymizer.
"""

import hmac
import hashlib
import re
import os
from typing import Dict, Tuple, Optional


class PrivacyScrambler:
    """
    Scrambles code identifiers, symbols, and proprietary file paths using HMAC-SHA256 salted tokens,
    preventing data leaks when exporting context to external AI coding agents.
    Supports deterministic bidirectional recovery.
    """

    DEFAULT_SALT = "ultron_vault_privacy_salt_2026"

    @classmethod
    def _hash_token(cls, token: str, prefix: str, salt: str) -> str:
        """Generates a compact deterministic salted token (e.g. $SYM_a8f9c1)."""
        h = hmac.new(salt.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()[:8]
        return f"${prefix}_{h}"

    @classmethod
    def scramble_code_context(
        cls,
        code_text: str,
        file_path: str,
        salt: Optional[str] = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        Anonymizes code symbols, class names, function names, and file paths.
        Returns: (scrambled_text, token_to_original_mapping)
        """
        active_salt = salt or cls.DEFAULT_SALT
        mapping: Dict[str, str] = {}  # token -> original

        norm_path = str(file_path or "").replace("\\", "/")
        path_token = cls._hash_token(norm_path, "PATH", active_salt)
        mapping[path_token] = norm_path

        scrambled_text = code_text

        # 1. Identify definition tokens (class X, def X, function X, const X)
        symbol_patterns = [
            r"\bdef\s+([a-zA-Z_]\w*)",
            r"\bclass\s+([a-zA-Z_]\w*)",
            r"\bfunction\s+([a-zA-Z_]\w*)",
            r"\b(?:const|let|var)\s+([a-zA-Z_]\w*)",
            r"\bimport\s+([a-zA-Z_]\w*)",
            r"\bfrom\s+([a-zA-Z_]\w*)"
        ]

        found_symbols = set()
        for pat in symbol_patterns:
            for match in re.finditer(pat, code_text):
                sym = match.group(1)
                if len(sym) > 1 and sym not in {"self", "cls", "None", "True", "False"}:
                    found_symbols.add(sym)

        # 2. Sort symbols by length descending to prevent sub-string collision during tokenization
        sorted_symbols = sorted(list(found_symbols), key=len, reverse=True)

        for sym in sorted_symbols:
            token = cls._hash_token(sym, "SYM", active_salt)
            mapping[token] = sym
            # Replace exact word boundaries
            scrambled_text = re.sub(rf"\b{re.escape(sym)}\b", token, scrambled_text)

        # 3. Replace path in text if present
        if norm_path:
            scrambled_text = scrambled_text.replace(norm_path, path_token)

        return scrambled_text, mapping

    @classmethod
    def unscramble_text(cls, scrambled_text: str, mapping: Dict[str, str]) -> str:
        """
        Restores original identifiers from scrambled text.
        Sorts tokens by descending length to prevent prefix collisions (e.g. $SYM_1 inside $SYM_10).
        """
        if not scrambled_text or not mapping:
            return scrambled_text or ""

        result = scrambled_text
        sorted_tokens = sorted(mapping.keys(), key=len, reverse=True)

        for token in sorted_tokens:
            original = mapping[token]
            result = result.replace(token, original)

        return result
