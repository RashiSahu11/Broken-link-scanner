import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import concurrent.futures
import time

#----------------------------------------
#function 1: Check whelter a url is valid
#----------------------------------------

def is_valid_url(url):
    """
    This function checks whelter the given url
    is a proper/complete url.

    Example of invalid url:
    https://example.com

    Example of invalid url:
    hello
    /about
    """
#urlparse()breaksthe url into different components 
parsad = urlparse(url)

#netloc means the domain name
#scheme means http/https
#Both should exist for a complete url.
#bool()converts the value into True or False
return bool(parsed.netloc)and bool (parsed.scheme)

#-----------------------------------------------------
#function 2:Check whelter a link is working or broken
#-----------------------------------------------------
def check_link(url,timeout = 5):
    """
     Checks whelter a url is working or broken
     Returns
     (status_code,error)

     Example of working url:
    (200,None)
    Example of broken url:
    (404."HTTP Error 404")
    timeout = 5 means we wait maximum around 5 seconds
    for the website response
    """
    #try is used because network requests can fail
    #we don't want the entire program to crash
    #because one url has a peoblem.
    try:
     #user-agent tells the website that the request
     #is coming from a browser-like client.
     headers={
     'User-Agent':
     'Mozilla/5.0(Windows NT 10.0; Win64; x64)'
     'AppleWebKit/537.36'
     }

#-----------------------------------------------------------------------
#First try a head request
#-----------------------------------------------------------------------
#
#HEAD request checks the response information
#without downloading the complete webpages
#
#this is generally faster than GET
response=requests.head(
    url,
    headers=headers,
    
    #If the Website redirects the request,
    #automatically follow the redirect.
    allow_redirects = True,
    #Don't wait forever for a website.
    timeout =timeout
)
# -------------------------------------------------
        # IF HEAD REQUEST DOES NOT WORK PROPERLY
        # -------------------------------------------------

        # Some websites do not allow HEAD requests.
        if response.status_code in [404, 405, 400, 403]:
            response = requests.get(
                url,
                headers=headers,
                allow_redirects=True,
                timeout=timeout,
                stream=True
            )

            # We only need the response status.
            response.close()

        # -------------------------------------------------
        # CHECK HTTP STATUS CODE
        # -------------------------------------------------

        if response.status_code >= 400:
            return (
                response.status_code,
                f"HTTP Error {response.status_code}"
            )

        # Status codes below 400 are considered working.
        return response.status_code, None

    # -----------------------------------------------------
    # HANDLE TIMEOUT ERROR
    # -----------------------------------------------------

    except requests.exceptions.Timeout:
        return None, "Request Timed Out"

    # -----------------------------------------------------
    # HANDLE TOO MANY REDIRECTS
    # -----------------------------------------------------

    except requests.exceptions.TooManyRedirects:
        return None, "Too Many Redirects"

    # -----------------------------------------------------
    # HANDLE OTHER REQUEST/NETWORK ERRORS
    # -----------------------------------------------------

    except requests.exceptions.RequestException:
        return None, "Connection Error"


# ---------------------------------------------------------
# FUNCTION 3: CRAWL THE WEBSITE
# ---------------------------------------------------------

def crawl_website(
    start_url,
    max_depth=2,
    max_pages=100,
    same_domain_only=True,
    max_threads=10
):
    """
    Crawls a website starting from start_url.

    Parameters:
        start_url:
            The website from where crawling should start.

        max_depth:
            How deeply we should crawl.
            Depth 0 -> Home page
            Depth 1 -> Links found on Home
            Depth 2 -> Links found on Depth 1 pages

        max_pages:
            Maximum number of URLs/pages to process.

        same_domain_only:
            If True, continue crawling only within
            the same website/domain.

        max_threads:
            Number of URLs that can be checked simultaneously.

    The function uses yield so that it can provide
    progress updates while crawling.
    """

    # -----------------------------------------------------
    # GET THE DOMAIN OF THE STARTING WEBSITE
    # -----------------------------------------------------

    domain = urlparse(start_url).netloc

    # -----------------------------------------------------
    # SET OF ALREADY VISITED URLS
    # -----------------------------------------------------

    visited = set()

    # -----------------------------------------------------
    # URL QUEUE
    # -----------------------------------------------------

    # Each item contains:
    # 1. URL
    # 2. Depth
    # 3. Source page

    to_visit = [
        (start_url, 0, start_url)
    ]

    # -----------------------------------------------------
    # STORE ALL BROKEN LINKS
    # -----------------------------------------------------

    broken_links = []

    # -----------------------------------------------------
    # COUNT HOW MANY PAGES/URLS WE HAVE PROCESSED
    # -----------------------------------------------------

    pages_crawled = 0

    # -----------------------------------------------------
    # CREATE THREAD POOL
    # -----------------------------------------------------

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max_threads
    ) as executor:

        # -------------------------------------------------
        # MAIN CRAWLING LOOP
        # -------------------------------------------------

        while to_visit and pages_crawled < max_pages:

            # -------------------------------------------------
            # CREATE CURRENT BATCH
            # -------------------------------------------------

            current_batch = to_visit.copy()
            to_visit.clear()

            # -------------------------------------------------
            # STORE FUTURE -> URL INFORMATION
            # -------------------------------------------------

            future_to_url = {}

            # -------------------------------------------------
            # SUBMIT EACH URL TO A WORKER THREAD
            # -------------------------------------------------

            for url, depth, source in current_batch:

                # If this URL was already visited,
                # don't process it again.
                if url in visited:
                    continue

                # Stop if maximum page limit is reached.
                if pages_crawled >= max_pages:
                    break

                # Mark this URL as visited.
                visited.add(url)

                # Increase the number of crawled pages.
                pages_crawled += 1

                # Run check_link() in a background thread.
                future = executor.submit(
                    check_link,
                    url
                )

                # Remember which URL this future belongs to.
                future_to_url[future] = (
                    url,
                    depth,
                    source
                )

            # -------------------------------------------------
            # PROCESS RESULTS AS SOON AS THEY FINISH
            # -------------------------------------------------

            for future in concurrent.futures.as_completed(
                future_to_url
            ):

                # Get URL, depth and source page.
                url, depth, source = future_to_url[future]

                # -------------------------------------------------
                # GET RESULT FROM check_link()
                # -------------------------------------------------

                try:
                    status_code, error = future.result()

                except Exception as exc:
                    status_code, error = None, str(exc)

                # -------------------------------------------------
                # SEND LIVE PROGRESS UPDATE
                # -------------------------------------------------

                yield {
                    "type": "progress",
                    "crawled": len(visited),
                    "broken_count": len(broken_links),
                    "current_url": url
                }

                # -------------------------------------------------
                # IF URL IS BROKEN
                # -------------------------------------------------

                if error:
                    broken_links.append({
                        "Broken URL": url,
                        "Source Page": source,
                        "Status Code": (
                            status_code
                            if status_code
                            else "N/A"
                        ),
                        "Error": error
                    })

                # -------------------------------------------------
                # IF URL IS WORKING
                # -------------------------------------------------

                else:

                    # -------------------------------------------------
                    # CHECK WHETHER WE SHOULD GO DEEPER
                    # -------------------------------------------------

                    if depth < max_depth:

                        # -------------------------------------------------
                        # CHECK DOMAIN
                        # -------------------------------------------------

                        if (
                            not same_domain_only
                            or urlparse(url).netloc == domain
                        ):

                            try:
                                # -------------------------------------------------
                                # DOWNLOAD THE CURRENT WEBPAGE
                                # -------------------------------------------------

                                headers = {
                                    "User-Agent": "Mozilla/5.0"
                                }

                                res = requests.get(
                                    url,
                                    headers=headers,
                                    timeout=5
                                )

                                # -------------------------------------------------
                                # CHECK WHETHER RESPONSE IS HTML
                                # -------------------------------------------------

                                if "text/html" in res.headers.get(
                                    "Content-Type",
                                    ""
                                ):

                                    # -------------------------------------------------
                                    # PARSE HTML USING BEAUTIFULSOUP
                                    # -------------------------------------------------

                                    soup = BeautifulSoup(
                                        res.text,
                                        "html.parser"
                                    )

                                    # -------------------------------------------------
                                    # FIND ALL ANCHOR TAGS
                                    # -------------------------------------------------

                                    for a_tag in soup.find_all(
                                        "a",
                                        href=True
                                    ):

                                        # -------------------------------------------------
                                        # GET href VALUE
                                        # -------------------------------------------------

                                        href = a_tag["href"]

                                        # -------------------------------------------------
                                        # CONVERT RELATIVE URL TO FULL URL
                                        # -------------------------------------------------

                                        next_url = urljoin(
                                            url,
                                            href
                                        )

                                        # -------------------------------------------------
                                        # REMOVE URL FRAGMENT
                                        # -------------------------------------------------

                                        next_url = urlparse(
                                            next_url
                                        )._replace(
                                            fragment=""
                                        ).geturl()

                                        # -------------------------------------------------
                                        # CHECK URL
                                        # -------------------------------------------------

                                        if (
                                            is_valid_url(next_url)
                                            and next_url not in visited
                                        ):

                                            # -------------------------------------------------
                                            # ADD URL TO NEXT BATCH
                                            # -------------------------------------------------

                                            to_visit.append(
                                                (
                                                    next_url,
                                                    depth + 1,
                                                    url
                                                )
                                            )

                            # -------------------------------------------------
                            # IGNORE ERRORS WHILE EXTRACTING LINKS
                            # -------------------------------------------------

                            except Exception:
                                pass

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------

    yield {
        "type": "done",
        "broken_links": broken_links
    }
