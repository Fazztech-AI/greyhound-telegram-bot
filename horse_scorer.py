def score_horse(runner, field):
    """
    Horse scoring engine.
    Returns:
        score, pros, warnings
    """

    score = 50

    pros = []
    warnings = []

    #
    # Barrier
    #

    barrier = runner.get("barrier")

    try:
        barrier = int(barrier)

        if barrier <= 4:
            score += 6
            pros.append("Good barrier")

        elif barrier >= 12:
            score -= 4
            warnings.append("Wide barrier")

    except:
        pass

    #
    # Recent form
    #

    form = str(runner.get("form") or "")

    if "1" in form[:3]:
        score += 8
        pros.append("Recent win")

    elif form == "":
        warnings.append("No form")

    #
    # Weight
    #

    try:
        weight = float(runner.get("weight"))

        if weight <= 55:
            score += 3

        elif weight >= 60:
            score -= 5
            warnings.append("Big weight")

    except:
        pass

    #
    # Jockey
    #

    if runner.get("jockey"):
        score += 2

    #
    # Trainer
    #

    if runner.get("trainer"):
        score += 2

    score = max(0, min(100, score))

    return score, pros, warnings
