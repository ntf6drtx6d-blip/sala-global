import re


def normalize_person_name(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw)
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip()
