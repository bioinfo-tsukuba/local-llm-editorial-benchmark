#!/usr/bin/env python3
"""Reference-verification tools for T8.

T3-refs showed that 7 of 8 models cannot convert a journal name to its Index
Medicus abbreviation: the information simply is not in the weights. T8 asks
whether giving the model a lookup tool fixes that, and whether tool access
introduces new failure modes (inventing DOIs, trusting a mismatched record).

The tools are implemented carefully here so that tool quality is not the
variable under test. Journal abbreviation resolution goes:

  Crossref short-container-title  ->  if it still looks like a full title,
  fall back to NLM Catalog medlineta looked up **by ISSN** (exact) rather than
  by title (which mis-matches: "Cell" returns "Cell Press Blue", "Nature"
  returns "Nat Health").

NLM's medlineta omits periods ("Biophys J"); BPPB style uses them
("Biophys. J."), so a formatting pass is applied.
"""
import json, re, time, urllib.parse, urllib.request

UA = {'User-Agent': 'bppb-eval/1.0 (mailto:ai-biology@ml.riken.jp)'}
_cache = {}


def _get(url, timeout=25):
    if url in _cache:
        return _cache[url]
    r = urllib.request.Request(url, headers=UA)
    d = json.load(urllib.request.urlopen(r, timeout=timeout))
    _cache[url] = d
    time.sleep(0.25)
    return d


def _nlm_abbrev_by_issn(issns):
    """Exact lookup: ISSN is unambiguous, journal titles are not."""
    for issn in issns or []:
        try:
            q = urllib.parse.quote(f'{issn}[ISSN]')
            ids = _get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
                       f'?db=nlmcatalog&term={q}&retmax=1&retmode=json'
                       )['esearchresult']['idlist']
            if not ids:
                continue
            r = _get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
                     f'?db=nlmcatalog&id={ids[0]}&retmode=json')['result'][ids[0]]
            ta = (r.get('medlineta') or '').strip()
            if ta:
                return ta
        except Exception:
            continue
    return None


def _periods(abbrev, full_title):
    """NLM writes 'Biophys J'; the journal's style is 'Biophys. J.'.

    A period marks a *truncated* word, so decide per token by aligning the
    abbreviation against the full journal title: a token that is a strict prefix
    of the corresponding full word was shortened and takes a period; a token
    that reproduces the whole word does not.

      Biophysical Journal            + Biophys J          -> Biophys. J.
      Protein Engineering, Design... + Protein Eng Des Sel -> Protein Eng. Des. Sel.
      Nature                         + Nature             -> Nature
    """
    if not abbrev:
        return abbrev
    words = [w.strip(',.:;').lower() for w in (full_title or '').split()]
    keep = {'of', 'and', 'the', 'in', 'for', 'on', 'a'}
    out = []
    wi = 0
    for tok in abbrev.split():
        low = tok.strip('.').lower()
        if low in keep or tok.endswith('.') or not tok[-1].isalpha():
            out.append(tok)
            continue
        # advance through the full title to the word this token stands for
        match = None
        for j in range(wi, len(words)):
            if words[j].startswith(low):
                match, wi = words[j], j + 1
                break
        out.append(tok if match == low else tok + '.')
    return ' '.join(out)


def lookup_doi(doi):
    """Fetch the authoritative record for a DOI. Returns {'found': False} if it
    does not resolve -- the model must not invent one."""
    doi = (doi or '').strip().removeprefix('https://doi.org/').removeprefix('doi:')
    try:
        m = _get(f'https://api.crossref.org/works/{urllib.parse.quote(doi, safe="")}')['message']
    except Exception:
        return {'found': False, 'doi': doi,
                'note': 'This DOI does not resolve in Crossref.'}
    return _record(m)


def search_reference(bibliographic):
    """Find candidate records for a free-text reference. Empty list means the
    reference could not be located -- report that, do not fabricate."""
    q = urllib.parse.quote(bibliographic)
    try:
        items = _get('https://api.crossref.org/works?query.bibliographic='
                     f'{q}&rows=3&select=DOI,title,container-title,short-container-title,'
                     'ISSN,volume,page,issued,author,type')['message']['items']
    except Exception as e:
        return {'candidates': [], 'note': f'search failed: {e}'}
    return {'candidates': [_record(m, brief=True) for m in items]}


def _record(m, brief=False):
    issns = m.get('ISSN') or []
    short = (m.get('short-container-title') or [''])[0]
    full = (m.get('container-title') or [''])[0]
    abbrev, src = short, 'crossref'
    # Crossref's short-container-title is often just the full title again. Treat
    # it as unabbreviated when it carries no period and is not already a short
    # one-word name ("Cell", "Nature"), and fall back to NLM in that case.
    looks_full = (not abbrev) or ('.' not in abbrev and
                                  (len(abbrev.split()) > 1 or len(abbrev) > 6))
    if looks_full:
        ta = _nlm_abbrev_by_issn(issns)
        if ta:
            abbrev, src = _periods(ta, full), 'nlm'
    rec = {
        'found': True,
        'doi': m.get('DOI'),
        'title': (m.get('title') or [''])[0],
        'journal_full': full,
        'journal_abbreviated': abbrev,
        'abbreviation_source': src,
        'volume': m.get('volume'),
        'pages': m.get('page'),
        'year': (m.get('issued', {}).get('date-parts') or [[None]])[0][0],
        'type': m.get('type'),
    }
    if not brief:
        rec['authors'] = [f"{a.get('family','')}, {a.get('given','')[:1]}."
                          for a in m.get('author', [])]
        rec['n_authors'] = len(m.get('author', []))
    return rec


TOOL_SPECS = [
    {'type': 'function', 'function': {
        'name': 'lookup_doi',
        'description': 'Look up the authoritative bibliographic record for a DOI. '
                       'Returns found=false if the DOI does not resolve.',
        'parameters': {'type': 'object', 'required': ['doi'], 'properties': {
            'doi': {'type': 'string', 'description': 'The DOI, e.g. 10.1038/35073513'}}}}},
    {'type': 'function', 'function': {
        'name': 'search_reference',
        'description': 'Search for a reference by its bibliographic text (title, '
                       'authors, journal). Returns up to 3 candidate records, or an '
                       'empty list if nothing matches.',
        'parameters': {'type': 'object', 'required': ['bibliographic'], 'properties': {
            'bibliographic': {'type': 'string',
                              'description': 'Free-text reference, e.g. the title plus first author'}}}}},
]
DISPATCH = {'lookup_doi': lookup_doi, 'search_reference': search_reference}

if __name__ == '__main__':
    for d in ['10.1016/S0006-3495(01)76033-X', '10.1073/pnas.0702950104',
              '10.1038/35073513', '10.1016/j.cell.2007.05.020',
              '10.1093/protein/14.1.1', '10.9999/nonexistent.doi.12345']:
        r = lookup_doi(d)
        print(f"{d:38s} -> {r.get('journal_abbreviated') or r.get('note')}"
              f"  [{r.get('abbreviation_source','-')}]")
