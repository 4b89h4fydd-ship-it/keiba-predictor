"""Marks remain unapproved; never translate research ranks into product marks."""
def run(*, probabilities=None):
    return {"status":"not-validated", "marks":None}
