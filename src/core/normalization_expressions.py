import re

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")

URL_RE = re.compile(r"https?://[^\s]+")

UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}\b"
)

IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")

JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+\b")

PATH_RE = re.compile(r"(?:[a-zA-Z]:\\[^\s]+|(?:/[^/\s]+)+)")

NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

NORMALIZATION_RULES = [
    (EMAIL_RE, "<email>"),
    (URL_RE, "<url>"),
    (UUID_RE, "<uuid>"),
    (IP_RE, "<ip>"),
    (JWT_RE, "<token>"),
    (PATH_RE, "<path>"),
    (NUMBER_RE, "<number>"),
]
