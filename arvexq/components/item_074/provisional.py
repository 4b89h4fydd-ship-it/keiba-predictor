"""Existing provisional label predicate, reused by confirmed-result guard."""
import re


def has_provisional_marker(text):
    return bool(re.search(r"速報|暫定", str(text or "")))
