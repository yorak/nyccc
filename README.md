# nyccc

**NYCCC = Name-Year Citation Cross Checker**, a tool that crosschecks citations from your manuscript text and references in your bibliography for undefined/unused and mistyped citations and references.


## License
 
Copyright (C) 2013
@author: Jussi Rasku

This program is free software with GNU General Public License v3.
See <http://www.gnu.org/licenses/>.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY. So be warned that your Professor may 
wery well stop a citation error this program misses.
    
    
## Details


nyccc is a tool written in Python that parses and cross-checks academic name-year (aka. parenthetical referencing aka. Harvard referencing) citations from your
article, manuscript, or thesis text documents and references with your
bibliography. 

It is most useful for **verifying citations and references from plain text
and bibliography files** where the references are manually managed. There it
can find undefined/unused and mistyped citations and references.

### It detects

 1. Duplicate or non-unique references in bibliography
 2. Bibliography references missing the publication year
 3. Citations that do not have a reference in bibliography
 4. Citations that do not have unambiguous reference(s)
 5. References that are not cited
 6. Perhaps other problems as well, but only as a byproduct.
	
Manuscript text is expected to use name-year citation format.
Some examples of such citations:

    "(Rasku-Puttonen 1988, 30-32)"
    "(Rasku et al 2013a)"
    "(Rasku, Musliu & Kärkkäinen 2013)"
    "(Rasku and Hotokka 2013, 4--12)"
    "(D'Alembert 2001; Descartes et al. 1966; Young, Oldman et al. 1966)"
	
It also supports citations within written text such as:

    "In their recent work Descartes, Platon et al. state (2003) that ..."
    "According to Rasku (2013, 1-2) there is still..."

To see which corner cases of yours are handled, run the tool with ```-v 3``` 
 option to see which are considered to be promising citation candidates.
	
Bibliography text is expected to have one reference per row. Also only the 
part upto the publication year is used when matching citations to
references:        

 * ```(Athens 2000)``` would match reference
  * ```"Athens, P. 2000. The book."```
	( -> ```"Athens, P. 2000"``` ), **but not**
  * ```"[2000a] Athens, P. 2000. The book."```
	( -> ```"[2000"``` )
	
Some examples of bibliography entries:

    "Ragins, B.R. & Cotton, J.S. 2000. Marginal mentorin..."
	-> "Ragins, B.R. & Cotton, J.S. 2000"

    "Lankau, M.J. & Scandura, T.A. 2002. An investigation of per..."
	-> "Lankau, M.J. & Scandura, T.A. 2002"
	
There is also rudimentary unicode support as the parser normalizes any
unicode characters to their ASCII counterparts.

Call the script with ```-h``` switch to get command line usage info.
        

### Limitations

 - Only citations and references with years 1800-2099 are supported
 - ```"previous sentence. Before Platon (2000) discovered ..."``` would produce a invalid citation
	-> ```([Before, Platon], (2000))```, because ```"Before"``` seems to be a lot like a persons name
 - Citations and references where the publication has no author _may_
    be parsed correctly, but probably not. For example:
    ```(European Union publications 2001)``` is a valid citation, but not
    100% correctly matched with the corresponding reference.
 - Numbered aka. ACS style is not supported. 

    
## Example 1

    
```
$ nyccc.py thesis.txt bib.txt -m "/" -a "och" -a "und" -e 2 -v 2
```
	
what this command does, is find citations in ```thesis.txt``` and cross check them against the bibliography in ```bib.txt```. Author names can be separated      with words ```"och"``` and ```"und"``` (german/swedish text) and if one set of parenthesis contains two or more citations they are separated with ```"/"``` (```-m "/"```). The two last chars (```-e 2```) from the ends of each author parsed from text (citation outside parenthesis) are removed. In addition a DEBUG level output (```-v 2```) is given.
         
         
## Example 2 

```
$ nyccc.py vkirja.txt llue.txt -a "ja" -e 3 -p ""
```
	
parses dissertation written in finnish with adjoining bibiography.
The author lists can be separated with finnish "ja" (and). Because
finnish language uses word suffixes a lot, rather agressive suffix
removal (3) is used. Also the page numbers in citations are given 
without the "p." prefix. This produces the output:


	Read from files:
	#cites: 861
	#unique cites: 355
	#references: 295

	Detected problems:
	No reference for citation ((Anderws 2008))
	Citation ((Bennet 1993)) is not unique, it can be any of these...
		Bennett, M. J. 1993. Towards Ethnorelativism: A developmenta...'
		Bennett, J. M. 1993. Cultural Marginality. Identity Issues i...'
	No reference for citation ((Bennet 1993a))
	... etc ...

	Reference 'Campinha-Bacote, J. 1999. The Model and Instrument...' is not cited
	Reference 'Colwell, S. 1998. Mentoring, socialisation and the...' is not cited
	Reference 'Council of European Union. 2001. The concrete futu...' is not cited
	... etc ...

	Summary:
	No reference for citation: 41/355 (11.55%)
	Reference was not cited: 60/295 (20.34%)