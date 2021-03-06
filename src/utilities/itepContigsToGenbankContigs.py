#!/usr/bin/env python

import fileinput
import os
import optparse
import re
import sys
from Bio import SeqIO

from FileLocator import *

usage = """%prog -g genbankfile [options] > Conversion_table
%prog -o organismid [options] > Conversion_table
%prog -g genbankfile -o organismid > Conversion_table
"""
description = """
Get a conversion table from ITEP contig IDs to
contig IDs in the provided genbank file.
The provided genbank file MUST have been modified using
addItepIdsToGenbank.py (or in the process of making tables
e.g. with convertGenabnk2Table.py) for the use of this function
to make sense!
"""

parser = optparse.OptionParser(usage=usage, description=description)
parser.add_option("-g", "--genbank", help="Genbank file. If the name is [organismID].gbk you don't need to specify an organism ID, otherwise you must provide one in addition.",
                   action="store", dest="genbank", default=None)
parser.add_option("-o", "--organismid", help="Organism ID. If only organism ID is provided, genbank file location is assumed to be $ITEPROOT/genbank/[organismid].gbk. If genbank file is also identified, we will use that one instead and use this organism ID to convert to ITEP contig IDs.",
                   action="store", dest="organismid", default=None)
(options, args) = parser.parse_args()

if options.genbank is None and options.organismid is None:
    sys.stderr.write("ERROR: At least one of genbank file and organism ID is required as input\n")
    exit(2)
elif options.genbank is None:
    genbankFile = os.path.join(locateRootDirectory(), "genbank", "%s.gbk" %(options.organismid))
    if not os.path.exists(genbankFile):
        sys.stderr.write("Unable to find genbank file for organism ID %s! (Expected location : %s)\n" %(options.organismid, genbankFile))
        exit(2)
    options.genbank = genbankFile
elif options.organismid is None:
    genbankFileFormatCheck = re.compile("^(\d+\.\d+).gbk$")
    match = genbankFileFormatCheck.search(options.genbank)
    if match is None:
        sys.stderr.write("ERROR: Unable to infer organism ID from genbank file name - either name must be normalized or organism ID must be provided.\n")
        exit(2)
    else:
        options.organismid = match.group(1)
else:
    # Neither of them is None
    pass

# Attempt to build links.
# ITEP IDs are generated by taking the raw IDs and adding the organism ID to them
putative_links = {}
multi_genbank = SeqIO.parse(options.genbank, "genbank")
for single_genbank in multi_genbank:
    # Get the raw contig ID from which ITEP IDs are derived
    raw = single_genbank.name
    itep = "%s.%s" %(options.organismid, raw)
    format_ok = False
    for feature in single_genbank.features:
        # We don't want to modify things that aren't coding sequences...
        if feature.type == "source":
            if "db_xref" in feature.qualifiers:
                for db_xref in feature.qualifiers["db_xref"]:
                    if db_xref.startswith("originalContig:"):
                        putative_links[itep] = db_xref.replace("originalContig:", "")
                        format_ok = True
                        break
                    pass
                pass
            if not format_ok:
                sys.stderr.write("ERROR: The inputted genbank file %s does not have the originalContig IDs (are you sure the ITEP Ids were added to it?)\n" %(options.genbank))
                exit(2)
            pass
        pass
    pass

# Sanity check
from ClusterFuncs import *
import sqlite3
con = sqlite3.connect(locateDatabase())
cur = con.cursor()
valid_contigs = getContigIds(cur, orgid=options.organismid, issanitized=False)
con.close()

# This won't catch everything if there are redundatn names and so on but it is something at least...
for link in putative_links:
    if link not in valid_contigs:
        sys.stderr.write("WARNING: ID mismatch between what is in genbank file and what is expected to be in ITEP -  ID %s was not found in ITEP but was generated from the genbank file\n" %(link))

for link in putative_links:
    print "%s\t%s" %(link, putative_links[link])
