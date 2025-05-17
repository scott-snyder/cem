#!/usr/bin/env python

import sys
import os
import json
import requests
import yaml
import time


def sanitize (s):
    s = s.replace (' ', '_')
    s = s.replace ('<', '_')
    s = s.replace ('>', '_')
    return s

def get_title1 (j):
    if 'other_title' in j and j['other_title']:
        return j['other_title'][0]
    t = j['partof_title'][0]
    ipos = t.find ('(')
    t = t[:ipos]
    return t.strip()

def get_title(j):
    t = get_title1(j)
    ipos = t.find ('published as:')
    if ipos >= 0:
        t = t[ipos+13:].strip()
    ipos = t.find ('called in error:')
    if ipos >= 0:
        t = t[ipos+16:].strip()
    ipos = t.find ('have title:')
    if ipos >= 0:
        t = t[ipos+11:].strip()
    return t

def make_dir (j):
    date = j['date']
    city = sanitize(j['location_city'][0])
    state = sanitize(j['location_state'][0])
    title = sanitize(get_title(j))
    dirbase = f'{date}-{city}-{state}-{title}'
    d = dirbase
    icount = 1
    while os.path.exists (d):
        mdfile = os.path.join (d, 'MDFILE')
        if not os.path.exists (mdfile): break
        l = open (mdfile).readline()
        fid = l.strip().split()[-1]
        if fid == j['id']: break
        icount += 1
        d = f'{dirbase}-{icount}'
    if not os.path.exists (d):
        os.mkdir (d)
    return d


def xlist (x):
    if len (x) == 1: return x[0]
    return x
def write_md (id, jitem, coords, d):
    mdfile = os.path.join (d, 'MDFILE')
    md = {
        'AAId'            : id,
        'Newspaper_Title' : xlist(jitem['item']['newspaper_title']),
        'Issue_Date'      : jitem['item']['date'],
        'State'           : xlist(jitem['item']['location_state']),
        'City'            : xlist(jitem['item']['location_city']),
        'LCCN'            : xlist(jitem['item']['number_lccn']),
        'Contributor'     : xlist(jitem['item']['contributor_names']),
        'Batch'           : xlist(jitem['item']['batch']),
        'Page'            : jitem['pagination']['current'],
        'ZZCoordinates'   : coords,
        'PDF link'        : jitem['resource']['pdf'],
        }
    yaml.dump (md, open (mdfile, 'w'))
    return


def get_pdf (jitem, d, dosleep):
    pdffile = os.path.join (d, d) + '.pdf'
    if not os.path.exists (pdffile):
        r = requests.get (jitem['resource']['pdf'])
        if dosleep: time.sleep(4)
        fpdf = open (pdffile, 'wb')
        fpdf.write (r.content)
        fpdf.close()
    return


def write_ocr (jitem, d):
    ocrfile = os.path.join (d, d) + '.text'
    open (ocrfile, 'w').write (jitem['full_text'])
    return


def write_pagecoor (pc, d):
    snipfile = os.path.join (d, 'matched.text')
    open (snipfile, 'w').write (pc['relevant_snippet'])
    out = []
    h = float (pc['height'])
    w = float (pc['width'])
    for c in pc['coords_list']:
        out.append ([c[0]/w, c[1]/h, c[2]/w, c[3]/h])
    return out


def process_json (fname, dosleep):
    for i in range(4):
        j = json.load (open (fname))
        d = make_dir (j)
        print (fname, d)
        if 'page_coordinate_data' in j:
            coords = write_pagecoor (j['page_coordinate_data'], d)
        else:
            coords = None
        item = requests.get (j['id'] + '&fo=json')
        try:
            jitem = item.json()
        except requests.exceptions.JSONDecodeError as err:
            print (err)
            time.sleep(4)
            continue
        write_md (j['id'], jitem, coords, d)
        get_pdf (jitem, d, dosleep)
        write_ocr (jitem, d)
        os.rename (fname, fname+'-done')
        if dosleep: time.sleep(4)
        return

    os.rename (fname, fname+'-bad')
    return


dosleep = len (sys.argv[1:]) > 2
for j in sys.argv[1:]:
    process_json (j, dosleep)
