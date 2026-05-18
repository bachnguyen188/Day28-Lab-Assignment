# scripts/patch_grafana.py
import json

path = 'monitoring/grafana/dashboards/fastapi_dashboard.json'
with open(path, 'r') as f:
    data = json.load(f)

def replace_ds(obj):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == 'uid' and v == '${DS_PROMETHEUS}':
                obj[k] = 'prometheus'
            elif isinstance(v, str) and '${DS_PROMETHEUS}' in v:
                obj[k] = v.replace('${DS_PROMETHEUS}', 'prometheus')
            else:
                replace_ds(v)
    elif isinstance(obj, list):
        for item in obj:
            replace_ds(item)

replace_ds(data)

with open(path, 'w') as f:
    json.dump(data, f, indent=2)

print("Successfully patched Grafana dashboard JSON!")
