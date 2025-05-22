import json
import re
from typing import Dict, List

class ReplacementRule:
    def __init__(self, match: str, replace: str, is_regex: bool = False):
        self.match = match
        self.replace = replace
        self.is_regex = is_regex
        if is_regex:
            self.compiled_re = re.compile(match)

class VocxConverter:
    def __init__(self):
        self.rules = json.loads(default_rules)
        self._prepare_rules()

    def _prepare_rules(self):
        # Buchstaben-Regeln
        self.letter_rules = {k: v for k, v in self.rules["letters"].items()}

        # Fragment-Regeln (mit Regex-Unterstützung)
        self.fragment_rules = []
        for rule in self.rules["fragments"]:
            is_regex = rule["match"].startswith('^') or rule["match"].endswith('\\b')
            self.fragment_rules.append(
                ReplacementRule(rule["match"], rule["replace"], is_regex)
            )

        # Override-Regeln (exakte Übereinstimmungen)
        self.override_rules = {
            override["eo"]: override["pl"]
            for override in self.rules["overrides"]
        }

        # Zahlen-Regeln
        self.number_rules = {k: v for k, v in self.rules["numbers"].items()}

    def convert(self, text: str) -> str:
        # 1. Override-Regeln zuerst anwenden (ganze Wörter)
        words = text.split()
        for i, word in enumerate(words):
            lower_word = word.lower()
            if lower_word in self.override_rules:
                words[i] = self.override_rules[lower_word]

        text = ' '.join(words)

        # 2. Zahlen ersetzen
        for num, repl in self.number_rules.items():
            text = text.replace(num, repl)

        # 3. Fragment-Regeln anwenden
        for rule in self.fragment_rules:
            if rule.is_regex:
                text = rule.compiled_re.sub(rule.replace, text)
            else:
                text = text.replace(rule.match, rule.replace)

        # 4. Einzelne Buchstaben ersetzen
        result = []
        for char in text:
            if char in self.letter_rules:
                result.append(self.letter_rules[char])
            else:
                result.append(char)

        return ''.join(result)

# Die Standardregeln als JSON-String
default_rules = '''
{
    "letters": {
        "a": "a",
        "b": "b",
        "c": "ts",
        "ĉ": "cz",
        "d": "d",
        "e": "e",
        "f": "f",
        "g": "g",
        "ĝ": "dż",
        "h": "h",
        "ĥ": "ch",
        "i": "ij",
        "j": "y",
        "ĵ": "rz",
        "k": "k",
        "l": "l",
        "m": "m",
        "n": "n",
        "o": "o",
        "p": "p",
        "r": "r",
        "s": "s",
        "ŝ": "sz",
        "t": "t",
        "u": "u",
        "ŭ": "ł",
        "v": "w",
        "z": "z"
    },
    "fragments": [
        { "match": "tsx", "replace": "cz" },
        { "match": "gx", "replace": "dż" },
        { "match": "hx", "replace": "ch" },
        { "match": "yx", "replace": "rz" },
        { "match": "sx", "replace": "sz" },
        { "match": "ux", "replace": "ł" },
        { "match": "atsij", "replace": "atssij" },
        { "match": "ide\\b", "replace": "ijde" },
        { "match": "io\\b", "replace": "ijo" },
        { "match": "ioy\\b", "replace": "ijoj" },
        { "match": "ioyn\\b", "replace": "ijojn" },
        { "match": "feyo\\b", "replace": "fejo" },
        { "match": "feyoy\\b", "replace": "feyoj" },
        { "match": "feyoyn\\b", "replace": "feyoj" },
        { "match": "^ekzij", "replace": "ekzji" },
        { "match": "tssijl", "replace": "tssil" },
        { "match": "ijuy", "replace": "iuyy" },
        { "match": "ijeh", "replace": "ije" },
        { "match": "sijlo", "replace": "ssilo" },
        { "match": "^sij", "replace": "syy" },
        { "match": "tsij", "replace": "tssij" },
        { "match": "sij", "replace": "ssij" },
        { "match": "sssij", "replace": "ssij" },
        { "match": "rijpozij", "replace": "ryypozyj" },
        { "match": "zijs", "replace": "zyjs" }
    ],
    "overrides": [
        { "eo": "ok", "pl": "ohk" },
        { "eo": "s-ro", "pl": "sjijnjoro" },
        { "eo": "s-ino", "pl": "sjijnjorijno" },
        { "eo": "ktp", "pl": "ko-to-po" },
        { "eo": "k.t.p", "pl": "ko-to-po" },
        { "eo": "atm", "pl": "antałtagmeze" },
        { "eo": "ptm", "pl": "posttagmeze" },
        { "eo": "bv", "pl": "bonvolu" }
    ],
    "numbers": {
        "0": "nulo",
        "1": "unu",
        "2": "du",
        "3": "trij",
        "4": "kvar",
        "5": "kvijn",
        "6": "ses",
        "7": "sep",
        "8": "ohk",
        "9": "nał",
        "10": "dek",
        "100": "tsent",
        "1000": "mijl",
        "1000000": "mijlijono"
    }
}
'''

_converter = VocxConverter()

def convert_text(text: str) -> str:
    """Haupt-API: Text konvertieren"""
    return _converter.convert(text)

if __name__ == "__main__":
    # CLI-Fallback
    import sys
    if len(sys.argv) > 1:
        print(convert_text(sys.argv[1]))
