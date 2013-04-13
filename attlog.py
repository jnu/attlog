#coding=utf8

'''
$ python attlog.py

Module for parsing ATT Wireless Logs. Currently only CSV supported.

Copyright (c) 2013 Joseph Nudell
'''
__author__="Joseph Nudell"
__date__="$April 12, 2013$"



import csv
import re
import json
from collections import defaultdict





class CustomException(Exception):
    def __init__(self, msg=""):
        self.msg = msg

    def __repr__(self):
        return self.msg

    def __str__(self):
        return repr(self)

class ParseError(CustomException):
    pass

class IllegalStateError(CustomException):
    pass

class BadHeaderError(CustomException):
    pass




class attlog(object):

    def __init__(self, path_to_csv=None):
        self._csvfile = path_to_csv
        self.records = dict()

        if self._csvfile is not None:
            # Parse on init
            self.parse_log()

    def parse_log(self, path_to_csv=None):
        if path_to_csv is None:
            path_to_csv = self._csvfile
            if path_to_csv is None:
                raise ValueError("No path specified")

        # Some useful RegExes that will be used repeatedly
        re_phone = re.compile(r'(?:\d{3}-){2}\d{4}')
        re_charge = re.compile(r'charge', flags=re.IGNORECASE)
        re_int = re.compile(r'[^\d]')

        with open(path_to_csv, 'r') as fh:
            reader = csv.reader(fh)

            # A log file can contain multiple accounts, made distinct by
            # the phone number, and voice + data records for each account.
            current_key = {
                'account' : None,
                'kind'    : None,
                'header'  : None,
            }

            for line in reader:
                # A lightweight FSM to parse log files
                if len(line)==0:
                    # Lots of blank lines in these files; skip them.
                    continue

                if line[0].startswith('AT&T'):
                    # Reset all keys -- this indicates a new account
                    current_key['account'] = None
                    current_key['kind'] = None
                    current_key['header'] = None
                    continue

                if current_key['account'] is None:
                    # Looking for account
                    if len(line)==2 and re_phone.match(line[1]) is not None:
                        # Found an account!
                        current_key['account'] = line[1]

                        # Add account to self.records dictionary. Its value is
                        # a defaultdict (list) to make code more readable.
                        if not self.records.has_key(line[1]):
                            self.records[line[1]] = defaultdict(list)
                        continue

                if current_key['kind'] is None:
                    # Looking for the kind of account (voice or data)
                    if line[0]=='Item':
                        # This is a header. Judge the type of account by 
                        # the format of this header. Also, save the header
                        # in memory to use as keys in the later record entries
                        # (Effectively using Mongo format)
                        if line[4] == 'Call To':
                            # Roaming headers are malformed ... oops, AT&T.
                            line.insert(4, 'Number Called')
                            line[-1] = "Roaming"

                        if line[4]=='Number Called':
                            # Voice record
                            current_key['kind'] = 'voice'
                        elif line[4]=='To/From':
                            # Data record
                            current_key['kind'] = 'data'

                            # Fix headers for consistency ...
                            line[6] = "Msg/KB"
                            line[10] = "In/Out"
                        else:
                            raise ParseError("Can't determine record type: %s"\
                                                 % str(line))

                        # Keep current line to use as keys for coming entries
                        current_key['header'] = line

                    # If key was found, or if it wasn't and is still unknown,
                    continue

                if line[0].strip().startswith('Total'):
                    # Skip totals rows. Reset kind and headers
                    current_key['kind'] = None
                    current_key['header'] = None
                    continue

                if line[0].strip().startswith('Subtotal'):
                    # Skip subtotals, since views in JS will be much more
                    # interesting and detailed.
                    continue

                if current_key['header'] is not None:
                    # Store record using headers in `account` and `kind`
                    a = current_key['account']
                    k = current_key['kind']
                    h = current_key['header']

                    new_entry = dict()
                    for key, val in enumerate(line):

                        try:
                            key = h[key]

                            # Do a little bit of typing and formatting here.
                            val = val.strip()

                            try:
                                if key=='Item':
                                    val = int(val)
                                elif key=='Day':
                                    # Some logs have full day name e.g. Saturday,
                                    # some only have abbr. e.g. SAT.
                                    val = val[:3].upper()
                                elif re_charge.search(key) is not None:
                                    # Charge is money, i.e. float
                                    val = float(val)
                                elif key=="Roaming":
                                    val = True
                                elif key=="Min":
                                    val = int(val)
                                elif key.startswith("Msg/KB"):
                                    val = int(re_int.sub('', val))
                                elif key=="Number Dialed":
                                    val = int(re_int.sub('', val))
                                elif key=="To/From":
                                    val = int(re_int.sub('', val))
                                elif key=="In/Out":
                                    # Some say "Sent/Rcvd" instead
                                    if val=="Rcvd" or val=="In":
                                        val = "In"
                                    elif val=="Sent" or val=="Out":
                                        val = "Out"
                                    else:
                                        raise ValueError("Val of I/O = %s"%val)
                            except ValueError as e:
                                pass

                            new_entry[key] = val
                        except IndexError as e:
                            raise BadHeaderError("Line (%s) doesn't match " \
                                                 "header (%s)" \
                                                 % (str(line), str(h)))

                    if new_entry != {'Item': ''}:
                        # Ignore blank entries ... these come in by accident.
                        self.records[a][k].append(new_entry)

                    continue

                # Should never get here. Something went wrong
                raise IllegalStateError("Unknown error parsing CSV")

    def __str__(self):
        return json.dumps(self.records)

    def __repr__(self):
        return "attlog(%s)" % str(self)

    def __add__(self, o):
        if type(o) is not type(self):
            raise TypeError("Add operation not defined for type %s"%type(o))

        new_records = dict()

        for obj in [self, o]:
            for account in obj.keys():
                if not new_records.has_key(account):
                    new_records[account] = defaultdict(list)

                for kind in obj[account].keys():
                    new_records[account][kind] += obj.records[account][kind]

        new_attlog = attlog()
        new_attlog.records = new_records
        return new_attlog

    def __setitem__(self, key, val):
        self.records[key] = val

    def __getitem__(self, key):
        return self.records[key]

    def keys(self):
        return self.records.keys()
