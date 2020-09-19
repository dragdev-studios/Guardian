import json


class Save:
    def __init__(self, file: str):
        self.file = "data/" + file + ".json"

    def load_data(self):
        try:
            with open(self.file, "r") as data_file:
                return json.load(data_file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_data(self, dictionary: dict):
        with open(self.file, "w") as data_file:
            json.dump(dictionary, data_file)

    def read_key(self, key):
        try:
            return self.load_data()[str(key)]
        except KeyError:
            return None

    def save_key(self, key, value):
        json_data = self.load_data()
        json_data[str(key)] = value
        self.save_data(json_data)
        return json_data

    def remove_key(self, key):
        json_data = self.load_data()
        removed = None
        try:
            removed = json_data.pop(str(key))
            self.save_data(json_data)
        except KeyError:
            pass
        return removed

    def wipe(self, agree: str):
        if agree == "I confirm that I want to wipe all data":
            self.save_data({})
            return {}
        else:
            raise TypeError("It looks like your confirmation string for wiping JSON data was malformed...")

