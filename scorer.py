from utils import is_valid

def parse_last5(last5):
    if not isinstance(last5, str):
        return []
    return [int(ch) for ch in last5 if ch.isdigit()]

def confidence_label(score, margin=None):
    if margin is not None:
        if margin < 5:
            if score >= 70:
                return "⚠️ Good dog, tight race"
            return "🧊 Low"
        if margin >= 20 and score >= 70:
            return "🔥 Dominant"
        if margin >= 10 and score >= 65:
            return "✅ Strong"
        if margin >= 5 and score >= 55:
            return "✅ Playable"

    if score >= 75:
        return "🔥 Strong"
    if score >= 60:
        return "✅ Solid"
    if score >= 45:
        return "⚠️ Usable"
    return "🧊 Low"

def dominance_label(margin):
    if margin >= 20:
        return f"Dominant +{margin}"
    if margin >= 10:
        return f"Strong +{margin}"
    if margin >= 5:
        return f"Decent +{margin}"
    return f"Tight +{margin}"

def race_risk_label(score, margin, field_size):
    if score >= 70 and margin >= 10 and field_size <= 8:
        return "🟢 Clean race"
    if score >= 55 and margin >= 5:
        return "🟡 Competitive but playable"
    return "🔴 Messy / low confidence"

def suggested_bet_type(score, margin):
    if score >= 75 and margin >= 15:
        return "Win / Place"
    if score >= 60 and margin >= 8:
        return "Place / Top 2 style"
    if score >= 45:
        return "Tiny place only"
    return "Skip unless tiny API-keeper bet"

def score_runner(runner, field):
    score = 0
    pros = []
    warnings = []

    if runner.get("scratched") is True or runner.get("isLateScratching") is True:
        return 0, [], ["Scratched"]

    rating = runner.get("rating")
    if is_valid(rating) and rating > 0:
        score += min(20, float(rating) / 5)
        pros.append(f"Rating {rating}")

    avg_speed = runner.get("averageSpeed")
    field_speeds = [
        r.get("averageSpeed") for r in field
        if is_valid(r.get("averageSpeed")) and r.get("averageSpeed") > 0
    ]
    if is_valid(avg_speed) and avg_speed > 0 and field_speeds:
        best_speed = max(field_speeds)
        if avg_speed == best_speed:
            score += 20
            pros.append("Best average speed")
        else:
            score += max(0, 15 * (avg_speed / best_speed))

    best_finish_td = runner.get("bestFinishTrackAndDistance")
    if is_valid(best_finish_td):
        try:
            best_finish_td = int(best_finish_td)
            if best_finish_td == 1:
                score += 15
                pros.append("Won track/distance")
            elif best_finish_td <= 3:
                score += 10
                pros.append("Placed track/distance")
        except Exception:
            pass

    last5 = parse_last5(runner.get("last5"))
    if last5:
        top3 = sum(1 for pos in last5 if pos <= 3)
        wins = sum(1 for pos in last5 if pos == 1)
        score += top3 * 4
        score += wins * 3
        if top3 >= 4:
            pros.append("Very consistent last 5")
        elif top3 >= 3:
            pros.append("Good recent form")
        elif wins >= 1:
            pros.append("Recent winner")
    else:
        score -= 5
        warnings.append("Limited last-5 form")

    box = runner.get("boxNumber") or runner.get("rugNumber")
    try:
        box = int(box)
        if box in [1, 2]:
            score += 12
            pros.append("Good inside box")
        elif box in [3, 4]:
            score += 7
        elif box in [5, 6]:
            score += 3
        elif box in [7, 8]:
            score += 4
    except Exception:
        warnings.append("No box data")

    total_form_count = runner.get("totalFormCount")
    if is_valid(total_form_count):
        try:
            total_form_count = int(total_form_count)
            if total_form_count == 0:
                score -= 8
                warnings.append("No exposed form")
            elif total_form_count >= 10:
                score += 8
                pros.append("Experienced runner")
            elif total_form_count >= 5:
                score += 5
        except Exception:
            pass

    start_price = runner.get("startPrice")
    if is_valid(start_price):
        try:
            start_price = float(start_price)
            if start_price > 1:
                if start_price <= 2.5:
                    score += 15
                    pros.append("Market liked recently")
                elif start_price <= 5:
                    score += 8
        except Exception:
            pass

    score = round(max(0, min(score, 100)), 1)
    if not pros:
        pros.append("Top ranked by available data")
    return score, pros[:5], warnings[:4]
