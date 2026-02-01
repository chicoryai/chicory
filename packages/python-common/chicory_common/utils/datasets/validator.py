from abc import ABC, abstractmethod

class Validator(ABC):
    """
    Abstract base class for validators.
    """

    @abstractmethod
    def validate(self, xml_path: str) -> bool:
        """
        Validate the given XML file.

        :param xml_path: Path to the XML file to validate.
        :return: True if valid, False otherwise.
        """
        pass


from lxml import etree

class DTDValidator(Validator):
    """
    Validator for XML files against a DTD.
    """

    def __init__(self, dtd_path: str):
        """
        Initialize with the path to the DTD file.

        :param dtd_path: Path to the DTD file.
        """
        self.dtd_path = dtd_path
        self.dtd = self._load_dtd()

    def _load_dtd(self) -> etree.DTD:
        """
        Load and parse the DTD file.

        :return: Parsed DTD object.
        """
        try:
            with open(self.dtd_path, 'r') as dtd_file:
                dtd_content = dtd_file.read()
            return etree.DTD(dtd_content)
        except (etree.DTDParseError, FileNotFoundError) as e:
            raise ValueError(f"Error loading DTD file: {e}")

    def validate(self, xml_path: str) -> bool:
        """
        Validate the XML file against the DTD.

        :param xml_path: Path to the XML file to validate.
        :return: True if the XML is valid, False otherwise.
        """
        try:
            with open(xml_path, 'r') as xml_file:
                xml_content = xml_file.read()
            xml_doc = etree.XML(xml_content)
            is_valid = self.dtd.validate(xml_doc)
            if not is_valid:
                print("Validation errors:")
                print(self.dtd.error_log.filter_from_errors())
            return is_valid
        except (etree.XMLSyntaxError, FileNotFoundError) as e:
            print(f"Error parsing XML file: {e}")
            return False


# if __name__ == "__main__":
#     dtd_validator = DTDValidator("path/to/your/schema.dtd")
#     xml_file_path = "path/to/your/document.xml"
#     if dtd_validator.validate(xml_file_path):
#         print("The XML file is valid.")
#     else:
#         print("The XML file is invalid.")
