IGNORE_KEYWORDS = [
    "fell",
    "checked",
    "severely checked",
    "badly checked",
    "hampered",
    "bumped",
    "injured",
    "injury",
    "eased",
    "vetted",
    "lost ground",
    "stumbled",
    "slow away",
    "missed start",
    "collision",
]


def is_clean_race(comment):
    """
    Returns True if the race is suitable for learning.
    """

    if not comment:
        return True

    comment = comment.lower()

    for word in IGNORE_KEYWORDS:
        if word in comment:
            return False

    return True
