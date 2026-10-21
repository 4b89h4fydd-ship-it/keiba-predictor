"""Load unchanged existing UI assets through their allocated box."""
from arvexq.components.item_195.assets import read_asset

def read_history_view():
    return read_asset('history/view.js')
