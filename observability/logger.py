"""
=================================================================
  日志配置模块
  用法：
    from logger import get_logger
    log = get_logger(__name__)
    log.info("采集完成，共 %d 条", count)
    log.warning("API 响应异常: %s", msg)
    log.error("采集失败", exc_info=True)
=================================================================
"""
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """获取日志器，按模块名区分"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
