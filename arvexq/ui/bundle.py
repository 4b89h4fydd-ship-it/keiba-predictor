"""Deterministic app assembly shared by FastAPI and the static PWA builder."""
from arvexq.ui.assets import read_asset

FORECAST_SCRIPTS = ('prediction', 'marks', 'tickets', 'prediction_frame', 'mark_frame', 'ticket_frame')

def compose_app_script(main_script):
    return '\n'.join(read_asset('forecast/'+name+'.js') for name in FORECAST_SCRIPTS)+'\n'+main_script
