import os
import glob
from array import array
import pandas as pd
from scipy.stats import kstest, ttest_ind_from_stats, ttest_ind, distributions
import numpy as np
import matplotlib.pyplot as plt
from nltk.sentiment.vader import SentimentIntensityAnalyzer, SentiText
from collections import namedtuple
import ROOT

minyear = 1872
maxyear = 1882

if not 'style_loaded' in globals():
    mydir = '.'
    ROOT.gROOT.LoadMacro (os.path.join (mydir, 'atlas-macros/AtlasStyle.C'))
    ROOT.gROOT.LoadMacro (os.path.join (mydir, 'atlas-macros/AtlasUtils.C'))
    ROOT.gROOT.LoadMacro (os.path.join (mydir, 'atlas-macros/AtlasLabels.C'))
    ROOT.gROOT.ProcessLine ("SetAtlasStyle();")
    ROOT.gStyle.SetErrorX (0)
    ROOT.gStyle.SetPadTickX(0);
    ROOT.gStyle.SetPadTickY(0);
    style_loaded = True

    #xblue = ROOT.TColor (1300, 0.12, 0.46, 0.70, 'xblue')
    xblue = ROOT.TColor (1301, 38/256, 152/256, 227/256, 'xblue')

plt.ion()

regions = {
    # Northeast
    1 : [ 'CT', 'ME', 'MA', 'NH', 'RI', 'VT', # new england
          'NJ', 'NY', 'PA',                   # mid-atlantic
         ],
    # Midwest
    2 : [ 'IL', 'IN', 'MI', 'OH', 'WI',       # east north central
          'IA', 'KS', 'MN', 'MO', 'NE', 'ND', 'SD', # west north central
         ],
    # South
    3 : [ 'DE', 'DC', 'FL', 'GA', 'MD', 'NC', 'SC', 'VA', 'WV', # south atlantic
          'AL', 'KY', 'MS', 'TN',  # east south central
          'AR', 'LA', 'OK', 'TX', # west south central
          ],
    # West
    4 : [ 'AZ', 'CO', 'ID', 'MT', 'NV', 'NM', 'UT', 'WY', # mountain
          'AK', 'CA', 'HI', 'OR', 'WA', # pacific
          ],
    }

regions_map = {}
for r, states in regions.items():
    for s in states:
        regions_map[s] = r


class Article:
    def __init__ (self, fname):
        self.key = os.path.splitext (os.path.basename (fname))[0]
        f = open (fname)
        self.title = ''
        self.paper = ''
        self.page = ''
        self.url = ''
        while True:
            l = f.readline().strip()
            if not l or l == '---': break
            key, val = l.split (':', 1)
            key = key.strip()
            val = val.strip()
            if key == 'Date':
                self.date = val
                self.year = int (val.split('-')[0])
            elif key == 'State':
                self.state = val.split()[0]
                self.region = regions_map[self.state]
            elif key == 'Title':
                self.title = val
            elif key == 'Paper':
                self.paper = val
            elif key == 'Page':
                self.page = val
            elif key == 'Url':
                self.url= val
            elif key == 'Paperkey':
                self.paperkey= val
        self.text = f.read()
        f.close()
        return


    def valences (self):
        sid = SentimentIntensityAnalyzer()
        sentitext = SentiText(self.text,
                              sid.constants.PUNC_LIST,
                              sid.constants.REGEX_REMOVE_PUNCTUATION)
        words = sentitext.words_and_emoticons
        sentiments = []
        valence = 0
        for item in words:
            i = words.index(item)
            sentiments = sid.sentiment_valence (valence, sentitext, item, i, sentiments)
        valences = [x for x in zip (sentiments, words) if x[0] != 0]
        valences.sort (key = lambda x: x[0])
        return valences


class Articles (dict):
    def __init__ (self, d):
        for fname in glob.glob (os.path.join (d, '1*/*.txt')):
            a = Article(fname)
            self[a.key] = a
        return


    def scale (self, x):
        return (x+1)*50


    def cat (self, score):
        if score < -0.8:
            return -2
        elif score < -0.2:
            return -1
        elif score < 0.2:
            return 0
        elif score < 0.8:
            return 1
        return 2


    def vader (self):
        sid = SentimentIntensityAnalyzer()
        for a in self.values():
            a.vader = sid.polarity_scores(a.text)
            a.vader_scaled = self.scale(a.vader['compound'])
            a.vader_cat = self.cat (a.vader['compound'])
        return


    def vader_nr (self):
        sid = SentimentIntensityAnalyzer()
        del sid.lexicon['regret']
        for a in self.values():
            a.vader_nr = sid.polarity_scores(a.text)
            a.vader_nr_cat = self.cat (a.vader_nr['compound'])
        return


    def pd (self):
        year = []
        region = []
        vader = []
        vader_cat = []
        vader_nr = []
        vader_nr_cat = []
        key = []
        for a in self.values():
            key.append (a.key)
            year.append (a.year)
            region.append (a.region)
            vader.append (self.scale(a.vader['compound']))
            vader_cat.append (a.vader_cat)
            vader_nr.append (self.scale(a.vader_nr['compound']))
            vader_nr_cat.append (a.vader_nr_cat)
        return pd.DataFrame ({ 'year' : year,
                               'region' : region,
                               'vader'  : vader,
                               'vader_cat'  : vader_cat,
                               'vader_nr'  : vader_nr,
                               'vader_nr_cat'  : vader_nr_cat,
                               'key'    : key})


    def tree (self):
        t = ROOT.TTree ('articles', 'articles')
        self.tyear = array ('I', [0])
        self.tvader = array ('f', [0])
        self.tvader_cat = array ('i', [0])
        self.tvader_nr = array ('f', [0])
        self.tvader_nr_cat = array ('i', [0])
        self.tregion = array ('I', [0])
        t.Branch ('year', self.tyear, 'year/I')
        t.Branch ('vader', self.tvader, 'vader/F')
        t.Branch ('vader_cat', self.tvader_cat, 'vader_cat/I')
        t.Branch ('vader_nr', self.tvader_nr, 'vader_nr/F')
        t.Branch ('vader_nr_cat', self.tvader_nr_cat, 'vader_nr_cat/I')
        t.Branch ('region', self.tregion, 'region/I')
        for a in self.values():
            self.tyear[0] = a.year
            self.tvader[0] = self.scale(a.vader['compound'])
            self.tvader_cat[0] = a.vader_cat
            self.tvader_nr[0] = self.scale(a.vader_nr['compound'])
            self.tvader_nr_cat[0] = a.vader_nr_cat
            self.tregion[0] = a.region
            t.Fill()
        return t
                           

text="""The 51 Chinese students who passed through the city this week on their
way from Hartford to San Francisco, being the second installment
ordered home by their government, attracted considerable attention
during the short time they were in town. About all their
fellow-students left here were on hand to see the party off, as well
as many of their white friends.  They say that the third and last
installment of students will start for China in about two weeks. The
party includes Lee Yan Foo, who studied here seven years and was well
known to all recent members of the high school."""

text1="The 51 Chinese students who passed through the city this week on their way from Hartford to San Francisco, being the second installment ordered home by their government, attracted considerable attention during the short time they were in town."
text2="About all their fellow-students left here were on hand to see the party off, as well as many of their white friends."
text3="They say that the third and last installment of students will start for China in about two weeks."
text4="The party includes Lee Yan Foo, who studied here seven years and was well known to all recent members of the high school."

#sid = SentimentIntensityAnalyzer()
#print (sid.polarity_scores(text))

#a = Article ('/home/sss/cem/cem/newspapers/1885/1885-01-02-springfield_republican.txt')
a = Articles('../newspapers')
a.vader()
a.vader_nr()
t = a.tree()

cat_labels = ['Strongly negative',
              'Negative',
              'Neutral',
              'Positive',
              'Strongly positive']
def bincat (df):
    return pd.cut(df, (-2.5,-1.5,-0.5,0.5,1.5,2.5),labels=cat_labels).value_counts(sort=False)

chisquareResult = namedtuple('chisquareResult',
                             ('statistic', 'pvalue'))

def chisquare (f1, f2):
    # arxiv:physics/0605123
    M = sum(f1)
    N = sum(f2)
    chisquare_elt = np.frompyfunc (lambda m, n: (M*n-N*m)**2/(n+m), 2, 1)
    aa = chisquare_elt (f1, f2)
    stat = sum (chisquare_elt (f1, f2)) / (M*N)
    p = distributions.chi2.sf(stat, len(f1) - 1 )
    return chisquareResult(stat, p)
    
    

df = a.pd()
df_years = df[(df['year']>=1872) & (df['year']<=1882)]
scores_r1 = df_years[df_years['region']==1]['vader']
scores_r2 = df_years[df_years['region']==2]['vader']
scores_r3 = df_years[df_years['region']==3]['vader']
scores_r4 = df_years[df_years['region']==4]['vader']
cat_r1 = bincat(df_years[df_years['region']==1]['vader_cat'])
cat_r2 = bincat(df_years[df_years['region']==2]['vader_cat'])
cat_r3 = bincat(df_years[df_years['region']==3]['vader_cat'])
cat_r4 = bincat(df_years[df_years['region']==4]['vader_cat'])
for i in range(1872, 1883):
    globals()[f'scores_{i}'] = df_years[df_years['year']==i]['vader']
    globals()[f'cat_{i}'] = bincat(df_years[df_years['year']==i]['vader_cat'])
scores_before = df_years[df_years['year']<=1880]['vader']
scores_after = df_years[df_years['year']>=1881]['vader']
cat_before = bincat(df_years[df_years['year']<=1880]['vader_cat'])
cat_after = bincat(df_years[df_years['year']>=1881]['vader_cat'])
def print_stats1 (df, name):
    print (f'{name:10s} N={len(df)} mean={df.mean():5.3} std={df.std():.3}')
    return
def print_stats():
    print_stats1 (scores_r1, 'Region 1')
    print_stats1 (scores_r2, 'Region 2')
    print_stats1 (scores_r3, 'Region 3')
    print_stats1 (scores_r4, 'Region 4')
    scores_r12 = pd.concat ([scores_r1, scores_r2])
    scores_r34 = pd.concat ([scores_r3, scores_r4])
    #scores_r124 = pd.concat ([scores_r1, scores_r2, scores_r4])
    cat_r12 = cat_r1 + cat_r2
    cat_r34 = cat_r3 + cat_r4
    print_stats1 (scores_r12, 'Regions 1,2')
    print_stats1 (scores_r34, 'Regions 3,4')
    #print_stats1 (scores_r124, 'Regions 1,2,4')
    print ('KS 1 vs 3:', kstest(scores_r1, scores_r3).pvalue)
    print ('KS 1,2 vs 3,4:', kstest(scores_r12, scores_r34).pvalue)
    #print ('KS 1,2,4 vs 3:', kstest(scores_r124, scores_r3).pvalue)
    print ('ttest 1,2 vs 3,4:',
           ttest_ind(scores_r12, scores_r34).pvalue)
    print ('chisq 1,2 vs 3,4',
           chisquare(cat_r12, cat_r34).pvalue)

    for i in range(1872, 1883):
        print_stats1 (globals()[f'scores_{i}'], str(i))
    print_stats1 (scores_before, 'Before')
    print_stats1 (scores_after, 'After')
    print_stats1 (df_years['vader'], 'All')
    print ('KS before vs after:', kstest(scores_before, scores_after).pvalue)
    print ('ttest before vs after:',
           ttest_ind(scores_before, scores_after).pvalue)
    print ('chisq before and after',
           chisquare(cat_before, cat_after).pvalue)
    return
#xx=pd.cut(df_years['vader_cat'], (-2.5,-1.5,-0.5,0.5,1.5,2.5),labels=['a','b','c','d','e']).value_counts(sort=False)



def printplot (name):
    ROOT.c1.Print (name + '.pdf', 'pdf,Portrait')
    ROOT.c1.Print (name + '.svg')
    ROOT.c1.Print (name + '.png')
    return


def label_cats(ax):
    for i,l in enumerate(cat_labels):
        ax.SetBinLabel (i+1, l)
    return

    
def label_regions(ax):
    ax.SetBinLabel (1, 'Northeast')
    ax.SetBinLabel (2, 'Midwest')
    ax.SetBinLabel (3, 'South')
    ax.SetBinLabel (4, 'West')
    return

    
def label_years(ax):
    nbins = maxyear - minyear + 1
    for i in range(nbins):
        ax.SetBinLabel (i+1, str(minyear+i))
    return

    
def year_plot(t):
    nbins = maxyear - minyear + 1
    h = ROOT.TH1I ('year', 'year', nbins, minyear, maxyear+1)
    h.SetFillColor(xblue.GetNumber())
    t.Project ('year', 'year', f'year>={minyear}&&year<={maxyear}')
    h.SetMinimum(0)
    h.SetNdivisions(10, axis='Y')
    h.GetYaxis().SetTitle('Number of articles/year')
    h.GetYaxis().SetTitleOffset(1.1)
    h.GetXaxis().SetLabelOffset(0.01)
    label_years (h.GetXaxis())
    h.GetXaxis().SetTitle('Article date')
    h.GetXaxis().SetLabelOffset(0.01)
    h.GetXaxis().SetTitleOffset(1.5)
    h.SetLineWidth(0)
    h.Draw()
    printplot ('year_plot')
    return h

def region_plot(t):
    h = ROOT.TH1I ('regions', 'regions', 4, 1, 5)
    h.SetFillColor(xblue.GetNumber())
    t.Project ('regions', 'region', f'year>={minyear}&&year<={maxyear}')
    h.SetNdivisions(10, axis='Y')
    h.SetMinimum(0)
    h.GetYaxis().SetTitle('Number of articles/region')
    h.GetYaxis().SetTitleOffset(1.1)
    label_regions (h.GetXaxis())
    h.GetXaxis().SetTitle('Article region')
    h.GetXaxis().SetLabelOffset(0.01)
    h.GetXaxis().SetTitleOffset(1.5)
    h.SetLineWidth(0)
    h.Draw()
    printplot ('region_plot')
    return h


def score_plot(t, nr = False):
    nrs = '_nr' if nr else ''
    h = ROOT.TH1I ('scores'+nrs, 'scores'+nrs, 5, -2, 3)
    h.SetFillColor(xblue.GetNumber())
    h.Draw()
    h.SetNdivisions(10, axis='Y')
    ROOT.gInterpreter.EndOfLineAction()
    c1 = ROOT.c1
    rm  = c1.GetRightMargin()
    c1.SetRightMargin(0.1)
    t.Project ('scores'+nrs, f'vader{nrs}_cat', f'year>={minyear}&&year<={maxyear}')
    h.SetMinimum(0)
    h.GetYaxis().SetTitle('Number of articles')
    h.GetYaxis().SetTitleOffset(1.1)
    label_cats(h.GetXaxis())
    h.GetXaxis().SetTitle('Article sentiment')
    h.GetXaxis().SetLabelOffset(0.01)
    h.SetLineWidth(0)
    h.Draw()
    printplot ('score_plot'+nrs)
    ROOT.gInterpreter.EndOfLineAction()
    c1.SetRightMargin(rm)
    return h


def score_vs_region(t, nr = False):
    nrs = '_nr' if nr else ''
    h = ROOT.TH2I (f'score{nrs}_vs_region', f'score{nrs}_vs_region', 4, 1, 5, 5, -2, 3)
    h.Draw()
    ROOT.gInterpreter.EndOfLineAction()
    c1 = ROOT.c1
    lm  = c1.GetLeftMargin()
    c1.SetLeftMargin(0.2)
    t.Project (f'score{nrs}_vs_region', f'vader{nrs}_cat:region', f'year>={minyear}&&year<={maxyear}')
    h.SetMinimum(0)
    label_cats(h.GetYaxis())
    label_regions(h.GetXaxis())
    h.GetYaxis().SetTitle('Article sentiment               ')
    h.GetYaxis().SetTitleOffset(2)
    h.GetXaxis().SetTitle('Article region')
    h.SetMarkerSize(2)
    #h.Draw('BOX,TEXT')
    h.SetFillColor(xblue.GetNumber())
    h.SetLineWidth(0)
    h.Draw('VIOLINX(03000000)')
    h.Draw('TEXT,SAME')
    printplot (f'score{nrs}_vs_region')
    ROOT.gInterpreter.EndOfLineAction()
    c1.SetLeftMargin(lm)
    return h


def score_vs_year(t, nr = False):
    nrs = '_nr' if nr else ''
    nbins = maxyear - minyear + 1
    h = ROOT.TH2I (f'score{nrs}_vs_year', f'score{nrs}_vs_year', nbins, minyear, maxyear+1, 5, -2, 3)
    h.Draw()
    ROOT.gInterpreter.EndOfLineAction()
    c1 = ROOT.c1
    lm  = c1.GetLeftMargin()
    c1.SetLeftMargin(0.2)
    t.Project (f'score{nrs}_vs_year', f'vader{nrs}_cat:year', f'year>={minyear}&&year<={maxyear}')
    h.SetMinimum(0)
    label_cats(h.GetYaxis())
    label_years (h.GetXaxis())
    h.GetYaxis().SetTitle('Article sentiment               ')
    h.GetYaxis().SetTitleOffset(2)
    h.GetXaxis().SetTitle('Article year')
    h.SetMarkerSize(2)
    #h.Draw('BOX,TEXT')
    h.SetFillColor(xblue.GetNumber())
    h.SetLineWidth(0)
    h.Draw('VIOLINX(03000000)')
    h.Draw('TEXT,SAME')
    printplot (f'score{nrs}_vs_year')
    ROOT.gInterpreter.EndOfLineAction()
    c1.SetLeftMargin(lm)
    return h


#########################################################################


def year_plot2():
    fig, ax = plt.subplots()
    ax.tick_params(direction='in')
    ax.hist(df_years['year'],
            bins=maxyear-minyear+1,
            range=(minyear, maxyear+1))
    ax.xaxis.set_minor_locator(matplotlib.ticker.AutoLocator())
    ax.xaxis.set_minor_formatter(matplotlib.ticker.ScalarFormatter())
    ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())

    ax.locator_params(axis='x', steps=[1])
    #ax.set_xlim ([minyear, maxyear+1])
    #ax.set_ylabel ('Number of articles/year', loc='top')
    #ax.set_xlabel ('Article year', loc='right')
    #years, counts = np.unique (df_years['year'], return_counts=True)
    #ax.bar (years, counts, width=1, align='edge')

    return ax
    nbins = maxyear - minyear + 1
    h = ROOT.TH1I ('year', 'year', nbins, minyear, maxyear+1)
    t.Project ('year', 'year', f'year>={minyear}&&year<={maxyear}')
    h.SetMinimum(0)
    h.GetYaxis().SetTitle('Number of articles/year')
    h.GetYaxis().SetTitleOffset(1.1)
    label_years (h.GetXaxis())
    h.GetXaxis().SetTitle('Article date')
    h.GetXaxis().SetLabelOffset(0.01)
    h.GetXaxis().SetTitleOffset(1.5)
    h.LabelsOption('v', 'x')
    h.Draw()
    printplot ('year_plot')
    return h


def mean_plot2():
    years = list (range(1872, 1883))
    means = [globals()[f'scores_{i}'].mean() for i in years]
    fig, ax = plt.subplots()
    ax.tick_params(direction='in')
    ax.set_ylim ([0, 100])
    ax.locator_params(axis='x', steps=[1])
    ax.plot (years, means, 'bo-')
    ax.set_ylabel ('Mean article score', loc='top')
    ax.set_xlabel ('Article year', loc='right')
    fig.savefig('mean_plot.svg')
    fig.savefig('mean_plot.pdf')
    fig.savefig('mean_plot.png')
    return (years, means)


def all_plots(t):
    year_plot(t)
    region_plot(t)
    score_plot(t)
    score_vs_region(t)
    score_vs_year(t)

    mean_plot2()
    return


#########################################################################


def cap_word (w):
    if w == 'New-York': return 'New York'
    if (w) == 'and': return w
    return w.capitalize()
def cap_words (s):
    return ' '.join ([cap_word(x) for x in s.split()])
def clean_paper1(p):
    if p == '"Vermont ph\\u0153nix."': return 'Vermont Phoenix'
    if p[-1] == '.':
        p = p[:-1]
    return cap_words(p)
def clean_paper(p, state, city):
    p = clean_paper1(p)
    return f'/{p}/ ({cap_words(city)}, {state})'
def read_papers():
    f = open ('../newspapers/LIST')
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
            state, city = paper.split(';')[1].split(None, 1)
            paper = paper.split(';')[0].strip()
            if len(fields) == 2:
                if fields[0] not in d:
                    d[fields[0]] = clean_paper(paper, state, city)
    return d


months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
    ]
def format_date (art):
    d = art.date
    year = d[:4]
    month = int(d[5:7])
    day = int(d[8:10])
    return f'{months[month-1]} {day}, {year}'
def format_paper (art, papers):
    pname = papers[art.paperkey]
    return f'{pname},'

def write_org():
    papers = read_papers()
    years = {}
    for k, v in a.items():
        y = k[:4]
        years.setdefault(y, []).append (v)
    for v in years.values():
        v.sort (key = lambda x: x.key)
    f = open ('articles.org', 'w')
    icount = 1
    for y in range(minyear, maxyear+1):
        print (f'   - {y}', file=f)
        for art in years[str(y)]:
            #if art.title:
            #    print (art.key, art.title)
            title = art.title
            if title:
                if title[-1] == '.': title = title[:-1]
                title = f'"{title}," '
            url = f', [[{art.url}]]' if art.url else ''
            page = f', {art.page}' if art.page else ''
            print (f'      {icount}. [@{icount}]\\zwj {title}{format_paper(art, papers)} {format_date(art)}{page}{url}.', file=f)
            icount += 1
        print (f'', file=f)
        pass
    f.close()
    return


def write_org2(text = False):
    papers = read_papers()
    years = {}
    arts = list (a.values())
    arts.sort (key = lambda x: x.vader_scaled)
    nm = 'articles3.org' if text else 'articles2.org'
    f = open (nm, 'w')
    icount = 1
    for art in arts:
        if art.year >= minyear and art.year <= maxyear:
            title = art.title
            if title:
                if title[-1] == '.': title = title[:-1]
                title = f'"{title}," '
            url = f', [[{art.url}]]' if art.url else ''
            page = f', {art.page}' if art.page else ''
            print (f'      {icount}. [@{icount}]\\zwj {art.vader_scaled:4.1f} ={art.key}= {title}{format_paper(art, papers)} {format_date(art)}{page}{url}.', file=f)
            if text:
                print ('#+BEGIN_QUOTE', file=f)
                f.write (art.text)
                print ('#+END_QUOTE', file=f)
            icount += 1
    f.close()
    return


def execfile():
    exec(open('ana.py').read(), globals())
    return
