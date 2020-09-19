import json


def read(fp) -> dict:
	with open(fp, 'r') as x:
		try: return json.load(x)
		except: return {}


def write(fp, data) -> None:
	with open(fp, 'w') as x:
		return json.dump(data, x, indent=1)
