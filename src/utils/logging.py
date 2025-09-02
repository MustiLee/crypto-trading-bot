from loguru import logger
import sys


def setup_logging(debug: bool = False):
    logger.remove()
    
    level = "DEBUG" if debug else "INFO"
    
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    return logger