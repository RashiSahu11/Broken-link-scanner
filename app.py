# ---------------------------------------------------------
# 1. IMPORT REQUIRED LIBRARIES
# ---------------------------------------------------------

# Streamlit is used to create the web application interface.
import streamlit as st

# Pandas is used to convert the broken links list
# into a DataFrame (table) and export it as a CSV file.
import pandas as pd

# Import the crawl_website function from our crawler.py file.
# This function scans the website and finds broken links.
from Crawler import crawl_website

# urllib.parse is used to validate and analyze URLs.
import urllib.parse

# time is imported but is not used in this code.
import time


# ---------------------------------------------------------
# 2. CONFIGURE THE STREAMLIT PAGE
# ---------------------------------------------------------

# set_page_config() defines the basic settings of the webpage.
st.set_page_config(
    page_title="Broken Link Scanner",  # Browser tab title
    page_icon="🔗",                    # Browser tab icon
    layout="wide"                      # Use full page width
)


# ---------------------------------------------------------
# 3. ADD CUSTOM CSS STYLING
# ---------------------------------------------------------

# st.markdown() displays Markdown and HTML content.
# unsafe_allow_html=True allows us to apply custom HTML and CSS.

st.markdown("""
<style>

    /* Set the background color of the entire application */
    .stApp {
        background-color: #f8f9fa;
    }

    /* Style the main heading */
    .main-header {
        font-family: 'Inter', sans-serif;
        color: #1e3a8a;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    /* Style the subtitle below the main heading */
    .sub-header {
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Design for the metric cards */
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;

        /* Add a soft shadow around the card */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
                    0 2px 4px -1px rgba(0, 0, 0, 0.06);

        text-align: center;

        /* Blue line at the top of the card */
        border-top: 4px solid #3b82f6;
    }

    /* Style the large number inside each metric card */
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #0f172a;
    }

    /* Style the label below the number */
    .metric-label {
        font-size: 1rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Change the top border color for broken links card */
    .broken-metric {
        border-top-color: #ef4444;
    }

</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 4. DISPLAY THE MAIN HEADING AND SUBTITLE
# ---------------------------------------------------------

# Display the main heading using custom CSS.
st.markdown(
    '<h1 class="main-header">'
    '🔗 Broken Link Intelligence Scanner'
    '</h1>',
    unsafe_allow_html=True
)

# Display a short description of the application.
st.markdown(
    '<p class="sub-header">'
    'Crawl your website to identify and report broken links instantly.'
    '</p>',
    unsafe_allow_html=True
)


# ---------------------------------------------------------
# 5. CREATE THE SIDEBAR FOR USER CONFIGURATION
# ---------------------------------------------------------

# Everything inside st.sidebar appears in the left sidebar.
with st.sidebar:

    # Sidebar heading
    st.header("⚙️ Configuration")

    # Input field where the user enters the website URL.
    # The entered value is stored in target_url.
    target_url = st.text_input(
        "Target URL",
        placeholder="https://example.com"
    )

    # Display a subheading for basic crawling settings.
    st.subheader("Crawl Settings")

    # Slider to select how many levels deep the crawler
    # should explore from the starting webpage.
    #
    # min_value = smallest allowed value
    # max_value = largest allowed value
    # value = default selected value
    max_depth = st.slider(
        "Max Crawl Depth",
        min_value=1,
        max_value=5,
        value=2,
        help="How many clicks deep to crawl from the start URL."
    )

    # Number input to set the maximum number of pages
    # that the crawler is allowed to scan.
    max_pages = st.number_input(
        "Max Pages to Scan",
        min_value=10,
        max_value=1000,
        value=100,
        step=50,
        help="Limit the total number of pages to avoid endless crawling."
    )

    # Display a subheading for advanced settings.
    st.subheader("Advanced")

    # Slider to select how many threads should check URLs
    # simultaneously.
    #
    # More threads can make the scan faster,
    # but they can also increase server load.
    max_threads = st.slider(
        "Concurrent Threads",
        min_value=1,
        max_value=20,
        value=10,
        help="More threads = faster crawl, but higher load on the target server."
    )

    # Checkbox to decide whether crawling should continue
    # only within the original website's domain.
    #
    # Checked by default.
    same_domain_only = st.checkbox(
        "Stay on Same Domain",
        value=True,
        help="If checked, only extracts links from pages on the original domain (external links are still checked for status)."
    )

    # Create the button that starts the scanning process.
    #
    # When clicked, its value becomes True for that run.
    start_button = st.button(
        "🚀 Start Scan",
        use_container_width=True,
        type="primary"
    )


# ---------------------------------------------------------
# 6. START SCANNING WHEN THE BUTTON IS CLICKED
# ---------------------------------------------------------

# The scanning process runs only when the user clicks
# the Start Scan button.
if start_button:

    # -----------------------------------------------------
    # 6.1 VALIDATE THE USER'S INPUT
    # -----------------------------------------------------

    # Check whether the user has entered a URL.
    if not target_url:

        # Display an error message if the input is empty.
        st.error("Please enter a Target URL to begin.")

    # Check whether the URL contains a scheme,
    # such as http:// or https://.
    #
    # urlparse() breaks the URL into parts.
    # .scheme gives us the protocol.
    elif not urllib.parse.urlparse(target_url).scheme:

        # Display an error if the scheme is missing.
        st.error(
            "Please enter a valid URL with a scheme "
            "(e.g., http:// or https://)."
        )

    else:

        # -------------------------------------------------
        # 6.2 DISPLAY SCAN START MESSAGE
        # -------------------------------------------------

        # Inform the user that scanning is beginning.
        st.info(
            f"Initiating scan for **{target_url}**..."
        )


        # -------------------------------------------------
        # 6.3 CREATE PROGRESS AND STATUS ELEMENTS
        # -------------------------------------------------

        # Create a progress bar.
        # Initially, its value is 0%.
        progress_bar = st.progress(0)

        # Create an empty placeholder.
        # We can update this later with the current status.
        status_text = st.empty()


        # -------------------------------------------------
        # 6.4 CREATE TWO COLUMNS FOR METRIC CARDS
        # -------------------------------------------------

        # Divide the available page width into two columns.
        col1, col2 = st.columns(2)

        # Create an empty placeholder inside the first column.
        # It will display the number of pages scanned.
        with col1:
            crawled_metric = st.empty()

        # Create an empty placeholder inside the second column.
        # It will display the number of broken links.
        with col2:
            broken_metric = st.empty()


        # -------------------------------------------------
        # 7. DEFINE FUNCTION TO UPDATE METRIC CARDS
        # -------------------------------------------------

        # This function updates the two metric cards
        # whenever new crawling progress is received.
        #
        # crawled = number of URLs processed
        # broken = number of broken links found
        def update_metrics(crawled, broken):

            # ---------------------------------------------
            # UPDATE THE PAGES SCANNED CARD
            # ---------------------------------------------

            # Display the number of scanned pages
            # inside a styled HTML card.
            crawled_metric.markdown(f"""
                <div class="metric-card">

                    <!-- Display the scanned page count -->
                    <div class="metric-value">{crawled}</div>

                    <!-- Display the card label -->
                    <div class="metric-label">Pages Scanned</div>

                </div>
            """, unsafe_allow_html=True)


            # ---------------------------------------------
            # UPDATE THE BROKEN LINKS CARD
            # ---------------------------------------------

            # Display the number of broken links
            # inside a card with a red top border.
            broken_metric.markdown(f"""
                <div class="metric-card broken-metric">

                    <!-- Display the broken link count -->
                    <div class="metric-value">{broken}</div>

                    <!-- Display the card label -->
                    <div class="metric-label">Broken Links</div>

                </div>
            """, unsafe_allow_html=True)


        # -------------------------------------------------
        # 8. INITIALIZE METRIC CARDS
        # -------------------------------------------------

        # Before scanning starts, both values are zero.
        update_metrics(0, 0)


        # -------------------------------------------------
        # 9. RUN THE WEBSITE CRAWLER
        # -------------------------------------------------

        # try-except handles unexpected errors
        # so the application can show an error message
        # instead of crashing.
        try:

            # Call crawl_website() from crawler.py.
            #
            # We pass the settings selected by the user.
            #
            # crawl_website() is a generator that provides
            # progress updates and a final result.
            crawler_generator = crawl_website(

                # Website entered by the user
                start_url=target_url,

                # Maximum crawling depth
                max_depth=max_depth,

                # Maximum number of URLs to scan
                max_pages=max_pages,

                # Whether to stay on the same domain
                same_domain_only=same_domain_only,

                # Number of concurrent threads
                max_threads=max_threads
            )


            # This list will store the final broken links.
            # Initially, it is empty.
            final_results = []


            # -------------------------------------------------
            # 10. PROCESS UPDATES FROM THE CRAWLER
            # -------------------------------------------------

            # Loop through every update produced
            # by the crawl_website() generator.
            for update in crawler_generator:


                # -------------------------------------------------
                # 10.1 HANDLE PROGRESS UPDATES
                # -------------------------------------------------

                # Check whether the current update is
                # a progress update.
                if update["type"] == "progress":

                    # Extract the number of URLs scanned.
                    crawled = update["crawled"]

                    # Extract the number of broken links found.
                    broken = update["broken_count"]

                    # Extract the URL currently being processed.
                    current = update["current_url"]


                    # -------------------------------------------------
                    # 10.2 CALCULATE PROGRESS PERCENTAGE
                    # -------------------------------------------------

                    # Divide the number of scanned URLs
                    # by the maximum page limit.
                    #
                    # Example:
                    # crawled = 50
                    # max_pages = 100
                    # progress = 0.5 (50%)
                    #
                    # min() ensures the value never exceeds 1.0.
                    #
                    # Note: This is an estimate. The crawler
                    # may finish before reaching max_pages.
                    progress = min(
                        crawled / max_pages,
                        1.0
                    )

                    # Update the progress bar.
                    # It accepts a value between 0.0 and 1.0.
                    progress_bar.progress(progress)


                    # -------------------------------------------------
                    # 10.3 FORMAT THE CURRENT URL
                    # -------------------------------------------------

                    # Long URLs can take up too much space.
                    #
                    # If the URL is longer than 60 characters,
                    # show only the first 57 characters
                    # followed by three dots.
                    display_url = (
                        current
                        if len(current) < 60
                        else current[:57] + "..."
                    )

                    # Display the URL currently being scanned.
                    status_text.text(
                        f"Scanning: {display_url}"
                    )


                    # -------------------------------------------------
                    # 10.4 REFRESH METRIC CARDS
                    # -------------------------------------------------

                    # Update the scanned pages and
                    # broken links cards with new values.
                    update_metrics(
                        crawled,
                        broken
                    )


                # -------------------------------------------------
                # 10.5 HANDLE FINAL RESULTS
                # -------------------------------------------------

                # Check whether crawling has finished.
                elif update["type"] == "done":

                    # Extract the complete list of broken links.
                    final_results = update["broken_links"]

                    # Set the progress bar to 100%.
                    progress_bar.progress(1.0)

                    # Display a success message.
                    status_text.success(
                        "Scan Completed!"
                    )


            # -------------------------------------------------
            # 11. DISPLAY THE BROKEN LINKS REPORT
            # -------------------------------------------------

            # Check whether any broken links were found.
            if final_results:

                # Display a heading with the total
                # number of broken links found.
                st.subheader(
                    f"⚠️ Found {len(final_results)} broken links"
                )


                # -------------------------------------------------
                # 11.1 CONVERT RESULTS INTO A DATAFRAME
                # -------------------------------------------------

                # Convert the list of dictionaries
                # into a Pandas DataFrame.
                #
                # Each dictionary becomes a row.
                # Dictionary keys become column names.
                df = pd.DataFrame(final_results)


                # -------------------------------------------------
                # 11.2 DISPLAY INTERACTIVE DATAFRAME
                # -------------------------------------------------

                # Show the report as a table.
                #
                # use_container_width=True:
                # Table uses the available page width.
                #
                # hide_index=True:
                # Hide the default row numbers.
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )


                # -------------------------------------------------
                # 12. PREPARE CSV REPORT FOR DOWNLOAD
                # -------------------------------------------------

                # Convert the DataFrame into CSV format.
                #
                # index=False:
                # Don't include the DataFrame row index.
                #
                # encode('utf-8'):
                # Convert the CSV text into bytes,
                # which can be provided to the download button.
                csv = df.to_csv(
                    index=False
                ).encode('utf-8')


                # -------------------------------------------------
                # 12.1 CREATE DOWNLOAD BUTTON
                # -------------------------------------------------

                # Allow the user to download the broken
                # links report as a CSV file.
                st.download_button(

                    # Text displayed on the button
                    label="📥 Download Report as CSV",

                    # CSV file content
                    data=csv,

                    # Name of the downloaded file
                    file_name="broken_links_report.csv",

                    # Tell the browser the file type
                    mime="text/csv",

                    # Display the button using primary styling
                    type="primary"
                )


            # -------------------------------------------------
            # 13. HANDLE CASE WHEN NO BROKEN LINKS ARE FOUND
            # -------------------------------------------------

            else:

                # Display a success message when
                # the crawler finds no broken links.
                st.success(
                    "🎉 Great job! No broken links found."
                )

                # Display balloon animation for celebration.
                st.balloons()


        # -----------------------------------------------------
        # 14. HANDLE ERRORS DURING THE SCAN
        # -----------------------------------------------------

        except Exception as e:

            # If an unexpected error occurs,
            # display its details in the application.
            st.error(
                f"An error occurred during the scan: {e}"
            )


# ---------------------------------------------------------
# 15. INITIAL SCREEN BEFORE SCANNING
# ---------------------------------------------------------

# This block runs when the Start Scan button
# has not been clicked.
else:

    # Ask the user to configure the settings
    # from the sidebar and start scanning.
    st.info(
        "👈 Configure the settings in the sidebar "
        "and click **Start Scan** to begin."
    )
