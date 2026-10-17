"""#18 Count actual race-card starters without a fabricated declared field."""
def extract(horses):
    return len([h for h in horses if isinstance(h,dict) and int(h.get("horseNumber") or 0)>0])
