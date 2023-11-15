import urllib.request
import re
import time
from urllib.error import URLError, HTTPError, ContentTooShortError
import itertools
from urllib.parse import urljoin
from urllib import robotparser
from urllib.parse import urlparse

#for pdf download
import requests
import os
#scraping
from lxml.html import fromstring


def download(url,user_agent='wswp', num_retries=2,charset='utf-8'):
    """
    Download and return html text from url
    """
    print('Downloading:', url)
    request = urllib.request.Request(url)
    request.add_header('User-agent', user_agent)
    try:
        html_b = urllib.request.urlopen(request)
        encoding = html_b.headers.get_content_charset()
        if not encoding:
            encoding=charset
        html = html_b.read().decode(encoding)
    except (URLError, HTTPError, ContentTooShortError) as e:
        print('Download error:', e.reason)
        html = None
        if num_retries > 0:
            if hasattr(e, 'code') and 500 <= e.code < 600:
                # recursively retry 5xx HTTP errors
                return download(url, num_retries - 1)
    return html


def link_crawler(start_url, link_regex,robots_url=None,user_agent='wswp',max_depth=3,delay=2,scrape_callback=None,folder=None):
    """ Crawl from the given start URL following links matched by
    link_regex
    """
    if not robots_url:
        robots_url = '{}/robots.txt'.format(start_url)
        rp = get_robots_parser(robots_url)

    throttle = Throttle(delay)# wait interval before trying to load link

    crawl_queue = [start_url]
    #keep track which URL's have seen before
    #seen = set(crawl_queue)
    seen ={}
    while crawl_queue:
        url = crawl_queue.pop()
        #check url passes robots.txt restrictions
        if rp.can_fetch(user_agent, url):
            depth = seen.get(url, 0)
            if depth == max_depth:
                print('Skipping %s due to depth' % url)
                continue
            throttle.wait(url)
            html = download(url, user_agent=user_agent)       
            if html:
                #do something with html, like scraping
                if scrape_callback:
                    tree=fromstring(html)
                    pdf_path=tree.xpath('//iframe[@id="s_pdf_frame"]/@src')
                    if pdf_path:
                        fname=str(pdf_path[0]).split("=")[-1]
                        print('Saving...',fname.split("/")[-1])
                        download_pdf(fname,folder)
                # filter for links matching our regular expression
                for link in get_links(html):
                    if re.search(link_regex, link):
                        abs_link = urljoin(start_url, link)
                        # check if have already seen this link
                        if abs_link not in seen:
                            #seen.add(abs_link)
                            seen[abs_link] = depth + 1
                            crawl_queue.append(abs_link)
            else:
                continue
        else:
            print('Blocked by robots.txt:', url)

def get_links(html):
    """ Return a list of links from html
    """
    # a regular expression to extract all links from the webpage
    webpage_regex = re.compile("""<a[^>]+href=["'](.*?)["']""",re.IGNORECASE)
    # list of all links from the webpage
    return webpage_regex.findall(html)

def get_robots_parser(robots_url):
    " Return the robots parser object using the robots_url "
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    return rp

class Throttle:
    """Add a delay between downloads to the same domain
    """
    def __init__(self, delay):
        # amount of delay between downloads for each domain
        self.delay = delay
        # timestamp of when a domain was last accessed
        self.domains = {}

    def wait(self, url):
        domain = urlparse(url).netloc
        last_accessed = self.domains.get(domain)
        if self.delay > 0 and last_accessed is not None:
            sleep_secs = self.delay - (time.time() - last_accessed)
            if sleep_secs > 0:
            # domain has been accessed recently so need to sleep
                time.sleep(sleep_secs)
            # update the last accessed time
        self.domains[domain] = time.time()


def download_pdf(url,folder):
    """
    Download pdf file from link and save to folder
    """
    # Get the file name from the URL
    file_name = url.split("/")[-1]
    # Create the folder if it does not exist
    if not os.path.exists(folder):
        os.makedirs(folder)
    # Join the folder name and the file name
    file_path = os.path.join(folder, file_name)
    # Send a GET request to the URL
    user_agent = 'wswp'
    headers = {'User-Agent':user_agent}
    response = requests.get(url,headers=headers)
    # Check if the response is successful
    if response.status_code == 200:
        # Write the content of the response to a binary file
        with open(file_path, "wb") as f:
            f.write(response.content)
        # Return the file path
        return file_path
    else:
        # Raise an exception if the response is not successful
        raise Exception(f"Failed to download PDF from {url}")

def main():
    #destination folder to save files
    dest_folder=input("Enter destination folder \t")
    if dest_folder=="":
        print("Please specify destination folder")
        return
    #link to subject webpage
    start_url=input("Copy and paste url of subject page \t")
    subject=input("Enter subjet \t")
    years=input("Enter years separated by commas \t")
    year_list=years.split(",")
    for year in year_list:
        if not year.isdigit():
            print("Skipping {} ".format())
        else:
             # select only links with the following pattern
            link_regex="{}.*{}.*[123]".format(year,subject) 
            print(link_regex)
            link_crawler(start_url, link_regex,scrape_callback=download_pdf,folder=dest_folder)
   
if __name__ == '__main__':
    main()