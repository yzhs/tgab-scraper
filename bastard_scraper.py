import urllib.request, os
from urllib.request import HTTPError
from bs4 import BeautifulSoup
from itertools import count
from textdistance import levenshtein, jaccard

"""
bastard_scraper.py
brought to you by: nokko
NOTE: TGaB is a large work, totalling 2,812,577 words as of Chapter 15-76
This script downloads the entire HTML page for each chapter. This means that
around 136MB of HTML is downloaded, and ~20MB of sanitized HTML is emitted.
"""
# set to True if want to keep the original HTML version with comments
keep_ingested = False

# start from the beginning
start_url = 'https://tiraas.wordpress.com/2014/08/22/1-1/'
current = urllib.request.Request(start_url)

def get_final_size():
    """
   Iterates through all the files in the working directory, gets their sizes.
   Returns the size in MB.
   """
    files = [f"{os.getcwd()}/{f}" for f in os.listdir('.') if os.path.isfile(f)]
    sizes = [os.path.getsize(f) for f in files]
    return round(sum(sizes) / 1_000_000, 2)


def download_chapter(i: int, current: str) -> (BeautifulSoup, str):
    with urllib.request.urlopen(current) as response:
        if response.code != 200:
            return None, None
        first_chapter = response.read()
        soup = BeautifulSoup(first_chapter, features="html.parser")
        title = soup.title.get_text()
        # Write ingest result to file
        if keep_ingested:
            with open(f'{os.getcwd()}/input/[{i + 1:03}] {title}.html', 'w') as out:
                out.write(soup.prettify(formatter='html5'))
    return soup, title

def add_title_heading(story: BeautifulSoup):
    new_tag = soup.new_tag('h1')
    new_tag.string = soup.title.get_text().replace(' | The Gods are Bastards', '')
    story.insert(0, new_tag)

def make_top_level_tag_body(story: BeautifulSoup):
    story.name = "body"
    del story['class']

# Page Gathering:
for i in count():
    # Try to open the URL provided, break on errors like a 404, etc.
    try:
        soup, title = download_chapter(i, current)
        if not soup:
            break
    except HTTPError as err:
        print(err)
        break

    # story is everything inside the first div.entry-content we find
    story = soup.find('div', {'class': 'entry-content'})

    # Remove Share link garbage
    story.find(attrs={'id': 'jp-post-flair'}).decompose()
    print(soup.title.get_text())

    # the next link we follow is the second one on the page,
    # unless it is too dissimilar from "Next Chapter &gt;"
    next_url, next_link = story.find_all('a')[1]['href'], story.find_all('a')[1].get_text()

    # make all the links point to nowhere
    # TODO: perhaps delete them? or delete every link except the vote link using jaccard
    for anchor in story.find_all('a'):
        anchor['href'] = ""

    add_title_heading(story)
    make_top_level_tag_body(story)

    paragraphs = story.find_all('p')
    paragraphs[0].decompose()
    paragraphs[-1].decompose()

    # write result to file
    with open(f'{os.getcwd()}/[{i + 1:03}] {title}.html', 'w') as out:
        out.write(f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/#" lang="en-US" xml:lang="en-US">
  <head>
    <title>{title}</title>
    <link href="style/main.css" rel="stylesheet" type="text/css"/>
  </head>
""")
        out.write(story.prettify(formatter='html5'))
        out.write("</html>\n")

    # figure out if the link we've selected with story.a[1] is in fact a "Next Chapter" link
    # by comparing its jaccard index to that of a template link
    jaccard_index = jaccard("Next Chapter &gt;".split(), next_link.split())
    if jaccard_index > 0.1:
        current = next_url
    # TODO: log similarity here?
    else:  # end scraping once next_link isn't a Next link
        print(f"""{'=' * 64}
Scraping ended at {current}.
Reason: "Next Chapter" link too dissimilar from template.
Jaccard index of "{"Next Chapter &gt;"}" and "{next_link}" = {jaccard_index}
Scraped {i + 1} pages, totalling {get_final_size()} MB.""")
        break
