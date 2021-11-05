import sys

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit()

import logging
from logging import Logger
import time
import datetime
import inspect
# import traceback
# from typing import Optional
from pprint import pprint # pformat
from .strutil import nott # iss

class Logg:
    """
    This method presently defines various log "levels" but does not yet express
    ability to log "areas" or "keywords".

    TODO:
    - LOG BUFFER a list that only holds last 100 lines logged to it. This is useful
    for emitting when an exception happens in a loop and you are not interested
    in the first 10e6 log entries

    - KEYWORD LOGGING: pair a --debug_kw=keyword,keyword set on the command line to only
    recieve log output from log statements matching those keywords

    - CLASS/METHOD/FUNCTION logging: --debug_fn=class.method,module.func set on the command
    line that activates logging in the method or function listed. See inspection techniques
    listed near this SO question https://stackoverflow.com/a/5104943/11014343

    - BITWISE LOG LEVELS: --log_level=DEBUG|FILEIO|JSON|HTTP a maskable combination of enum_bitmask
    names that combine to a value that can trigger logging.

    These reserved words may not be used as tags:
        debug, debugging, debug_log, digest, file, gui, http, json, log, method, tag

    Please also consider how log messages can be formatted:
    https://stackoverflow.com/a/20112491/11014343:
    logging.basicConfig(format="[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s")
    """
    DEFAULT_LEVEL = logging.WARNING
    DefaultLogger = logging.getLogger(__name__)
    method_name_list: list = []  # list[str]
    tag_list: list = []  # list[str]
    reserved_tags: list = [  # list[str]
        "debug",
        "debugging",
        "debug_log",
        "digest",
        "file",
        "gui",
        "http",
        "json",
        "log",
        "method",
        "tag"
    ]

    def __init__(self,
                 log_level: int = DEFAULT_LEVEL,
                 name: str = None,
                 filename: str = None,
                 debug: bool = False):
        """----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
        Base class that can be used to send logging messages elsewhere. extend this
        in order to send log messages from this framework elsewhere.
        ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----"""

        self.level = log_level
        self.logger: Logger

        # self.start_time = datetime.now() # py 3.9 maybe?
        self.start_time = datetime.datetime.now() # py 3.9 maybe?
        self.start_time_str = time.strftime("%Y%m%d-%I:%M%:%S")
        if name:
            self.name = name
            if "@" in name:
                self.name = name.replace('@', self.start_time_str)
        else:
            self.name = "started-" + self.start_time_str

        self.logger = Logger(name, level=log_level)
        if filename:
            logging.basicConfig(filename=filename, filemode="a")
        if debug:
            self.logg(level=logging.WARNING,
                      msg="Logger {name} begun to {filename}".format(name=name,
                                                                     filename=filename))

    @classmethod
    def logg(cls,
             level: int = logging.WARNING,
             tag: str = None,
             msg: str = None) -> None:
        """
        Use this *class method* to send logs to the DefaultLogger instance created when this class was created
        :param level:
        :param msg:
        :return:
        """
        if nott(msg):
            return
        if level == logging.CRITICAL:
            cls.DefaultLogger.critical(msg)
            return
        if level == logging.ERROR:
            cls.DefaultLogger.error(msg)
            return
        if level == logging.WARNING:
            cls.DefaultLogger.warning(msg)
            return
        if level == logging.INFO:
            cls.DefaultLogger.info(msg)
            return
        if level == logging.DEBUG:
            cls.DefaultLogger.debug(msg)
            return

    def by_level(self,
                 level: int = logging.WARNING,
                 msg: str = None):
        """
        Use this *instance* version of the method for logging when you have a specific logger
        customized for a purpose. Otherwise please use Logg.logg().
        :param level: python logging priority
        :param msg: text to send to logging channel
        :return: None
        """
        if nott(msg):
            return

        if level == logging.CRITICAL:
            self.logger.critical(msg)
            return

        if level == logging.ERROR:
            self.logger.error(msg)
            return

        if level == logging.WARNING:
            self.logger.warning(msg)
            return

        if level == logging.INFO:
            self.logger.info(msg)
            return

        if level == logging.DEBUG:
            self.logger.debug(msg)
            return
        print("UNKNOWN: " + msg)

    def error(self, message: str = None):
        if not message:
            return
        self.logg(level=logging.ERROR, msg=message)

    def warning(self, message: str = None):
        if not message:
            return
        self.logg(level=logging.WARNING, msg=message)

    def info(self, message: str = None):
        if not message:
            return
        self.logg(level=logging.INFO, msg=message)

    def debug(self, message: str = None):
        if not message:
            return
        self.logg(level=logging.DEBUG, msg=message)

    @classmethod
    def register_method_name(cls, methodname: str = None) -> None:
        """
        Use this method to register names of functions you want to allow logging from
        :param methodname:
        :return:
        """
        if not methodname:
            return
        cls.method_name_list.append(methodname)
        if methodname not in cls.tag_list:
            cls.tag_list.append(methodname)

    @classmethod
    def register_tag(cls, tag: str = None) -> None:
        """
        Use this method to register keywords you want to allow logging from.
        There are a list of reserved tags which will not be accepted.
        :return:
        """
        if not tag:
            return
        if tag in cls.tag_list:
            return
        if tag in cls.reserved_tags:
            cls.logg(level=logging.ERROR,
                     msg=f"tag [{tag}] is reserved, ignoring")
            # note: add directly to tag_list to append a reserved tag
        cls.tag_list.append(tag)

    @classmethod
    def by_method(cls, msg: str = None) -> None:
        """
        should only log if we're in the method_list
        reminder: https://stackoverflow.com/a/13514318/11014343
        import inspect
        import types
        from typing import cast
        this_fn_name = cat(types.FrameType, inspect.currentframe()).f_code.co_name
        :return: None
        """
        try:
            caller = inspect.currentframe().f_back.f_code.co_name

            if caller in cls.method_name_list:
                cls.logg(level=cls.DEFAULT_LEVEL, msg=f"[{caller}] {msg}")

        except Exception as e:
            pprint(e)
            pass

    @classmethod
    def by_tag(cls, tag: str = None, msg: str = None) -> None:
        """
        should only log if we're in the method_list
        reminder: https://stackoverflow.com/a/13514318/11014343
        import inspect
        import types
        from typing import cast
        this_fn_name = cat(types.FrameType, inspect.currentframe()).f_code.co_name
        :return:
        """
        if (not cls.tag_list) or (tag not in cls.tag_list):
            return

        cls.logg(level=cls.DEFAULT_LEVEL, msg=f"[{tag}] {msg}")

    def enable(self, reserved_tag: str = None) -> None:
        if (not reserved_tag) or (reserved_tag not in self.reserved_tags):
            return
        if reserved_tag in self.tag_list:
            return
        self.tag_list.append(reserved_tag)
