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
        except jsonschema.exceptions.ValidationError as error:
            print(error.message)
            if len(error.absolute_path) == 0:
                print("Level of the error: root")
            else:
                print(error.absolute_path)

    def convert_code(self):
        """
        Convert every "code" property to a string with zfill to get 6 chars length
        :return: same json object, normalized
        """
        try:
            self.json_data['code'] = str(self.json_data['code'].zfill(6))
            try:
                for corresp in self.json_data['corresp']:
                    corresp['code'] = str(corresp['code'].zfill(6))
            except KeyError:
                pass
        except KeyError:
            print("The character must be identified by an hexa code.")

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




if __name__ == '__main__':
    for file in glob.glob("../data/characters/*/*.md"):
        print(f"--- Validating {file.replace('../data', '')} --- ")
        FileValidator = Validator(file)
        FileValidator.extract_yaml()
        FileValidator.convert_to_json()
        FileValidator.convert_code()
        FileValidator.validate()
        print("---\n")
