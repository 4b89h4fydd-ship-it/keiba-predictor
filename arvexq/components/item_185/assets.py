"""Load unchanged existing UI assets through their allocated box."""
from arvexq.components.item_195.assets import read_asset

def read_prediction_frame():
    return read_asset('forecast/prediction_frame.js')
