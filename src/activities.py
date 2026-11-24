"""Verified activity discovery; broad water listings do not imply kayaking."""
import re
from .nps_api import official_url

ACTIVITIES = ("Climbing", "Hiking", "Camping", "Kayaking")
PATTERNS = {"Climbing": r"\b(?:climb(?:ing|s)?|rock[- ]climbing|mountaineering)\b",
            "Hiking": r"\bhik(?:e|es|ing)\b", "Camping": r"\bcamp(?:ing|grounds?|sites?|s)?\b",
            "Kayaking": r"\bkayak(?:ing|s)?\b"}

def requested_activities(question):
    # Negated preferences must not become a positive activity requirement.
    return [name for name, pattern in PATTERNS.items() if re.search(pattern, question, re.I)
            and not re.search(r"\b(?:no|not|without|avoid|don't want|do not want)\s+(?:to\s+)?" + pattern, question, re.I)]

def enforce_activity_intent(plan, question, previous=None):
    activities = requested_activities(question)
    discovery = re.search(r"\b(?:where|which|recommend|suggest|good\s+(?:national\s+)?park|parks?\s+(?:that|with|for|has|have)|activities)\b", question, re.I)
    route_question = re.search(r"\b(?:trails?|moderate|strenuous|easy|distance|miles|elevation)\b", question, re.I)
    followup = previous and previous.get("intent") == "activities"
    if activities and ((discovery and not route_question) or (followup and not route_question) or plan["intent"] == "activities"):
        return {**plan, "intent": "activities", "activities": activities}
    return plan

def matching_parks(parks, profiles, activities, codes):
    result, coverage = [], []
    for park in parks.itertuples():
        if codes and park.park_code not in codes:
            continue
        profile = profiles.get(park.park_code, {})
        records = [a for a in profile.get("activities", []) if official_url(a.get("url"))]
        matches = []
        for activity in activities:
            found = []
            for item in records:
                label = item.get("source_label") or item.get("name", "")
                # A broad category alone cannot substantiate kayaking or climbing.
                target = label + " " + item.get("url", "")
                if activity == "Kayaking":
                    ok = bool(re.search(r"kayak", target, re.I))
                elif activity == "Climbing":
                    ok = bool(re.search(r"climb|mountaineer", target, re.I))
                else:
                    ok = item.get("name") == activity or bool(re.search(PATTERNS[activity], label, re.I))
                if ok:
                    found.append({"activity": activity, "label": label, "url": official_url(item["url"])})
            if found:
                matches.append(found[0])
        coverage.append({"park_code": park.park_code, "status": "matched" if len(matches) == len(activities) and activities else "unconfirmed" if records else "no_data"})
        if activities and len(matches) == len(activities):
            result.append({"park_code": park.park_code, "park_name": park.park_name,
                           "matches": matches, "source_url": official_url(profile.get("official_url")),
                           "checked_at": profile.get("checked_at"), "source_kind": profile.get("source_kind"),
                           "historical": None})
    return result, coverage
