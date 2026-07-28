# backend/core/logger.py
import logging, os
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("AI-Digital-Company")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
ch = logging.StreamHandler(); ch.setFormatter(fmt)
fh = logging.FileHandler("logs/app.log"); fh.setFormatter(fmt)
if not logger.handlers:
    logger.addHandler(ch); logger.addHandler(fh)
