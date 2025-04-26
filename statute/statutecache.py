from statute.statuteparser import StatuteParser

class StatuteCache:
    # Cache a set of html documents based on title and statute
    # Get the html document, construct a StatuteScraper
    #   I will need to lazily construct the formatted_data in the scraper object in the future (some re-reads might not work?)
    # Save the link itself / way of determining if we've cached this before
    # Decide on some kind of structure to house the statutes in (folder?) with their
    # link, title.section, datetime, html
    # JSON!

    #
    def __init__(self, cache_folder: str):
        ...
        # if the cache folder doesn't exist, create it

    def cache_statute(self, statute_link: str) -> StatuteParser:
        return StatuteParser("foo", "bar", [])
        # grab, cache the statute, return the parsed Statute

    def available_statutes(self):
        list[str]
        # read and list
