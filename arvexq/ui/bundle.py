"""Deterministic app assembly shared by FastAPI and the static PWA builder."""
from arvexq.components.item_068.ui_route_asset import read_route_script as _read_route_068
from arvexq.components.item_125.ui_route_asset import read_route_script as _read_route_125
from arvexq.components.item_130.ui_route_asset import read_route_script as _read_route_130
from arvexq.components.item_131.ui_route_asset import read_route_script as _read_route_131
from arvexq.components.item_132.ui_route_asset import read_route_script as _read_route_132
from arvexq.components.item_133.ui_route_asset import read_route_script as _read_route_133
from arvexq.components.item_136.ui_route_asset import read_route_script as _read_route_136
from arvexq.components.item_138.ui_route_asset import read_route_script as _read_route_138
from arvexq.components.item_147.ui_route_asset import read_route_script as _read_route_147
from arvexq.components.item_176.ui_route_asset import read_route_script as _read_route_176
from arvexq.components.item_177.ui_route_asset import read_route_script as _read_route_177
from arvexq.components.item_178.ui_route_asset import read_route_script as _read_route_178
from arvexq.components.item_179.ui_route_asset import read_route_script as _read_route_179
from arvexq.components.item_180.ui_route_asset import read_route_script as _read_route_180
from arvexq.components.item_181.ui_route_asset import read_route_script as _read_route_181
from arvexq.components.item_183.ui_route_asset import read_route_script as _read_route_183
from arvexq.components.item_184.ui_route_asset import read_route_script as _read_route_184
from arvexq.components.item_188.ui_route_asset import read_route_script as _read_route_188
from arvexq.components.item_189.ui_route_asset import read_route_script as _read_route_189
from arvexq.components.item_190.ui_route_asset import read_route_script as _read_route_190
from arvexq.components.item_191.ui_route_asset import read_route_script as _read_route_191
from arvexq.components.item_192.ui_route_asset import read_route_script as _read_route_192
from arvexq.components.item_194.ui_route_asset import read_route_script as _read_route_194
from arvexq.components.item_055.assets import read_history_deduplicate
from arvexq.components.item_058.assets import read_history_temporal
from arvexq.components.item_182.assets import read_history_view
from arvexq.components.item_126.assets import read_prediction, read_marks
from arvexq.components.item_121.assets import read_tickets
from arvexq.components.item_185.assets import read_prediction_frame
from arvexq.components.item_186.assets import read_mark_frame
from arvexq.components.item_187.assets import read_ticket_frame
from arvexq.components.item_195.assets import read_asset

HISTORY_SCRIPTS = ('deduplicate', 'temporal', 'view')
FORECAST_SCRIPTS = ('prediction', 'marks', 'tickets', 'prediction_frame', 'mark_frame', 'ticket_frame')

def compose_app_script(main_script):
    return ('\n'.join(reader() for reader in (_read_route_068, _read_route_125, _read_route_130, _read_route_131, _read_route_132, _read_route_133, _read_route_136, _read_route_138, _read_route_147, _read_route_176, _read_route_177, _read_route_178, _read_route_179, _read_route_180, _read_route_181, _read_route_183, _read_route_184, _read_route_188, _read_route_189, _read_route_190, _read_route_191, _read_route_192, _read_route_194))+'\n'+'\n'.join(reader() for reader in (read_history_deduplicate, read_history_temporal, read_history_view))+'\n'+
            '\n'.join(reader() for reader in (read_prediction, read_marks, read_tickets, read_prediction_frame, read_mark_frame, read_ticket_frame))+'\n'+main_script)
