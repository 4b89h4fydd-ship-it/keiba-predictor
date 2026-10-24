"""Research-only replay over existing static snapshots and independently retrieved labels.

The current snapshots were archived after race dates: NOT a forward-validated
preoff prediction record. Labels are used strictly after all predictions, and
no outcome keys are ever passed to Stage64. Never use this as product accuracy.
"""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from collections import defaultdict
import warnings

from arvexq.research.stage64.pipeline import predict

ROOT = Path(__file__).resolve().parents[1]
LABELS = json.loads(r'''{"jra-2026-10-17-京都-01":[2,9,3],"jra-2026-10-17-京都-02":[7,6,1],"jra-2026-10-17-京都-03":[4,5,8],"jra-2026-10-17-京都-04":[5,2,1],"jra-2026-10-17-京都-05":[1,2,4],"jra-2026-10-17-京都-06":[4,10,8],"jra-2026-10-17-京都-07":[7,4,8],"jra-2026-10-17-京都-08":[7,3,6],"jra-2026-10-17-京都-09":[7,11,14],"jra-2026-10-17-京都-10":[6,2,7],"jra-2026-10-17-京都-11":[10,5,9],"jra-2026-10-17-京都-12":[5,7,10],"jra-2026-10-17-新潟-01":[9,2,7],"jra-2026-10-17-新潟-02":[7,11,1],"jra-2026-10-17-新潟-03":[2,5,1],"jra-2026-10-17-新潟-04":[7,11,10],"jra-2026-10-17-新潟-05":[11,3,15],"jra-2026-10-17-新潟-06":[11,15,2],"jra-2026-10-17-新潟-07":[6,4,7],"jra-2026-10-17-新潟-08":[2,4,13],"jra-2026-10-17-新潟-09":[3,9,1],"jra-2026-10-17-新潟-10":[10,6,3],"jra-2026-10-17-新潟-11":[6,12,15],"jra-2026-10-17-新潟-12":[16,14,8],"jra-2026-10-17-東京-01":[4,2,6],"jra-2026-10-17-東京-02":[4,9,8],"jra-2026-10-17-東京-03":[11,8,6],"jra-2026-10-17-東京-04":[5,17,15],"jra-2026-10-17-東京-05":[9,7,3],"jra-2026-10-17-東京-06":[13,17,7],"jra-2026-10-17-東京-07":[5,11,4],"jra-2026-10-17-東京-08":[6,4,3],"jra-2026-10-17-東京-09":[7,12,5],"jra-2026-10-17-東京-10":[4,10,14],"jra-2026-10-17-東京-11":[13,10,14],"jra-2026-10-17-東京-12":[2,7,5],"nar-2026-10-15-名古屋-01":[1,10,7],"nar-2026-10-15-名古屋-02":[11,4,2],"nar-2026-10-15-名古屋-03":[6,2,1],"nar-2026-10-15-名古屋-04":[9,6,3],"nar-2026-10-15-名古屋-05":[7,6,1],"nar-2026-10-15-名古屋-06":[2,1,3],"nar-2026-10-15-名古屋-07":[6,4,5],"nar-2026-10-15-名古屋-08":[6,8,9],"nar-2026-10-15-名古屋-09":[7,2,1],"nar-2026-10-15-名古屋-10":[6,3,4],"nar-2026-10-15-名古屋-11":[5,4,12],"nar-2026-10-15-名古屋-12":[6,7,11],"nar-2026-10-15-園田-01":[6,10,1],"nar-2026-10-15-園田-02":[8,7,3],"nar-2026-10-15-園田-03":[5,1,4],"nar-2026-10-15-園田-04":[4,2,8],"nar-2026-10-15-園田-05":[12,8,4],"nar-2026-10-15-園田-06":[4,5,9],"nar-2026-10-15-園田-07":[5,2,8],"nar-2026-10-15-園田-08":[4,9,5],"nar-2026-10-15-園田-09":[2,3,6],"nar-2026-10-15-園田-10":[9,3,8],"nar-2026-10-15-園田-11":[2,4,6],"nar-2026-10-15-園田-12":[7,3,6],"nar-2026-10-15-川崎-01":[7,8,3],"nar-2026-10-15-川崎-02":[6,2,8],"nar-2026-10-15-川崎-03":[9,8,7],"nar-2026-10-15-川崎-04":[4,6,2],"nar-2026-10-15-川崎-05":[11,10,7],"nar-2026-10-15-川崎-06":[7,13,1],"nar-2026-10-15-川崎-07":[7,2,3],"nar-2026-10-15-川崎-08":[8,2,1],"nar-2026-10-15-川崎-09":[3,12,2],"nar-2026-10-15-川崎-10":[5,10,6],"nar-2026-10-15-川崎-11":[2,7,6],"nar-2026-10-15-川崎-12":[14,1,9],"nar-2026-10-15-門別-01":[8,3,5],"nar-2026-10-15-門別-02":[6,4,7],"nar-2026-10-15-門別-03":[11,3,7],"nar-2026-10-15-門別-04":[8,1,3],"nar-2026-10-15-門別-05":[1,4,3],"nar-2026-10-15-門別-06":[4,7,5],"nar-2026-10-15-門別-07":[10,2,7],"nar-2026-10-15-門別-08":[4,7,2],"nar-2026-10-15-門別-09":[4,10,8],"nar-2026-10-15-門別-10":[9,2,1],"nar-2026-10-15-門別-11":[5,7,3],"nar-2026-10-15-門別-12":[7,9,8],"nar-2026-10-17-佐賀-01":[5,4,6],"nar-2026-10-17-佐賀-02":[1,8,6],"nar-2026-10-17-佐賀-03":[7,2,1],"nar-2026-10-17-佐賀-04":[6,4,7],"nar-2026-10-17-佐賀-05":[13,5,12],"nar-2026-10-17-佐賀-06":[1,5,7],"nar-2026-10-17-佐賀-07":[8,1,3],"nar-2026-10-17-佐賀-08":[1,6,8],"nar-2026-10-17-佐賀-09":[2,3,7],"nar-2026-10-17-佐賀-10":[8,7,6],"nar-2026-10-17-佐賀-11":[7,8,5],"nar-2026-10-17-帯広ば-01":[3,7,6],"nar-2026-10-17-帯広ば-02":[2,4,9],"nar-2026-10-17-帯広ば-03":[5,9,7],"nar-2026-10-17-帯広ば-04":[1,7,6],"nar-2026-10-17-帯広ば-05":[4,10,5],"nar-2026-10-17-帯広ば-06":[2,1,6],"nar-2026-10-17-帯広ば-07":[1,4,3],"nar-2026-10-17-帯広ば-08":[4,2,6],"nar-2026-10-17-帯広ば-09":[9,4,6],"nar-2026-10-17-帯広ば-10":[5,8,7],"nar-2026-10-17-帯広ば-11":[6,7,9],"nar-2026-10-17-帯広ば-12":[4,5,8],"nar-2026-10-17-高知-01":[1,6,3],"nar-2026-10-17-高知-02":[5,11,12],"nar-2026-10-17-高知-03":[8,7,10],"nar-2026-10-17-高知-04":[9,8,2],"nar-2026-10-17-高知-05":[8,7,10],"nar-2026-10-17-高知-06":[9,6,2],"nar-2026-10-17-高知-07":[10,7,1],"nar-2026-10-17-高知-08":[7,4,5],"nar-2026-10-17-高知-09":[9,11,4],"nar-2026-10-17-高知-10":[7,5,8],"nar-2026-10-17-高知-11":[9,7,5]}''')


# Later calendar dates were held out from the exploratory candidate design.
# They are postrace source labels: this is NOT independently frozen pre-off.
HOLDOUT_LABELS = json.loads(r'''{"jra-2026-10-18-京都-01":[8,7,11],"jra-2026-10-18-京都-02":[1,4,7],"jra-2026-10-18-京都-03":[6,7,11],"jra-2026-10-18-京都-04":[7,10,12],"jra-2026-10-18-京都-05":[3,4,1],"jra-2026-10-18-京都-06":[7,2,8],"jra-2026-10-18-京都-07":[7,8,3],"jra-2026-10-18-京都-08":[5,2,3],"jra-2026-10-18-京都-09":[3,2,8],"jra-2026-10-18-京都-10":[8,2,4],"jra-2026-10-18-京都-11":[8,1,13],"jra-2026-10-18-京都-12":[3,8,10],"jra-2026-10-18-新潟-01":[8,10,1],"jra-2026-10-18-新潟-02":[5,1,7],"jra-2026-10-18-新潟-03":[3,7,9],"jra-2026-10-18-新潟-04":[4,11,9],"jra-2026-10-18-新潟-05":[11,7,10],"jra-2026-10-18-新潟-06":[12,15,1],"jra-2026-10-18-新潟-07":[9,18,7],"jra-2026-10-18-新潟-08":[10,3,7],"jra-2026-10-18-新潟-09":[1,6,10],"jra-2026-10-18-新潟-10":[16,15,9],"jra-2026-10-18-新潟-11":[3,1,5],"jra-2026-10-18-新潟-12":[8,7,2],"jra-2026-10-18-東京-01":[11,3,10],"jra-2026-10-18-東京-02":[9,1,3],"jra-2026-10-18-東京-03":[1,6,7],"jra-2026-10-18-東京-04":[12,16,15],"jra-2026-10-18-東京-05":[4,8,1],"jra-2026-10-18-東京-06":[7,1,6],"jra-2026-10-18-東京-07":[4,12,10],"jra-2026-10-18-東京-08":[5,14,15],"jra-2026-10-18-東京-09":[9,7,6],"jra-2026-10-18-東京-10":[7,6,3],"jra-2026-10-18-東京-11":[9,11,6],"jra-2026-10-18-東京-12":[14,15,13],"nar-2026-10-16-名古屋-01":[9,4,11],"nar-2026-10-16-名古屋-02":[3,2,10],"nar-2026-10-16-名古屋-03":[10,4,3],"nar-2026-10-16-名古屋-04":[6,3,5],"nar-2026-10-16-名古屋-05":[11,2,10],"nar-2026-10-16-名古屋-06":[5,7,4],"nar-2026-10-16-名古屋-07":[2,9,4],"nar-2026-10-16-名古屋-08":[3,11,1],"nar-2026-10-16-名古屋-09":[12,1,7],"nar-2026-10-16-名古屋-10":[6,3,1],"nar-2026-10-16-名古屋-11":[3,1,8],"nar-2026-10-16-名古屋-12":[12,5,7],"nar-2026-10-16-園田-01":[8,1,7],"nar-2026-10-16-園田-02":[3,2,8],"nar-2026-10-16-園田-03":[3,5,6],"nar-2026-10-16-園田-04":[1,4,3],"nar-2026-10-16-園田-05":[4,9,2],"nar-2026-10-16-園田-06":[5,4,2],"nar-2026-10-16-園田-07":[9,7,6],"nar-2026-10-16-園田-08":[5,4,7],"nar-2026-10-16-園田-09":[9,1,3],"nar-2026-10-16-園田-10":[1,2,3],"nar-2026-10-16-園田-11":[6,3,4],"nar-2026-10-16-園田-12":[7,6,1],"nar-2026-10-16-川崎-01":[8,5,6],"nar-2026-10-16-川崎-02":[2,1,6],"nar-2026-10-16-川崎-03":[3,6,4],"nar-2026-10-16-川崎-04":[3,4,2],"nar-2026-10-16-川崎-05":[9,4,8],"nar-2026-10-16-川崎-06":[12,1,11],"nar-2026-10-16-川崎-07":[8,1,10],"nar-2026-10-16-川崎-08":[7,3,5],"nar-2026-10-16-川崎-09":[5,7,6],"nar-2026-10-16-川崎-10":[5,4,8],"nar-2026-10-16-川崎-11":[8,11,1],"nar-2026-10-16-川崎-12":[10,5,8],"nar-2026-10-18-佐賀-01":[2,7,6],"nar-2026-10-18-佐賀-02":[4,1,6],"nar-2026-10-18-佐賀-03":[11,6,2],"nar-2026-10-18-佐賀-04":[7,1,11],"nar-2026-10-18-佐賀-05":[2,11,3],"nar-2026-10-18-佐賀-06":[9,7,2],"nar-2026-10-18-佐賀-07":[10,3,4],"nar-2026-10-18-佐賀-08":[2,9,1],"nar-2026-10-18-佐賀-09":[5,7,4],"nar-2026-10-18-佐賀-10":[2,1,10],"nar-2026-10-18-佐賀-11":[3,14,6],"nar-2026-10-18-帯広ば-01":[1,5,4],"nar-2026-10-18-帯広ば-02":[4,3,9],"nar-2026-10-18-帯広ば-03":[1,3,5],"nar-2026-10-18-帯広ば-04":[5,8,6],"nar-2026-10-18-帯広ば-05":[6,3,1],"nar-2026-10-18-帯広ば-06":[8,5,3],"nar-2026-10-18-帯広ば-07":[2,7,4],"nar-2026-10-18-帯広ば-08":[7,8,6],"nar-2026-10-18-帯広ば-09":[4,9,2],"nar-2026-10-18-帯広ば-10":[1,6,7],"nar-2026-10-18-帯広ば-11":[2,3,8],"nar-2026-10-18-帯広ば-12":[1,5,6],"nar-2026-10-18-盛岡-01":[8,4,11],"nar-2026-10-18-盛岡-02":[1,3,8],"nar-2026-10-18-盛岡-03":[1,9,8],"nar-2026-10-18-盛岡-04":[3,10,5],"nar-2026-10-18-盛岡-05":[1,5,7],"nar-2026-10-18-盛岡-06":[2,5,1],"nar-2026-10-18-盛岡-07":[8,5,3],"nar-2026-10-18-盛岡-08":[7,2,4],"nar-2026-10-18-盛岡-09":[10,9,8],"nar-2026-10-18-盛岡-10":[9,2,1],"nar-2026-10-18-盛岡-11":[1,2,9],"nar-2026-10-18-盛岡-12":[6,7,9],"nar-2026-10-18-金沢-01":[5,8,9],"nar-2026-10-18-金沢-02":[6,9,5],"nar-2026-10-18-金沢-03":[1,7,3],"nar-2026-10-18-金沢-04":[4,7,3],"nar-2026-10-18-金沢-05":[7,1,2],"nar-2026-10-18-金沢-06":[1,5,7],"nar-2026-10-18-金沢-07":[8,5,4],"nar-2026-10-18-金沢-08":[7,8,10],"nar-2026-10-18-金沢-09":[6,1,2],"nar-2026-10-18-金沢-10":[5,3,4],"nar-2026-10-18-高知-01":[5,8,1],"nar-2026-10-18-高知-02":[8,1,5],"nar-2026-10-18-高知-03":[2,4,5],"nar-2026-10-18-高知-04":[7,5,2],"nar-2026-10-18-高知-05":[3,2,9],"nar-2026-10-18-高知-06":[7,8,3],"nar-2026-10-18-高知-07":[1,4,3],"nar-2026-10-18-高知-08":[10,5,9],"nar-2026-10-18-高知-09":[11,8,2],"nar-2026-10-18-高知-10":[9,3,5],"nar-2026-10-18-高知-11":[5,1,2],"nar-2026-10-19-名古屋-01":[2,5,7],"nar-2026-10-19-名古屋-02":[2,5,4],"nar-2026-10-19-名古屋-03":[3,1,6],"nar-2026-10-19-名古屋-04":[2,9,10],"nar-2026-10-19-名古屋-05":[4,8,9],"nar-2026-10-19-名古屋-06":[5,10,7],"nar-2026-10-19-名古屋-07":[5,4,9],"nar-2026-10-19-名古屋-08":[5,4,2],"nar-2026-10-19-名古屋-09":[3,7,9],"nar-2026-10-19-名古屋-10":[7,12,11],"nar-2026-10-19-名古屋-11":[7,2,10],"nar-2026-10-19-名古屋-12":[11,8,6],"nar-2026-10-19-帯広ば-01":[1,6,3],"nar-2026-10-19-帯広ば-02":[1,6,7],"nar-2026-10-19-帯広ば-03":[1,7,2],"nar-2026-10-19-帯広ば-04":[4,6,8],"nar-2026-10-19-帯広ば-05":[10,9,4],"nar-2026-10-19-帯広ば-06":[3,9,1],"nar-2026-10-19-帯広ば-07":[8,9,1],"nar-2026-10-19-帯広ば-08":[10,8,6],"nar-2026-10-19-帯広ば-09":[1,8,3],"nar-2026-10-19-帯広ば-10":[6,9,10],"nar-2026-10-19-帯広ば-11":[5,2,3],"nar-2026-10-19-帯広ば-12":[6,2,10],"nar-2026-10-19-浦和-01":[2,1,5],"nar-2026-10-19-浦和-02":[6,4,7],"nar-2026-10-19-浦和-03":[3,5,4],"nar-2026-10-19-浦和-04":[4,1,5],"nar-2026-10-19-浦和-05":[2,11,5],"nar-2026-10-19-浦和-06":[3,9,5],"nar-2026-10-19-浦和-07":[8,2,10],"nar-2026-10-19-浦和-08":[4,2,7],"nar-2026-10-19-浦和-09":[1,6,8],"nar-2026-10-19-浦和-10":[8,3,4],"nar-2026-10-19-浦和-11":[8,4,11],"nar-2026-10-19-浦和-12":[4,11,6],"nar-2026-10-19-盛岡-01":[2,5,8],"nar-2026-10-19-盛岡-02":[4,1,6],"nar-2026-10-19-盛岡-03":[1,4,9],"nar-2026-10-19-盛岡-04":[5,11,4],"nar-2026-10-19-盛岡-05":[5,6,11],"nar-2026-10-19-盛岡-06":[6,9,11],"nar-2026-10-19-盛岡-07":[3,4,11],"nar-2026-10-19-盛岡-08":[3,2,11],"nar-2026-10-19-盛岡-09":[11,2,7],"nar-2026-10-19-盛岡-10":[6,5,1],"nar-2026-10-19-盛岡-11":[10,4,3],"nar-2026-10-19-盛岡-12":[1,3,7],"nar-2026-10-19-金沢-01":[1,6,2],"nar-2026-10-19-金沢-02":[6,3,2],"nar-2026-10-19-金沢-03":[8,9,7],"nar-2026-10-19-金沢-04":[4,6,9],"nar-2026-10-19-金沢-05":[3,2,4],"nar-2026-10-19-金沢-06":[7,3,1],"nar-2026-10-19-金沢-07":[4,1,2],"nar-2026-10-19-金沢-08":[3,8,7],"nar-2026-10-19-金沢-09":[5,2,4],"nar-2026-10-19-金沢-10":[1,6,8],"nar-2026-10-19-金沢-11":[11,3,4],"nar-2026-10-20-浦和-01":[9,2,1],"nar-2026-10-20-浦和-02":[1,8,5],"nar-2026-10-20-浦和-03":[2,4,1],"nar-2026-10-20-浦和-04":[2,11,5],"nar-2026-10-20-浦和-05":[3,2,9],"nar-2026-10-20-浦和-06":[12,2,7],"nar-2026-10-20-浦和-07":[6,7,4],"nar-2026-10-20-浦和-08":[1,11,7],"nar-2026-10-20-浦和-09":[7,5,2],"nar-2026-10-20-浦和-10":[1,4,2],"nar-2026-10-20-浦和-11":[1,2,3],"nar-2026-10-20-浦和-12":[11,5,4],"nar-2026-10-20-盛岡-03":[10,4,7],"nar-2026-10-20-盛岡-04":[7,6,1],"nar-2026-10-20-盛岡-05":[5,6,8],"nar-2026-10-20-盛岡-06":[10,2,5],"nar-2026-10-20-盛岡-07":[8,5,9],"nar-2026-10-20-盛岡-08":[5,7,3],"nar-2026-10-20-盛岡-09":[9,12,6],"nar-2026-10-20-盛岡-10":[1,5,4],"nar-2026-10-20-盛岡-11":[8,4,12],"nar-2026-10-20-盛岡-12":[5,12,11],"nar-2026-10-20-金沢-01":[9,4,1],"nar-2026-10-20-金沢-02":[2,6,3],"nar-2026-10-20-金沢-03":[6,3,4],"nar-2026-10-20-金沢-04":[5,4,2],"nar-2026-10-20-金沢-05":[4,1,2],"nar-2026-10-20-金沢-06":[8,9,10],"nar-2026-10-20-金沢-07":[10,9,6],"nar-2026-10-20-金沢-08":[6,9,7],"nar-2026-10-20-金沢-09":[6,4,7],"nar-2026-10-20-金沢-10":[4,1,2],"nar-2026-10-20-金沢-11":[5,6,9],"nar-2026-10-20-金沢-12":[8,4,2],"nar-2026-10-20-門別-01":[8,1,2],"nar-2026-10-20-門別-02":[6,12,3],"nar-2026-10-20-門別-03":[3,8,10],"nar-2026-10-20-門別-04":[6,7,12],"nar-2026-10-20-門別-05":[3,8,1],"nar-2026-10-20-門別-06":[8,2,1],"nar-2026-10-20-門別-07":[1,8,4],"nar-2026-10-20-門別-08":[4,6,9],"nar-2026-10-20-門別-09":[10,6,4],"nar-2026-10-20-門別-10":[7,11,4],"nar-2026-10-20-門別-11":[2,3,8],"nar-2026-10-20-門別-12":[10,12,2],"nar-2026-10-21-園田-01":[4,10,8],"nar-2026-10-21-園田-02":[6,3,2],"nar-2026-10-21-園田-03":[10,7,9],"nar-2026-10-21-園田-04":[6,5,10],"nar-2026-10-21-園田-05":[8,12,11],"nar-2026-10-21-園田-06":[11,4,2],"nar-2026-10-21-園田-07":[5,3,4],"nar-2026-10-21-園田-08":[4,5,6],"nar-2026-10-21-園田-09":[12,9,2],"nar-2026-10-21-園田-10":[1,4,3],"nar-2026-10-21-園田-11":[12,3,6],"nar-2026-10-21-園田-12":[6,11,2],"nar-2026-10-21-浦和-01":[10,12,7],"nar-2026-10-21-浦和-02":[8,9,6],"nar-2026-10-21-浦和-03":[11,9,6],"nar-2026-10-21-浦和-04":[4,1,2],"nar-2026-10-21-浦和-05":[3,2,1],"nar-2026-10-21-浦和-06":[4,11,3],"nar-2026-10-21-浦和-07":[1,6,2],"nar-2026-10-21-浦和-08":[1,2,8],"nar-2026-10-21-浦和-09":[7,11,10],"nar-2026-10-21-浦和-10":[8,1,3],"nar-2026-10-21-浦和-11":[8,7,9],"nar-2026-10-21-浦和-12":[12,11,9],"nar-2026-10-21-笠松-01":[10,11,5],"nar-2026-10-21-笠松-02":[5,9,1],"nar-2026-10-21-笠松-03":[10,2,7],"nar-2026-10-21-笠松-04":[10,12,11],"nar-2026-10-21-笠松-05":[2,4,1],"nar-2026-10-21-笠松-06":[7,10,5],"nar-2026-10-21-笠松-07":[5,12,6],"nar-2026-10-21-笠松-08":[7,6,9],"nar-2026-10-21-笠松-09":[5,1,3],"nar-2026-10-21-笠松-10":[9,7,6],"nar-2026-10-21-笠松-11":[5,3,4],"nar-2026-10-21-笠松-12":[10,5,3],"nar-2026-10-21-門別-01":[7,10,6],"nar-2026-10-21-門別-02":[11,8,6],"nar-2026-10-21-門別-03":[2,5,10],"nar-2026-10-21-門別-04":[10,11,3],"nar-2026-10-21-門別-05":[12,6,8],"nar-2026-10-21-門別-06":[9,7,6],"nar-2026-10-21-門別-07":[6,8,2],"nar-2026-10-21-門別-08":[1,5,3],"nar-2026-10-21-門別-09":[8,10,1],"nar-2026-10-21-門別-10":[9,2,7],"nar-2026-10-21-門別-11":[4,3,7],"nar-2026-10-21-門別-12":[5,1,2]}''')


def _existing_snapshot(race_id):
    date = "-".join(race_id.split("-")[1:4])
    root = ROOT / "arvexq/ui/static/saved-snapshots"
    catalog = json.loads((root / (date + ".json")).read_text(encoding="utf-8"))
    meta = catalog["races"].get(race_id)
    if meta is None:
        return None
    packed = json.loads((root / meta["file"]).read_text(encoding="utf-8"))
    raw = gzip.decompress(base64.b64decode(packed["gzipBase64"]))
    assert len(raw) == packed["bytes"]
    assert hashlib.sha256(raw).hexdigest() == packed["sha256"]
    full = json.loads(raw)
    if full.get("id") != race_id or full.get("date") != date:
        raise AssertionError("archive identity mismatch")
    # Explicit allow-list prevents result, payouts, race-day diagnosis and odds
    # from entering the prediction candidate.
    owner = full.get("circuit")
    owner = {"中央": "jra", "地方": "nar"}.get(owner, owner)
    horses = []
    for horse in full.get("horses") or []:
        source = horse.get("recentRaces") or (
            horse.get("allPastRuns") if owner == "nar" else None) or []
        # Full career is accessible for same-track facts only; Stage64 never
        # uses future/outcome runs because all runs are date-fenced.
        horses.append({
            "horseNumber": horse.get("horseNumber"),
            "frameNumber": horse.get("frameNumber"),
            "status": horse.get("status"),
            "scratched": horse.get("scratched"),
            "recentRaces": source,
            "allPastRuns": horse.get("allPastRuns") or [],
        })
    return {
        "id": race_id, "date": date, "circuit": owner,
        "analysisMode": full.get("analysisMode"),
        "track": full.get("track"), "surface": full.get("surface"),
        "distance": full.get("distance"),
        "fieldSize": full.get("fieldSize"), "horses": horses,
    }


def test_two_date_replay_baselines_and_public_tactics():
    judged = []
    observed_coverage = defaultdict(lambda: defaultdict(int))
    for race_id in sorted(LABELS):
        if "帯広ば" in race_id:
            continue
        source = _existing_snapshot(race_id)
        if source is None:
            continue
        if source.get("analysisMode") == "障害" or source.get("surface") == "障害":
            continue
        try:
            plain = predict(source, expected_circuit=source["circuit"])
            recent = predict(source, expected_circuit=source["circuit"],
                             ability_method="recent5")
        except (ValueError, KeyError, TypeError):
            continue
        stages = plain["stages"]
        if any(stages[key]["value"] is None for key in ("marks", "pace")):
            continue
        win_order = stages["marks"]["value"]["orderedWinCandidates"]
        recent_order = recent["stages"]["marks"]["value"]["orderedWinCandidates"]
        tactics = plain["paceEvidence"]["publicPositionTactics"]
        course = plain["paceEvidence"]["historicalCourseEvidence"]
        # Two qualitative candidates for comparison ONLY; not used by product.
        # No weighted score and no retrospective label-dependent changes.
        course_winners = [h for h in win_order[:5] if
            (course.get(h) or {}).get("sameTrackDistanceWins", 0) > 0]
        explicit_course = course_winners[0] if course_winners else win_order[0]
        segregated = set(tactics["separatedForwardIntentCandidates"])
        distinct_front = next((h for h in win_order[:3] if h in segregated),
                              win_order[0])
        # Freeze all four candidate predictions before opening labels.
        fact = plain["paceEvidence"]["holisticWinnerEvidence"]
        key = ("-".join(race_id.split("-")[1:4]), source["circuit"])
        observed_coverage[key]["races"] += 1
        if fact["headToHead"]:
            observed_coverage[key]["sharedPastOpposition"] += 1
        if any(x.get("sameTrackDistanceMarginSamples", 0) > 0
               for x in fact["byHorse"].values()):
            observed_coverage[key]["courseComparableMargins"] += 1
        if any(x.get("individualGateReactionSamples", 0) > 0
               for x in fact["byHorse"].values()):
            observed_coverage[key]["individualStartReadings"] += 1
        if fact["firstCorner"] is not None:
            observed_coverage[key]["verifiedFirstCornerDistance"] += 1
        challenger = (plain.get("winnerEvidenceComparison") or {}).get(
            "proposedHeadToHeadResearchChallenger")
        rematch = challenger["horseNumber"] if challenger else win_order[0]
        judged.append((race_id, source["circuit"], win_order[0],
                       recent_order[0], explicit_course, distinct_front,
                       rematch, bool(challenger)))
    assert len(judged) >= 30, "insufficient comparable saved race history"
    report = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    rematch_triggers = defaultdict(int)
    for race_id, circuit, baseline, recent, course, separated, rematch, triggered in judged:
        winner, runnerup, third = LABELS[race_id]
        if triggered:
            rematch_triggers[("-".join(race_id.split("-")[1:4]), circuit)] += 1
        for method, n in (("baseline", baseline), ("recent5", recent),
                          ("explicitCourse", course),
                          ("isolatedForward", separated),
                          ("directRivalReplayOnly", rematch)):
            row = report[("-".join(race_id.split("-")[1:4]), circuit)][method]
            row[0] += 1
            row[1] += n == winner
            row[2] += n in (winner, runnerup, third)
    for (date, circuit), methods in sorted(report.items()):
        info = "; ".join("%s %d/%d◎1着 %d/%d◎3内" % (
            method, result[1], result[0], result[2], result[0])
            for method, result in sorted(methods.items()))
        info += "; directRivalTriggers=%d; evidenceCoverage=%s" % (rematch_triggers[(date,circuit)], dict(observed_coverage[(date,circuit)]))
        warnings.warn("ARVEXQ_RESEARCH_NOT_PREOFF %s %s: %s" %
                      (date, circuit, info), UserWarning, stacklevel=1)


def test_later_day_blind_replay_comparison():
    """Compare candidate with baseline across all eligible unseen later dates."""
    locked = []
    for race_id in sorted(HOLDOUT_LABELS):
        if "帯広ば" in race_id:
            continue
        source = _existing_snapshot(race_id)
        if source is None or source.get("analysisMode") == "障害":
            continue
        if source.get("surface") == "障害":
            continue
        try:
            p = predict(source, expected_circuit=source["circuit"])
        except (KeyError, TypeError, ValueError):
            continue
        stage = p["stages"]["marks"]
        if stage["value"] is None:
            continue
        order = stage["value"]["orderedWinCandidates"]
        challenger = p["winnerEvidenceComparison"]["proposedHeadToHeadResearchChallenger"]
        new_pick = challenger["horseNumber"] if challenger else order[0]
        # Prediction/decision fully locked before reading result map.
        locked.append((race_id, source["circuit"], order[0], new_pick,
                       challenger is not None))
    assert len(locked) >= 60, "too few eligible unseen archives"
    groups = defaultdict(lambda: {"n":0, "baseWin":0, "baseTop3":0,
                                  "candidateWin":0, "candidateTop3":0,
                                  "changed":0, "goodChanges":0, "badChanges":0})
    for race_id, circuit, baseline, challenger, changed in locked:
        winning, second, third = HOLDOUT_LABELS[race_id]
        date = "-".join(race_id.split("-")[1:4])
        metrics = groups[(date, circuit)]
        metrics["n"] += 1
        metrics["baseWin"] += int(baseline == winning)
        metrics["baseTop3"] += int(baseline in (winning, second, third))
        metrics["candidateWin"] += int(challenger == winning)
        metrics["candidateTop3"] += int(challenger in (winning, second, third))
        metrics["changed"] += int(changed)
        metrics["goodChanges"] += int(changed and challenger == winning and baseline != winning)
        metrics["badChanges"] += int(changed and baseline == winning and challenger != winning)
    for (date, circuit), stats in sorted(groups.items()):
        warnings.warn("ARVEXQ_UNSEEN_RETROSPECTIVE_NOT_PREOFF %s %s %s" %
                      (date, circuit, stats), UserWarning, stacklevel=1)
