import json


def load_config():
    fp = open("config.json", "r")
    config = json.load(fp)
    fp.close()
    return config