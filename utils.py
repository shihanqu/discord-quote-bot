# utils.py
from fuzzywuzzy import fuzz

def fuzzy_search(query, items, key=None, scorer=fuzz.ratio, threshold=60):
    """
    Performs a fuzzy search on a list of items.

    Args:
        query: The search string.
        items: A list of items to search through.
        key: An optional function to extract the string to compare against from each item.
        scorer: The fuzzywuzzy scorer function to use (default: fuzz.ratio).
        threshold: The minimum score to consider a match (0-100).

    Returns:
        A list of tuples, where each tuple contains a matching item and its score.
    """
    results = []
    for item in items:
        value = key(item) if key else item
        score = scorer(query.lower(), value.lower())
        if score >= threshold:
            results.append((item, score))
    return sorted(results, key=lambda x: x[1], reverse=True) # Sort by score (descending)
