#!/usr/bin/env python

import fileinput, optparse, sqlite3, sys, re
from ClusterFuncs import *
from FileLocator import *
from sanitizeString import *

usage = "%prog -g GPR_file -i RunID [options] > Rxn_presence_absence"
description = """This function takes a two-column table containing
gene protein reaction relationships (GPR) and produces a table
telling whether the reaction is present in each organism in a given cluster run
based on the presence\absence of individual genes from the clustering results.

The GPR_file should have exactly two columns:
* A column of reaction IDs (first column)
* A column of Gene-protein relationships [I.E. "GeneX and GeneY"] (second column)

This will only work if the gene IDs are the same in the GPRs as they are in the database.

The gene IDs MUST be formatted the same way as they are in the database, i.e. in the 
fig\|\d+\.\d+\.peg\.\d+ format
"""
parser = optparse.OptionParser(usage=usage, description=description)
parser.add_option("-g", "--gprfile", help="GPR file (required, D=None)", action="store", type="str", dest="gprfile", default=None)
parser.add_option("-i", "--runid", help="Run ID to use to identify presence\absence of genes (requried, D=None)", action="store", type="str", dest="runid", default=None)
parser.add_option("-o", "--or", help="Replace all AND in the input GPR with OR (useful for diagnosing issues with missing subunits). D = False, evaluate as written",
                  action="store_true", dest="repor", default=False)
(options, args) = parser.parse_args()

if options.gprfile is None:
    sys.stderr.write("ERROR: GPR file (-g) is a required argument to evaluateReactionsFromGpr.py \n")
    exit(2)

if options.runid is None:
    sys.stderr.write("ERROR: Run ID (-i) is a required argument to evaluateReactionsFromGpr.py \n")
    exit(2)

geneFinder = re.compile("fig\|\d+\.\d+\.peg\.\d+")

# Lets get a dictionary from reactions to GPRs first
# This will be a dictionary from reaction to a LIST of GPRs
# because it is quite possible that we are using more than one
# reference organism with some overlapping reacitons.
rxn2gpr = {}
for line in open(options.gprfile, "r"):
    spl = line.strip("\r\n").split("\t")
    if len(spl) < 2:
        gpr = ""
    else:
        gpr = spl[1]
    if options.repor:
        gpr = gpr.replace("and", "or")
    if spl[0] in rxn2gpr:
        rxn2gpr[spl[0]].append(gpr)
    else:
        rxn2gpr[spl[0]] = [ gpr ]

# Now lets get a list of genes contained in those GPRs.
genelist = []
for rxn in rxn2gpr:
    for gpr in rxn2gpr[rxn]:
        genes = geneFinder.findall(gpr)
        if genes is None:
            sys.stderr.write("WARNING: No genes with expected format found in GPR %s\n" %(gpr) )
            continue
        for gene in genes:
            genelist.append(gene)

if len(genelist) == 0:
    sys.stderr.write("ERROR: No genes were found with expected formatting - dont forget to replace your IDs with those present in the database...\n")
    exit(2)

# One gene can catalyze multiple reactions. For the purposes of finding clusters, we don't care.
# We'll go back and sort that out with the GPRs later.
genelist = list(set(genelist))

# Use the database to get lists of organisms in each cluster that contains a gene in the query GPR...
con = sqlite3.connect(locateDatabase())
cur = con.cursor()

# ClusterID -> [organisms]
cluster2orgs = {}
# Cluster ID -> [genes in the input GPR]
cluster2genes = {}

orglist = set(getOrganismsInClusterRun(options.runid, cur))
cluster_tuples = getClustersContainingGenes( genelist, cur, runid=options.runid)

for tup in cluster_tuples:
    clusterid = str(tup[1])
    geneid = str(tup[2])
    if clusterid in cluster2genes:
        cluster2genes[clusterid].add(geneid)
    else:
        cluster2genes[clusterid] = set()
        cluster2genes[clusterid].add(geneid)

    if clusterid not in cluster2orgs:
        cluster_orgs = getOrganismsInCluster(options.runid, clusterid, cur)
        cluster2orgs[clusterid] = set(cluster_orgs)

con.close()

# For each organism we iterate over each of those clusters and see if it is in there.
# If not, we assign the genes in those clusters to FALSE and if they are to TRUE.
# Then we evaluate...
rxn2presence = {}

syntaxerrors = set()
nameerrors = set()
badrxns = []
for org in orglist:
    gene2presenceabsence = {}
    for cluster in cluster2orgs:
        val = False
        if org in cluster2orgs[cluster]:
            val = True
        for gene in cluster2genes[cluster]:
            # To use EVAL we need to have variables (gene names) with valid python syntax.
            gen = gene.replace("|", "_").replace(".", "_")
            gene2presenceabsence[gen] = val
    # Now we SHOULD be able to do eval.
    # If we have issues it means there's a formatting error in the GPR - we should print the offending ones and continue on.
    for rxn in rxn2gpr:
        gprlist = rxn2gpr[rxn]
        overallPresence = False
        for gpr in gprlist:
            try:
                rxnPresent = eval(gpr.replace("|", "_").replace(".", "_"), {"__builtins__":None}, gene2presenceabsence)
            except SyntaxError:
                syntaxerrors.add("WARNING: There was a syntax error (probably a missing parenthesis) in the following GPR: \n%s\t%s \n" %(rxn, gpr))
                badrxns.append(rxn)
                break
            except NameError:
                nameerrors.add("WARNING: The following GPR had a NameError (likely caused by a bad gene name in the GPR): \n%s\t%s \n " %(rxn,gpr))
                badrxns.append(rxn)
                break
            # If it matches ANY of the query organisms that's good enough for me.
            overallPresence = overallPresence or rxnPresent
        # I turn it into ints so that I can append the results directly to a tree as a heatmap (0 and 1 can be mapped to colors but True and False cannot)
        if rxn in rxn2presence:
            rxn2presence[rxn].append(int(overallPresence))
        else:
            rxn2presence[rxn] = [ int(overallPresence) ]

for s in syntaxerrors:
    sys.stderr.write(s)
for s in nameerrors:
    sys.stderr.write(s)

print "orgs\t%s" %("\t".join(orglist))

for rxn in rxn2presence:
    # I do it this kind of round-about way because eval isn't always consistent with whether or not it throws a syntax error!
    # This makes me a bit worried about the accuracy of the results...
    if rxn in badrxns:
        continue
    print "%s\t%s" %(rxn, "\t".join( [ str(a) for a in rxn2presence[rxn] ] ))
