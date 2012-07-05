#!/bin/sh

# Check for existence and formatting of required input files.
# On success, will give no errors and retrun 0
#

STATUS=0

# Check existence of organism file
echo "Checking for existence of organisms file..."
if [ ! -f "organisms" ]; then
    echo "ERROR: organisms file not found";
    STATUS=1
fi

# Check that the organism ID is the third column
echo "Checking format of organism ID in organisms file..."
orgmatch=$(cat organisms | cut -f 3 | grep -P "^\d+\.\d+$")
if [ $? -eq 1 ]; then
    echo 'ERROR: Organism IDs not found or not in the expected format (third column of organisms file, and must have format #.# i.e. 83333.1 for E coli)';
    STATUS=1
fi

# Check existence of groups file (for clustering)
echo "Checking existence of groups file..."
if [ ! -f "groups" ]; then
    echo 'ERROR: groups file not found';
    STATUS=1
fi

# Check that organism names in groups file match with organisms file?

# For each orgmatch see if there is a raw file containing genes with that ID
if [ ! -d "raw" ]; then
    echo 'ERROR: Raw files must be placed in the "raw" folder';
    STATUS=1;
else
    cd raw;
    for org in ${orgmatch}; do
	fmatch=$(grep -o -F ${org} *);
	echo "Testing existence of a raw file for organism ${org}...";
	if [ $? -eq 1 ]; then
	    echo "ERROR: No raw file match for organism ID ${org}";
	    STATUS=1;
	fi
    done

    for file in $(ls | grep -v "README"); do
	echo "Checking format of raw file ${file}..."
	# Note  - all of these check for the existence of ONE thing with the right format in each column (they don't check that ALL of the rows are the right format)
	# I dont check the following things that are still useful:
	# contig (column 1) - no specific format required
	# function (column 8) - no specific format required
	# The following columns are never used by my programs:
	# column 4 (location) - use columns 1,5,6, and 7 instead.
	# column 9 (aliases) - use the "aliases" file instead.
	# column 10 (figfam)
	# column 11 (evidence codes)
	fmatch=$(cat ${file} | cut -f 2 | grep -o -P "^fig\|\d+\.\d+\.peg\.\d+$");
	if [ $? -eq 1 ]; then
	    echo "ERROR: Gene IDs in raw file ${file} were not in expected format (fig|#.#.peg.# where the first two are the organism ID) or not in the expected place (second column)";
	    STATUS=1;
	fi
	fmatch=$(cat ${file} | cut -f 3 | grep -o -P "^peg$");
	if [ $? -eq 1 ]; then
	    echo "ERROR: No objects of type peg (third column) identified in file ${file}. Only pegs (protein encoding genes) are considered in our clustering analysis!";
	    STATUS=1;
	fi
	fmatch=$(cat ${file} | cut -f 5 | grep -o -P "^\d+$");
	if [ $? -eq 1 ]; then
	    echo "ERROR: Gene start location (fifth column) expected to be a number in file ${file}";
	    STATUS=1;
	fi
	fmatch=$(cat ${file} | cut -f 6 | grep -o -P "^\d+$");
	if [ $? -eq 1 ]; then
	    echo "ERROR: Stop location (sixth column) expected to be a number in file ${file}";
	    STATUS=1;
	fi
        fmatch=$(cat ${file} | cut -f 7 | grep -o -P "^[+-]$");
	if [ $? -eq 1 ]; then
	    echo "ERROR: Strand (seventh column) must be + or - in file ${file}";
	    STATUS=1;
	fi
        fmatch=$(cat ${file} | cut -f 12 | grep -o -i -P "^[acgt]+$");
	if [ $? -eq 1 ]; then
	    echo "ERROR: Nucleotide sequence expected in 12th column in file ${file}";
	    STATUS=1;
	fi
	# Note this wont match the header because fo the "_" in aa_sequences
	fmatch=$(cat ${file} | cut -f 13 | grep -o -i -P "^[A-Z]+$")
	if [ $? -eq 1 ]; then
	    echo "ERROR: Amino acid sequence expected in 13th column in file ${file}";
	    STATUS=1;
	fi
    done
    cd ..;
fi

if [ ! -f ./aliases/aliases ]; then
    echo "WARNING: No aliases file found - no alias subsitution will be performed for gene names"
fi

exit ${STATUS}