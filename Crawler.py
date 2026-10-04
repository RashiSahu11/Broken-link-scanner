# ---------------------------------------------------------
# IMPORTING REQUIRED LIBRARIES
# ---------------------------------------------------------
# requests is used to send HTTP requests to websites
# Example: GET request, HEAD request etc.
import requests
# BeautifulSoup is used to read and extract information
# from HTML pages
from bs4 import BeautifulSoup
# urljoin -> combines a base URL with a relative URL
# urlparse -> breaks a URL into different parts
from urllib.parse import urljoin, urlparse
# concurrent.futures is used for multithreading.
# It allows us to check multiple URLs at the same time.
import concurrent.futures
# time is imported but is not actually used in this code.
# It can be removed if not required.
import time

# ---------------------------------------------------------
# FUNCTION 1: CHECK WHETHER A URL IS VALID
# ---------------------------------------------------------
def is_valid_url(url):
    """
    This function checks whether the given URL
    is a proper/complete URL.
    Example of valid URL:
    https://example.com
    Example of invalid URL:
    hello
    /about
    """

    # urlparse() breaks the URL into different components
    parsed = urlparse(url)

    # netloc means the domain name
    # scheme means http/https

    # Both should exist for a complete URL.

    # bool() converts the value into True or False.
    return bool(parsed.netloc) and bool(parsed.scheme)


# ---------------------------------------------------------
# FUNCTION 2: CHECK WHETHER A LINK IS WORKING OR BROKEN
# ---------------------------------------------------------
def check_link(url, timeout=5):
    """
    Checks whether a URL is working or broken.
    Returns:
    (status_code, error)
    Example of working URL:
    (200, None)
    Example of broken URL:
    (404, "HTTP Error 404")
    timeout=5 means we wait maximum around 5 seconds
    for the website response.
    """

    # try is used because network requests can fail.
    # We don't want the entire program to crash
    # because one URL has a problem.
    try:
        # User-Agent tells the website that the request
        # is coming from a browser-like client.
        headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36'
        }

        # -------------------------------------------------
        # FIRST TRY A HEAD REQUEST
        # -------------------------------------------------

        # HEAD request checks the response information
        # without downloading the complete webpage.

        # This is generally faster than GET.
        response = requests.head(
            url,
            headers=headers,
            # If the website redirects the request,
            # automatically follow the redirect.
            allow_redirects=True,
            # Don't wait forever for the website.
            timeout=timeout
        )

        # -------------------------------------------------
        # IF HEAD REQUEST DOES NOT WORK PROPERLY
        # -------------------------------------------------

        # Some websites don't allow HEAD requests.

        # Common problematic status codes here:
        #
        # 400 -> Bad Request
        # 403 -> Forbidden
        # 404 -> Not Found
        # 405 -> Method Not Allowed

        # In these cases, we try a GET request instead.
        if response.status_code in [404, 405, 400, 403]:
            # Send a GET request as a fallback.
            response = requests.get(
                url,
                headers=headers,
                allow_redirects=True,
                timeout=timeout,
                # stream=True means don't immediately
                # download the complete response body.
                stream=True
            )

            # We only needed the response status,
            # so close the connection immediately.
            response.close()

        # -------------------------------------------------
        # CHECK HTTP STATUS CODE
        # -------------------------------------------------

        # HTTP status codes >= 400 generally represent
        # client/server errors.

        # Examples:
        # 404 -> Page not found
        # 403 -> Forbidden
        # 500 -> Server error
        if response.status_code >= 400:
            # Return status code and error message
            return (
                response.status_code,
                f"HTTP Error {response.status_code}"
            )

        # If status code is below 400,
        # we consider the link working.

        # Example:
        # 200 -> Success
        # 301 -> Redirect
        # 302 -> Redirect

        # None means there is no error.
        return response.status_code, None

    # -----------------------------------------------------
    # HANDLE TIMEOUT ERROR
    # -----------------------------------------------------
    except requests.exceptions.Timeout:
        # Website didn't respond within the timeout period.
        return None, "Request Timed Out"

    # -----------------------------------------------------
    # HANDLE TOO MANY REDIRECTS
    # -----------------------------------------------------
    except requests.exceptions.TooManyRedirects:
        # Example:
        # A -> B -> C -> A -> B -> C ...
        #
        # The website keeps redirecting.
        return None, "Too Many Redirects"

    # -----------------------------------------------------
    # HANDLE OTHER REQUEST/NETWORK ERRORS
    # -----------------------------------------------------
    except requests.exceptions.RequestException as e:
        # This can handle other network-related errors.
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
            Example:
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

    # Example:
    #
    # start_url:
    # https://example.com
    #
    # domain:
    # example.com
    domain = urlparse(start_url).netloc

    # -----------------------------------------------------
    # SET OF ALREADY VISITED URLS
    # -----------------------------------------------------

    # A set is used because checking whether an item
    # already exists in a set is very fast.
    #
    # It prevents the crawler from checking
    # the same URL again and again.
    visited = set()

    # -----------------------------------------------------
    # URL QUEUE
    # -----------------------------------------------------

    # Each item contains:
    #
    # 1. URL
    # 2. Depth
    # 3. Source page
    #
    # Initially we only have the starting URL.
    #
    # Example:
    # [
    # (
    # "https://example.com",
    # 0,
    # "https://example.com"
    # )
    # ]
    to_visit = [
        (start_url, 0, start_url)
    ]

    # -----------------------------------------------------
    # STORE ALL BROKEN LINKS
    # -----------------------------------------------------

    # Whenever we find a broken URL,
    # we will store its information here.
    broken_links = []

    # -----------------------------------------------------
    # COUNT HOW MANY PAGES/URLS WE HAVE PROCESSED
    # -----------------------------------------------------
    pages_crawled = 0

    # -----------------------------------------------------
    # CREATE THREAD POOL
    # -----------------------------------------------------

    # ThreadPoolExecutor allows multiple URLs
    # to be checked simultaneously.
    #
    # If max_threads = 10,
    # up to 10 URL checks can run at the same time.
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max_threads
    ) as executor:

        # -------------------------------------------------
        # MAIN CRAWLING LOOP
        # -------------------------------------------------

        # Continue while:
        #
        # 1. There are URLs waiting to be checked
        # AND
        # 2. We haven't reached max_pages
        while to_visit and pages_crawled < max_pages:

            # -------------------------------------------------
            # CREATE CURRENT BATCH
            # -------------------------------------------------

            # Copy the current URLs into current_batch.
            #
            # Then clear to_visit because newly discovered
            # URLs will be added there for the next batch.
            current_batch = to_visit.copy()
            to_visit.clear()

            # -------------------------------------------------
            # STORE FUTURE -> URL INFORMATION
            # -------------------------------------------------

            # When using multiple threads, URLs may finish
            # in any order.
            #
            # This dictionary helps us remember:
            #
            # Future -> (URL, depth, source page)
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

                # -------------------------------------------------
                # RUN check_link() IN A BACKGROUND THREAD
                # -------------------------------------------------

                # Instead of directly doing:
                #
                # check_link(url)
                #
                # we submit it to a worker.
                #
                # This allows multiple URLs to be checked
                # simultaneously.
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

            # as_completed() gives us the futures
            # in the order in which they finish.
            #
            # It does NOT necessarily follow the original order.
            for future in concurrent.futures.as_completed(
                future_to_url
            ):

                # Get the URL, depth and source page
                # associated with this future.
                url, depth, source = future_to_url[future]

                # -------------------------------------------------
                # GET RESULT FROM check_link()
                # -------------------------------------------------
                try:
                    # future.result() gives us the result
                    # returned by check_link().
                    #
                    # Example:
                    # status_code = 200
                    # error = None
                    status_code, error = future.result()

                except Exception as exc:
                    # If something unexpected happens,
                    # store the exception as an error.
                    status_code, error = None, str(exc)

                # -------------------------------------------------
                # SEND LIVE PROGRESS UPDATE
                # -------------------------------------------------

                # Because this function uses yield,
                # another part of the application
                # (for example Streamlit) can display
                # this information live.
                yield {
                    "type": "progress",
                    # Number of URLs visited so far.
                    "crawled": len(visited),
                    # Number of broken URLs found so far.
                    "broken_count": len(broken_links),
                    # URL currently being processed.
                    "current_url": url
                }

                # -------------------------------------------------
                # IF URL IS BROKEN
                # -------------------------------------------------
                if error:
                    # Store all useful information
                    # about the broken URL.
                    broken_links.append({
                        # The broken URL itself.
                        "Broken URL": url,
                        # The page where this broken URL
                        # was found.
                        "Source Page": source,
                        # HTTP status code.
                        #
                        # If status_code is None,
                        # display "N/A".
                        "Status Code":
                            status_code
                            if status_code
                            else "N/A",
                        # Error reason.
                        "Error": error
                    })

                # -------------------------------------------------
                # IF URL IS WORKING
                # -------------------------------------------------
                else:

                    # -------------------------------------------------
                    # CHECK WHETHER WE SHOULD GO DEEPER
                    # -------------------------------------------------

                    # Example:
                    #
                    # max_depth = 2
                    #
                    # Depth 0 -> Home
                    # Depth 1 -> Links from Home
                    # Depth 2 -> Links from Depth 1
                    #
                    # After depth 2, don't continue crawling.
                    if depth < max_depth:

                        # -------------------------------------------------
                        # CHECK DOMAIN
                        # -------------------------------------------------

                        # If same_domain_only = True,
                        # only crawl pages belonging to
                        # the same domain.
                        #
                        # Example:
                        #
                        # Main website:
                        # example.com
                        #
                        # Same domain:
                        # example.com/about -> YES
                        #
                        # Different domain:
                        # youtube.com -> NO
                        if (
                            not same_domain_only
                            or urlparse(url).netloc == domain
                        ):

                            try:

                                # -------------------------------------------------
                                # DOWNLOAD THE CURRENT WEBPAGE
                                # -------------------------------------------------

                                # We need the HTML because we want
                                # to find more links inside it.
                                headers = {
                                    'User-Agent': 'Mozilla/5.0'
                                }

                                res = requests.get(
                                    url,
                                    headers=headers,
                                    timeout=5
                                )

                                # -------------------------------------------------
                                # CHECK WHETHER RESPONSE IS HTML
                                # -------------------------------------------------

                                # We only want to extract links
                                # from HTML pages.
                                #
                                # For example:
                                #
                                # text/html -> process
                                # image/png -> don't process
                                # application/pdf -> don't process
                                if "text/html" in res.headers.get(
                                    "Content-Type",
                                    ""
                                ):

                                    # -------------------------------------------------
                                    # PARSE HTML USING BEAUTIFULSOUP
                                    # -------------------------------------------------

                                    # res.text contains the HTML code.
                                    #
                                    # BeautifulSoup converts it into
                                    # a structure that we can search.
                                    soup = BeautifulSoup(
                                        res.text,
                                        "html.parser"
                                    )

                                    # -------------------------------------------------
                                    # FIND ALL ANCHOR TAGS
                                    # -------------------------------------------------

                                    # We search for:
                                    #
                                    # <a href="...">
                                    #
                                    # href=True means we only want
                                    # anchor tags that contain an href.
                                    for a_tag in soup.find_all(
                                        "a",
                                        href=True
                                    ):

                                        # -------------------------------------------------
                                        # GET href VALUE
                                        # -------------------------------------------------

                                        # Example:
                                        #
                                        # <a href="/about">
                                        #
                                        # href will be:
                                        #
                                        # /about
                                        href = a_tag["href"]

                                        # -------------------------------------------------
                                        # CONVERT RELATIVE URL TO FULL URL
                                        # -------------------------------------------------

                                        # Example:
                                        #
                                        # Current page:
                                        # https://example.com
                                        #
                                        # href:
                                        # /about
                                        #
                                        # Result:
                                        # https://example.com/about
                                        next_url = urljoin(
                                            url,
                                            href
                                        )

                                        # -------------------------------------------------
                                        # REMOVE URL FRAGMENT
                                        # -------------------------------------------------

                                        # Example:
                                        #
                                        # https://example.com/about#team
                                        #
                                        # becomes:
                                        #
                                        # https://example.com/about
                                        #
                                        # This prevents the crawler from
                                        # treating each fragment as a
                                        # completely different URL.
                                        next_url = urlparse(
                                            next_url
                                        )._replace(
                                            fragment=""
                                        ).geturl()

                                        # -------------------------------------------------
                                        # CHECK URL
                                        # -------------------------------------------------

                                        # Two conditions must be true:
                                        #
                                        # 1. It must be a valid URL.
                                        # 2. We haven't visited it already.
                                        if (
                                            is_valid_url(next_url)
                                            and next_url not in visited
                                        ):

                                            # -------------------------------------------------
                                            # ADD URL TO NEXT BATCH
                                            # -------------------------------------------------

                                            # depth + 1 means this URL
                                            # is one level deeper.
                                            #
                                            # We also store the current URL
                                            # as the source page.
                                            #
                                            # Example:
                                            #
                                            # Current page:
                                            # example.com/about
                                            #
                                            # Found link:
                                            # example.com/contact
                                            #
                                            # We store:
                                            #
                                            # (
                                            # example.com/contact,
                                            # depth + 1,
                                            # example.com/about
                                            # )
                                            to_visit.append(
                                                (
                                                    next_url,
                                                    depth + 1,
                                                    url
                                                )
                                            )

                            # ---------------------------------------------------------
                            # IGNORE ERRORS WHILE EXTRACTING LINKS
                            # ---------------------------------------------------------

                            # If we can't download or parse one page,
                            # don't stop the entire crawler.
                            except Exception:
                                # pass means:
                                # "Do nothing and continue."
                                pass

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------

    # Once there are no more URLs to process
    # OR max_pages has been reached,
    # crawling is complete.
    #
    # We send one final result.
    yield {
        "type": "done",
        # Return the complete list of broken links.
        "broken_links": broken_links
    }