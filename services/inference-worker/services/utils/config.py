import os

def load_default_envs():
    os.environ.setdefault("HOME_PATH", "/app")
    os.environ.setdefault("BASE_DIR", os.path.join(os.getenv("HOME_PATH"), "data"))
    os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-3-small")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    os.environ.setdefault("MODEL", "gpt-4o")
    os.environ.setdefault("USER_AGENT", "chicory_ai")
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
