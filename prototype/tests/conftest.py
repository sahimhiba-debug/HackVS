"""Les tests ne touchent jamais les bases de var/ : tout en mémoire."""
import os

os.environ.setdefault("HACKVS_DB", ":memory:")
os.environ.setdefault("HACKVS_DECISIONS_DB", ":memory:")
