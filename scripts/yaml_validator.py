import jsonschema as jsonschema
import yaml
import glob
import traceback
import jsonschema
import json


class Validator:
    def __init__(self, filepath):
        self.filepath = filepath
        self.yaml_data = None
        self.json_data = {}
        with open("schema.json", "r") as schema:
            self.schema = json.load(schema)

    def validate(self):
        """
        Validate JSON against schema.
        :return: 
        """

        try:
            jsonschema.validate(self.json_data, self.schema)
            print("Document is valid.")
        except jsonschema.exceptions.ValidationError as e:
            print(e.message)
            print(e.validator_value)
            if len(e.absolute_path) == 0:
                print("Level of the error: root")
            else:
                print(e.absolute_path)

    def convert_code(self):
        """
        Convert every "code" property to a string with zfill to get 6 chars length
        :return: same json object, normalized
        """
        if check_hexa(self.json_data['code'].zfill(6)):
            self.json_data['code'] = str(self.json_data['code'].zfill(6))
        else:
            print(f"{self.json_data['code']} is not an hexadecimal value. Please check char code.")
        try:
            for corresp in self.json_data['corresp']:
                if check_hexa(corresp['code'].zfill(6)):
                    corresp['code'] = str(corresp['code'].zfill(6))
                else:
                    print(f"{corresp['code']} is not an hexadecimal value. Please check char code.")
        except KeyError:
            pass

    def convert_to_json(self):
        """
        Takes the YAML data extracted (as string) and converts it to json. 
        :return: json object
        """
        try:
            self.json_data = yaml.load(self.yaml_data, Loader=yaml.loader.BaseLoader)
        except yaml.parser.ParserError:
            print(f"Issue with file: {self.filepath}")
            print(traceback.print_exc())
            print(f"YAML section of {self.filepath} is not well formed. Please verify the indentation.")
            exit(0)

    def extract_yaml(self):
        """
        Extracts YAML data from string
        :return: YAML as string
        """
        with open(self.filepath, "r") as input_file:
            md_file = input_file.read()
        self.yaml_data = md_file.split("---")[1]


def check_hexa(val) -> bool:
    """
    Function that checks if given string is heaxdecimal
    :param val: 
    :return: Bool
    """
    try:
        int(str(val), 16)
        result = True
    except ValueError:
        result = False
    return result


if __name__ == '__main__':
    for file in glob.glob("../data/characters/*/*.md"):
        print(f"--- Validating {file.replace('../data', '')} --- ")
        FileValidator = Validator(file)
        FileValidator.extract_yaml()
        FileValidator.convert_to_json()
        FileValidator.convert_code()
        FileValidator.validate()
        print("---\n")
