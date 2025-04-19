#!/usr/bin/env python

import sys
import os
import glob


states = {'arizona'       : 'AZ',
          'california'    : 'CA',
          'colorado'      : 'CO',
          'connecticut'   : 'CT',
          'delaware'      : 'DE',
          'district of columbia' : 'DC',
          'georgia'       : 'GA',
          'hawaii'        : 'HI',
          'illinois'      : 'IL',
          'indiana'       : 'IN',
          'iowa'          : 'IA',
          'kentucky'      : 'KY',
          'louisiana'     : 'LA',
          'maine'         : 'ME',
          'maryland'      : 'MD',
          'massachusetts' : 'MA',
          'minnesota'     : 'MN',
          'mississippi'   : 'MS',
          'missouri'      : 'MO',
          'montana'       : 'MT',
          'nebraska'      : 'NE',
          'nevada'        : 'NV',
          'new hampshire' : 'NH',
          'new york'      : 'NY',
          'north carolina': 'NC',
          'ohio'          : 'OH',
          'oregon'        : 'OR',
          'pennsylvania'  : 'PA',
          'rhode island'  : 'RI',
          'texas'         : 'TX',
          'south carolina': 'SC',
          'tennessee'     : 'TN',
          'vermont'       : 'VT',
          'virginia'      : 'VA',
          'washington'    : 'WA',
          'west virginia' : 'WV',
          'wisconsin'     : 'WI',
          'wyoming'       : 'WY',
          }


def read_papers():
    f = open ('../LIST')
    d = {}
    inpapers = False
    keys = set()
    for l in f.readlines():
        l = l.strip()
        if l == 'PAPERS':
            inpapers = True
        elif inpapers:
            if not l: break
            fields = l.split (None, 1)
            paper = fields[1]
            paper = paper.split(';')[0].strip()
            if len(fields) == 2:
                d[paper] = fields[0]
                if fields[0] in keys:
                    print ('duplicate key', fields[0], paper)
    return d


def readmd (mdfile_name):
    f = open (mdfile_name)
    d = {}
    for l in f.readlines():
        fields = l.strip().split(':', 1)
        if len(fields) == 2:
            d[fields[0].strip()] = fields[1].strip()
    return d


def writetxt (md, d, startclient):
    paperdict = read_papers()
    paper_title = md['Newspaper_Title']
    if paper_title not in paperdict:
        print ("Cannot find key for paper `" + paper_title + "'")
        sys.exit(1)
    paperkey = paperdict[paper_title]
    date = md['Issue_Date']
    if date[0] == "'" and date[-1] == "'":
        date = date[1:-1]
    print (paperkey, date)
    txtname = f'{date}-{paperkey}.txt'
    inum = 1
    while os.path.exists (txtname):
        inum += 1
        txtname = f'{date}-{paperkey}-{inum}.txt'

    state = md['State']
    statecode = states[state]
    state = statecode + ' ' + state

    f = open(txtname, 'w')
    print (f'Name: {txtname}', file=f)
    print (f'Date: {date}', file=f)
    print (f'Paper: {paper_title}', file=f)
    print (f'Paperkey: {paperkey}', file=f)
    print (f'Page: {md["Page"]}', file=f)
    print (f'City: {md["City"]}', file=f)
    print (f'State: {state}', file=f)
    print (f'Url: {md["AAId"]}', file=f)
    print (f'Title: ', file=f)
    print (f'Author: ', file=f)
    print (f'---', file=f)

    wrote_cleaned = False
    for cleaned_file in glob.glob (os.path.join (d, '*.cleaned')):
        f.write('\n')
        f.write (open(cleaned_file).read())
        wrote_cleaned = True

    if not wrote_cleaned:
        intxt = os.path.join (d, os.path.basename (d) + '.text')
        if os.path.exists (intxt):
            f.write('\n')
            f.write (open(intxt).read())
    f.close()

    if startclient:
        os.system (f'emacsclient -n {txtname}')
    print ('Wrote:', os.path.join (os.getcwd(), txtname))
    return wrote_cleaned


def movedir (d):
    if not os.path.exists ('extra'):
        os.mkdir ('extra')
    os.rename (d, os.path.join ('extra', os.path.basename (d)))
    return


def showpdf (d):
    pdf = os.path.join ('extra', os.path.basename(d), os.path.basename (d) + '.pdf')
    if os.path.exists(pdf):
        os.system (f'xpdf {pdf}&')
    return


def processmd (d, startclient):
    if d[-1] == '/': d = d[:-1]
    md = readmd (os.path.join (d, 'MDFILE'))
    wrote_cleaned = writetxt (md, d, startclient)
    movedir (d)
    if startclient and not wrote_cleaned:
        showpdf (d)
    return


startclient = True
if sys.argv[1] == '-n':
    startclient = False
    del sys.argv[1]
processmd (sys.argv[1], startclient)
