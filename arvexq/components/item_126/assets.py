"""Load unchanged existing UI assets through their allocated box."""
from arvexq.components.item_195.assets import read_asset

def read_prediction():
    return read_asset('forecast/prediction.js')

def read_marks():
    return read_asset('forecast/marks.js')
