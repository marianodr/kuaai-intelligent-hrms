import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
    """
    Configura el sistema de logging para toda la aplicación.
    - Console: nivel configurable (stdout/stderr, visible en Docker)
    - Archivo rotativo: nivel DEBUG siempre (captura todo para diagnóstico)
    - Librerías ruidosas (docling, transformers) se silencian a WARNING
    """
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Evitar handlers duplicados si setup_logging se llama más de una vez
    if root.handlers:
        root.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console.setFormatter(fmt)
    root.addHandler(console)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB por archivo
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)

    # Silenciar librerías externas que generan mucho ruido
    for noisy in (
        "docling",
        "transformers",
        "sentence_transformers",
        "httpx",
        "httpcore",
        "urllib3",
        "multipart",
        "RapidOCR",       # logger nombrado así en el código fuente de rapidocr
        "rapidocr",       # submodulos como rapidocr.base, rapidocr.main, etc.
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)
