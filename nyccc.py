#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
license :
    
    Copyright (C) 2013
    @author: Jussi Rasku

    This program is free software with GNU General Public License v3.
    See <http://www.gnu.org/licenses/>.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY. So be warned that your Professor may 
    wery well stop a citation error this program misses.
    
    
nyccc.py :
    
    is A python tool that parses and cross-checks academic name-year aka. 
    parenthetical referencing aka. Harvard referencing citations from your
    article, manuscript, or thesis text documents and references with your
    bibliography. 
    
    It is most useful for verifying citations and references from plain text
    and bibliography files where the refrences are manually managed. There it
    can find undefined/unused and mistyped citations and references.
    
    It detects:
        1) Duplicate or non-unique references in bibliography
        2) Bibliography references missing the publicaton year
        3) Citations that do not have a reference in bibliography
        4) Citations that do not have unambiguous reference(s)
        5) References that are not cited
        6) Perhaps other problems as well, but only as a byproduct.
        
    
    Manucript text is expected to use name-year citation format.
    Some examples of such citations:
        "(Rasku-Puttonen 1988, 30-32)"
        "(Rasku et al 2013a)"
        "(Rasku, Musliu & Kärkkäinen 2013)"
        "(Rasku and Hotokka 2013, 4--12)"
        "(D'Alembert 2001; Descartes et al. 1966; Young, Oldman et al. 1966)"
        
    It also supports citations within written text such as:
        "In their recent work Descartes, Platon et al. state (2003) that ..."
        "According to Rasku (2013, 1-2) there is still..."

    To see which corner cases of yours are handled, run the tool with -v 3 
     option to see which are considered to be promising citation candidates.
        
    Bibliography text is expected to have one reference per row. Also only the 
    part upto the plublication year is used when matching citations to
    references:        
        - (Athens 2000) would match reference
            * "Athens, P. 2000. The book." -> "Athens, P. 2000"
            but not 
            * "[2000a] Athens, P. 2000. The book." -> "[2000"
    Some examples of bibliography entries:
        - "Ragins, B.R. & Cotton, J.S. 2000. Marginal mentorin..."
            -> "Ragins, B.R. & Cotton, J.S. 2000"
        - "Lankau, M.J. & Scandura, T.A. 2002. An investigation of per..."
            -> "Lankau, M.J. & Scandura, T.A. 2002"
            
        
    There is also rudimendary unicode support as the parser normalizes any
    unicode characters to their ASCII counterparts.
    
    Call the script with "-h" switch to get command line usage info.
        

Some limitations:
    - Only citations and references with years 1800-2099 are supported
    - "Before Platon (2000)..." would produce a invalid citation
        -> ([Before, Platon], (2000)), because "Before" seems to be a name
    - Citations and references where the publication has no author _may_
       be parsed correctly, but probably not. For example:
         (European Union publications 2001) is valid citation, but not
         100% correctly matched with the correspondig reference.
    - Numbered aka. ACS style is not supported. 

    
example 1: 
        
    $ nyccc.py thesis.txt bib.txt -m "/" -a "och" -a "und" -e 2 -v 2
    
    what this does, is find citations in thesis.txt and cross check them
     against the bibliography in bib.txt. Author names can be separated
     with words "och" and "und" (german/swedish text) and if one set of
     parenthesis contains two or more citations they are separated with 
     "/" (-m "/"). The two last chars (-e 2) from the ends of each 
     author parsed from text (citation outside parenthesis) are removed.
     In addition a DEBUG level output (-v 2) is given.
         
         
example 2: 
        
    $ nyccc.py vkirja.txt llue.txt -a "ja" -a "und" -e 3 -p ""
    
    parses dissertation written in finnish with adjoining bibiography.
    The author lists can be separated with finnish "ja" (and). Because
    finnish language uses word suffixes a lot, rather agressive suffix
    removal (3) is used. Also the page numbers in citations are given 
    without the "p." prefix. This produces the output:
        
    Read from files:
    #cites: 861
    #unique cites: 355
    #references: 295
    
    No reference for citation ((Anderws 2008))
    Citation ((Bennet 1993)) is not unique, it can be any of these...
    	Bennett, M. J. 1993. Towards Ethnorelativism: A developmenta...'
    	Bennett, J. M. 1993. Cultural Marginality. Identity Issues i...'
    No reference for citation ((Bennet 1993a))
    ...
    
    Reference 'Campinha-Bacote, J. 1999. The Model and Instrument...' is not cited
    Reference 'Colwell, S. 1998. Mentoring, socialisation and the...' is not cited
    Reference 'Council of European Union. 2001. The concrete futu...' is not cited
    ...
    
    Summary:
    No reference for citation: 41/355 (11.55%)
    Reference was not cited: 60/295 (20.34%)
    
"""

import re
import os
import argparse
from collections import Counter

from unicodedata import normalize, category


####################
# DEFAULT SETTINGS #
####################

MULTICITE_DELIMETER = ";"
AND_WORDS = ["and"]
PAGE_NUM_ABBR = "p."
# In finnish text citations "according to Rasku" becomes "Raskun mukaan".
#  it is even worse with for example "Virtanen" becomes "Virtasen mukaan"
#  therefore it is possible to "eat up" last N words of the text citations
#  paranthesis citations are left as they were.
EAT_SUFFIX_CHARS = 2 
VERBOSITY = 0

    
##################################
# HELPER FUNCTIONS AND VARIABLES #
##################################

# Compiled regexps comes here
textcitere = None
authorre = None
yearre = None
likere = None
citere = None

def _strip_accents(s):
    return str(''.join(c for c in normalize('NFD', s) if category(c) != 'Mn'))

def _bib_to_key(bibref):
    global yearre
    
    yearmatch = yearre.search(bibref)       
    if not yearmatch:
        shortref = bibref[:min(len(bibref),60)]
        print "Reference '%s...' has no publication year" % shortref
        end = len(bibref)-1
    else:
        end = yearmatch.span()[1]   
    return bibref[:end] 
    
def _find_cite_in_bib(authors, year, bib_keys, full_bib=None):
    # unpack 
    cite_matched = False
    matched_refs = []        
    
    for ref in bib_keys:
        match = True
        for author in authors:
            if author not in ref:
                match = False
                break
        if match and year in ref:
            cite_matched = True
            matched_refs.append(ref)
            
    # As a backup, do a full search (for example if names are editors)
    if full_bib and not cite_matched:
        for full_ref in full_bib:
            match = True
            for author in authors:
                if author not in full_ref:
                    match = False
                    break
            if match and year in full_ref:
                cite_matched = True
                matched_refs.append(_bib_to_key(full_ref))
    
    return cite_matched, matched_refs

def _unique(cites):
    nolist_cites = [(" ".join(auths), year, cmpl) for auths, year, cmpl in cites]    
    seen = set()
    seen_add = seen.add
    unique_nolist_cites  = [ x for x in nolist_cites if x not in seen and not seen_add(x)]    
    return [(auths.split(), year, cmpl) for auths, year, cmpl in unique_nolist_cites]

def _file_exists(filename):
    if os.path.exists(filename):
        return filename
    raise argparse.ArgumentError("%s does not exist" % filename)
    
def _cite_to_str(cite):
    #unpack
    authors, year, complete = cite
    if complete:
        return "(%s %s)" % (", ".join(authors), year)  
    else:
        return "(%s... %s)" % ("..., ".join(authors), year)  
        
        
#############################
# THE NYCCC DEVELOPER "API" #
#############################

def init_regexps(and_word_list=AND_WORDS, page=PAGE_NUM_ABBR):
    """ Call this function first to initialize regexps that are used to
    detect name-year style citations from the text.
    """
    global textcitere
    global authorre
    global yearre
    global likere
    global citere

    # The regexes are derived from the c++/boost implementation of user Tex
    #  of the Q/A site stackoverflow. Thanks Tex!
    # http://stackoverflow.com/a/10533527/1788710
    
    page_abbr = ""
    if page!="":
        page_abbr = r"(?:"+re.escape(page)+r") +"
    
    # Apostrophes like in "D'Alembert" and hyphens like in "Flycht-Eriksson".
    author = r"([A-Z][a-zA-Z'`-]+)"
    # " 1990" or "(1990b)" or "1990."
    year = r" *((?:18|19|20)[0-9][0-9][a-z]?)\.?" 
    # Some authors write citations like "A, B, et al. (1995)".
    #  The comma before the "et al" pattern is not rare.
    etal = r"(?:,? et al.?)"
    # Page number of formats ", 1-3" or ", 1." or ", 112--12"  
    pagen = r"(?:, +"+page_abbr+r"[0-9]+(?:--?[0-9]+)?\.?)"
    nameconj = r"(?:"+author + r"(?: +"+" +| +".join(and_word_list)+r" +| +& +|, +)?)+"    
    totcit = nameconj+etal+r"?(?: ?[a-z]+ )*"+year+pagen+r"?"
    # Sounds like a citation but does not have names?
    likecite = r"\(([^\)]*?"+year+pagen+r"?[^\)]*?)\)"
    # Descartes & Platon et al. write (2003) that ...
    textcite = nameconj+etal+r"?(?: ?[a-z]+ )*\("+year+pagen+r"?\)" 
    
    textcitere = re.compile(textcite)
    authorre = re.compile(author)
    yearre = re.compile(year)
    likere = re.compile(likecite)
    citere = re.compile(totcit)
    
def get_bib_from_file(filename, verbosity=0):
    """ Read bibliograpy file where each row contains one (1) reference to
    some academic publication. It must be of the name-year format, so
    number.
    
    filename
        the file to read
    verbosity
        change the output detail level
    """
    src = open(filename, 'r')
    bib = []
    while 1:
        line = src.readline()
        if not line:
            break
            
        nonunicode_line = _strip_accents(unicode(line)).strip()
        if nonunicode_line != "":
            bib.append(nonunicode_line)
    return bib
    
def get_cites_from_file(filename, mutlicite_sep, eat_suffix_cnt=0, max_cites=None, verbosity=0):
    """ Read the text file that has name-year style citations. Returns 
    the detected citations. 
    
    filename
        the file to read
    mutlicite_sep
        parenthesis pair can contain be multiple cites if they are separated
         with this char (or string)
    eat_suffix_cnt
        this many characters are removed from the end of authors names for
         names parsed straight from the text (not in parenthesis).
    max_cites
        specify how many citations are read before stopping.
    verbosity
        change the output detail level
    """
    
    global textcitere
    global authorre
    global yearre
    global likere
    global citere
    if not (textcitere and authorre and yearre and likere and citere):
       init_regexps()
    
    src = open(filename, 'r')
    allcites = []
    counter = 0
    while 1:
        line = src.readline()
        if not line or (max_cites and counter>max_cites):
            break
            
        nonunicode_line = _strip_accents(unicode(line))
        nameyear_candidates = likere.findall(nonunicode_line)
        textcite_candidates = textcitere.finditer(nonunicode_line)
        
        for tc_candidate in textcite_candidates:
            if verbosity > 2:
                print "Detected a text citation:" 
                print tc_candidate.group(0)
                
            text_cite_text = tc_candidate.group(0)
            year = yearre.findall(text_cite_text)[0]
            complete = False
            posfixed_authors = authorre.findall( text_cite_text )
            tcite = ([author[:-eat_suffix_cnt] for author in posfixed_authors], year, complete)
            allcites.append(tcite)
            counter += 1
            
            if verbosity > 2:
                print "Extracted citation:" 
                print tcite
                print  
        
        for ny_candidate in nameyear_candidates:
            # if citation like (2009), then we have used the textcite_candidates
            if ny_candidate[0] == ny_candidate[1]:
                continue
            
            if verbosity > 2:
                print "Detected something that seems to be a citation:" 
                print ny_candidate
            
            cites = []
            for scc in ny_candidate[0].split(mutlicite_sep):
                cres = citere.search(scc)

                if not cres or len(cres.groups())<2: 
                    continue
                
                authors = authorre.findall( cres.group(0) )
                year = cres.group(2)
                complete = True
                pcite = (authors, year, complete)
                cites.append(pcite)
                allcites.append(pcite)
                counter += 1
            
            if verbosity > 2:
                print "Extracted citations:" 
                print cites
                print
                
    return allcites
    
def cross_check(cites, bib):
    """ This function does the actual verification of the citations and 
    references. 
    
    cites
        is a list of triplets: (author_list, year, complete), where
        complete states wether the author names are complete (not partial)
        
    bib 
        is a list of strings. Each string is a reference in some relatively 
        standard name-year bibliography format.
    """
    
    ## For faster search use the reference only upto the year ##
    bib_keys = []
    key_to_bib = {}
    for bibref in bib:
        key = _bib_to_key(bibref)
        bib_keys.append( key )
        if key in key_to_bib: 
            print "Non-unique or duplicate bibliography entry:"
            print "/t"+bibref
            print "/t"+key_to_bib[key]
        else:
            key_to_bib[key] = bibref
    
    ## Validate citations and bibliography ##
    #  and calcluate some statistics while you are at it!
    refcnt = Counter()
    missing_ref_cnt = 0
    missing_cite_cnt = 0
    
    print
    for cite in cites:
        authors, year, complete = cite
        
        # Complete author names, so we require a comma before the initials
        #if complete:
        #    authors = [author+"," for author in authors]            
        
        # Find the citations in the bibliography
        cite_has_target, refs = _find_cite_in_bib(authors, year, bib_keys, bib)
        if cite_has_target:
            if len(refs)>1:
                print "Citation (%s) is not unique, it can be any of these..." % _cite_to_str(cite)                
                for ref in refs:
                    fullref = key_to_bib[ref] 
                    #print fullref 
                    print "\t%s...'" % (fullref[:min(len(fullref), 60)])  
            for ref in refs:
                refcnt[ref] += 1
        else:
            print "No reference for citation (%s)" %  _cite_to_str(cite)
            missing_ref_cnt += 1
    print 
    
    for key in bib_keys:
        if refcnt[key] == 0:
            fullref = key_to_bib[key] 
            shortref = fullref[:min(len(fullref), 50)]
            print "Reference '%s...' is not cited" % shortref
            missing_cite_cnt += 1
    print 
    
    return missing_ref_cnt, missing_cite_cnt


#############################    
# COMMAND LINE UI FUNCTIONS #
#############################

def parse_cmd_arguments():
    parser = argparse.ArgumentParser(description='A tool that crosschecks citations from your manuscript text and references in your bibliography.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('textfile', help='The manuscript as plain text file (1 line = 1 paragraph)', type=_file_exists)
    parser.add_argument('bibfile', help='The bibiliography as plain text file (1 line =  1 reference)', type=_file_exists)
    
    parser.add_argument('-m', help='Multiple citations separator (eg. Author 1990; Author 1992)', default=MULTICITE_DELIMETER, dest='multi_cite_sep')
    parser.add_argument('-a', help='Additional word to treat as "and" word (can be given multiple times eg. -a "and" -a "och")', action='append', dest='and_word_list')
    parser.add_argument('-p', help='Page number abbreviation', default=PAGE_NUM_ABBR, dest="page_num_abbr")
    parser.add_argument('-e', help='Eat this many letters from the end of author names of in-text citations (to remove suffixes)', dest='suffix_eat_cnt', default=EAT_SUFFIX_CHARS, type=int)
    parser.add_argument('-v', help='Verbosity level (0-3)', dest='verbosity', default=1, type=int)

    return vars(parser.parse_args())
    
def read_files(parsed_args):
    # use temp vars. for clarity
    itf = parsed_args['textfile']
    ibf = parsed_args['bibfile']
    mcs = parsed_args['multi_cite_sep'] 
    sec = parsed_args['suffix_eat_cnt']
    verbosity = parsed_args['verbosity']
    
    cites = get_cites_from_file(itf, mcs, sec, verbosity=verbosity)    
    bib = get_bib_from_file(ibf, verbosity=verbosity)    
    ucites = _unique(cites)
    cites.sort()
    ucites.sort()

    return ucites, cites, bib    

def main():
    parsed_args = parse_cmd_arguments()
    verbosity = parsed_args['verbosity']
    
    ## Prepare the parsers
    additional_and_words = parsed_args['and_word_list'] if parsed_args['and_word_list'] else []
    init_regexps(additional_and_words+AND_WORDS, parsed_args['page_num_abbr'])
        
    ## Read cites and bibliography from files ##
    ucites, cites, bib = read_files(parsed_args)
    
    if verbosity > 0:
        print "Read from files:"
        print "#cites:", len(cites)
        print "#unique cites:", len(ucites)
        print "#references:", len(bib)
        print         
    if parsed_args['verbosity'] > 2:
        from pprint import pprint
        pprint(ucites)
    
    ## Check for missing refs and cites
    print "Detected problems:"
    missing_ref_cnt, missing_cite_cnt = cross_check(ucites, bib)
    
    if verbosity > 0:      
        num_cites = len(ucites)    
        num_refs = len(bib)   
        
        print "Summary:"
        print "No reference for citation: %d/%d (%.2f%%)" % \
            (missing_ref_cnt, num_cites, 100.0*missing_ref_cnt/num_cites)
        print "Reference was not cited: %d/%d (%.2f%%)" % \
            (missing_cite_cnt, num_refs, 100.0*missing_cite_cnt/num_refs)
        
if __name__ == "__main__":
    main()
                