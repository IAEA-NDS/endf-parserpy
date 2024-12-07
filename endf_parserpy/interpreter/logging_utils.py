############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2024/12/07
# License:         MIT
# Copyright (c) 2022-2024 International Atomic Energy Agency (IAEA)
#
############################################################


import logging
from endf_parserpy.utils.tree_utils import reconstruct_tree_str


def setup_logger(logger_name, log_level, log_format=None):
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    # create handlers
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    # create formatters
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    ch.setFormatter(formatter)
    # add handler to logger
    if not logger.hasHandlers():
        logger.addHandler(ch)
    return logger


def write_info(logger, message, ofs=None):
    prefix = f"Line #{ofs}: " if ofs is not None else ""
    logger.info(prefix + message)


def abbreviate_valstr(val):
    if isinstance(val, int) or isinstance(val, float):
        return str(val)
    elif isinstance(val, str):
        if len(val) < 13:
            return val
        else:
            return val[1:5] + "..." + val[1:5]
    elif isinstance(val, dict):
        return "{" + ", ".join(str(k) for k in tuple(val.keys())[:3]) + ", ..." + "}"


def should_skip_logging_info(varnames, datadic):
    if len(varnames) == 0:
        return True
    elif (
        len(varnames) == 1
        and isinstance(datadic[varnames[0]], dict)
        and len(datadic[varnames[0]]) > 1
    ):
        return True
    # if all variables are dictionaries...
    elif len(tuple(1 for v in varnames if isinstance(datadic[v], dict))) == len(
        varnames
    ):
        # and all these dictionaries have more than one element
        # we skip displaying then because they have been already
        # filled and displayed before
        if len(tuple(1 for v in varnames if len(datadic[v]) <= 1)) == 0:
            return True
        else:
            return False
    else:
        return False


class RingBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.tail = -1
        self.num_enqueued = 0

    def enqueue(self, elem):
        self.tail = (self.tail + 1) % self.capacity
        self.buffer[self.tail] = elem
        self.num_enqueued += 1

    def get_queue(self):
        if self.num_enqueued > self.capacity:
            return self.buffer[self.tail + 1 :] + self.buffer[: self.tail + 1]
        else:
            return self.buffer[: self.tail + 1]

    def dump_state(self):
        return {
            "capacity": self.capacity,
            "buffer": self.buffer,
            "tail": self.tail,
            "num_enqueued": self.num_enqueued,
        }

    def load_state(self, state_info):
        self.capacity = state_info["capacity"]
        self.buffer = state_info["buffer"]
        self.tail = state_info["tail"]
        self.num_enqueued = state_info["num_enqueued"]

    def save_record_log(self, ofs, line, record_tree, onlyfirst=False):
        recon_str = reconstruct_tree_str(record_tree)
        if onlyfirst:
            recon_str = recon_str.split("\n")[0]
        self.enqueue({"ofs": ofs, "line": line.rstrip(), "record_spec": recon_str})

    def display_record_logs(self):
        outstr = ""
        for curentry in self.get_queue():
            outstr += f'-------- Line {curentry["ofs"]} -----------\n'
            outstr += "Template:  {}\n".format(curentry["record_spec"])
            outstr += 'Line:     "{}"\n\n'.format(curentry["line"])
        return outstr

    def save_reduced_record_log(self, record_tree, onlyfirst=False):
        self.save_record_log(0, "", record_tree, onlyfirst)

    def display_reduced_record_logs(self):
        outstr = ""
        for curentry in self.get_queue():
            outstr += "Template:  {}\n".format(curentry["record_spec"])
        return outstr

    def get_last_entry(self, key_prefix=""):
        last_entry = self.buffer[self.tail]
        return {f"{key_prefix}{k}": v for k, v in last_entry.items()}
