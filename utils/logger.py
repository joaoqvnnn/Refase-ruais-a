# ==============================================
# LARIZINHA STORE - CONFIGURAÇÃO DE LOGGING
# ==============================================

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(name: str, level: str = "INFO", log_file: str = "bot.log") -> logging.Logger:
    """
    Configura e retorna um logger com saída para console e arquivo.

    Args:
        name: Nome do logger (geralmente o nome do módulo).
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Caminho do arquivo de log.

    Returns:
        logging.Logger configurado.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Evita duplicação de handlers se o logger já existir
    if logger.handlers:
        return logger

    # Formato das mensagens
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para arquivo com rotação (máx. 5 MB, mantém 5 backups)
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)  # garante que a pasta existe
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
