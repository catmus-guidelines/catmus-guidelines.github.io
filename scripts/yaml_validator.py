import os

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

    def validate(self) -> bool:
        """
        Validate JSON against schema.
        :return: a boolean, stating the validation has failed or not
        """

        try:
            jsonschema.validate(self.json_data, self.schema)
            github_print("Document is valid.")
            return True
        except jsonschema.exceptions.ValidationError as error:
            github_print(error.message)
            if len(error.absolute_path) == 0:
                github_print("Level of the error: root")
            else:
                github_print(error.absolute_path)
            return False

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
            github_print("The character must be identified by an hexa code.")

    def convert_to_json(self):
        """
        Takes the YAML data extracted (as string) and converts it to json. 
        :return: json object
        """
        try:
            self.json_data = yaml.load(self.yaml_data, Loader=yaml.loader.BaseLoader)
        except yaml.parser.ParserError:
            github_print(f"Issue with file: {self.filepath}")
            github_print(traceback.print_exc())
            github_print(f"YAML section of {self.filepath} is not well formed. Please verify the indentation.")
            exit(0)

    def extract_yaml(self):
        """
        Extracts YAML data from string
        :return: YAML as string
        """
        with open(self.filepath, "r") as input_file:
            md_file = input_file.read()
        self.yaml_data = md_file.split("---")[1]


def github_print(string):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(string, file=fh)


if __name__ == '__main__':
    validations = []
    for file in glob.glob("../data/characters/*/*.md"):
        github_print(f"--- Validating {file.replace('../data', '')} --- ")
        FileValidator = Validator(file)
        FileValidator.extract_yaml()
        FileValidator.convert_to_json()
        FileValidator.convert_code()
        validations.append(FileValidator.validate())
        github_print("---\n")
    if any(result is False for result in validations):
        exit(2)
    else:
        exit(0)
