This program will match two, or more (up to 3) columns of deposit amounts and a column of bank transactions to ensure they match. This program should accept a CSV file and find the correct columns, and match them to a column in a dataframe. The idea is to check the bank transactions with the PDI deposits and bank transactions.  

The CSV structure is as follows:

A|SITE ID|	B|Date|	C|Dep1|	D|Dep2|	E|Dep3|	F|Total|			I|Bank|

The CSV may only have 1 Dep column, so Dep1. That would shift the rest of the columns over.

Lets keep this solution as simple and quick as possible. Lets use a Tkinter UI to select the CSV, run button to run the check, and then a preview pane/text pane to reflect the output. 