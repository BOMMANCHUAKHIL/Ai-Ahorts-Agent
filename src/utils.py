import logging

def setup_logger(name, log_file="logs/agent.log"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(handler)
    return logger

def slugify(text):
    return "".join(c if c.isalnum() else "_" for c in text).lower()

def ensure_dirs(*paths):
    import os
    for p in paths:
        os.makedirs(p, exist_ok=True)