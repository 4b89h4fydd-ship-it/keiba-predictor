"""Forward the existing audit invocation once; never start a new test runner."""

def audit(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
