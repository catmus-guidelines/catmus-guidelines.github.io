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

        validator = jsonschema.Draft7Validator(self.schema)
        errors = validator.iter_errors(self.json_data)  # get all validation errors
        errors_as_list = list(errors)
        if len(errors_as_list) == 0:
            print("Document is valid.")
            return True
        else:
            for error in errors_as_list:
                print(error.message)
                if len(error.absolute_path) == 0:
                    print("Level of the error: root")
                else:
                    print(f"Path to problematic item: {error.absolute_path}")
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
    validations = []
    for file in glob.glob("../data/characters/*/*.md"):
        print(f"--- Validating {file.replace('../data', '')} --- ")
        FileValidator = Validator(file)
        FileValidator.extract_yaml()
        FileValidator.convert_to_json()
        FileValidator.convert_code()
        validations.append(FileValidator.validate())
        print("---\n")
    if any(result is False for result in validations):
        print("One document or more are not correctly formatted")
        exit(2)
    else:
        print("Succes")
        exit(0)
