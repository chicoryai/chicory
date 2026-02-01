from lxml import etree
from langchain.tools import Tool
import os
from abc import ABC, abstractmethod


class SchemaToFileConverter(ABC):
    """Abstract Base Class for Schema to File Conversion."""

    def __init__(self, schema_path, output_format):
        self.schema_path = schema_path
        self.output_format = output_format
        self.elements = {}

    @abstractmethod
    def parse_schema(self):
        """Parse schema and extract structure."""
        pass

    @abstractmethod
    def generate_file(self):
        """Generate a structured output file."""
        pass

    def convert_schema(self):
        """Main method to parse schema and generate output."""
        self.parse_schema()
        output_file = self.generate_file()
        return f"Generated {self.output_format.upper()} saved at: {output_file}"


class DTDToXMLConverter(SchemaToFileConverter):
    """Converts a DTD file into a structured XML file."""

    def __init__(self, dtd_path):
        super().__init__(dtd_path, output_format="xml")

    def parse_schema(self):
        """Parses DTD and extracts elements with valid tag names."""
        with open(self.schema_path, "r") as file:
            dtd = etree.DTD(file)

        for element in dtd.elements():
            self.elements[element.name] = element.content

    def extract_element_names(self, content):
        """Extracts valid element names from content declarations."""
        element_names = []

        if content is None:
            return element_names  # No children, return empty list

        if isinstance(content, str):
            element_names.append(content)  # Direct element name

        elif hasattr(content, "type"):
            # Handle 'or' (|) and 'seq' (,)
            if content.type in ("or", "seq"):
                if hasattr(content, "children"):
                    element_names.extend([child.name for child in content.children if child.name])
            elif content.type == "element" and content.name:
                element_names.append(content.name)  # Single element

        return element_names

    def generate_file(self):
        """Generates an XML file based on the parsed DTD."""
        if not self.elements:
            raise ValueError("No elements found in DTD!")

        root_name = list(self.elements.keys())[0]  # Use the first element as root
        root = etree.Element(root_name)

        def add_elements(parent, element_name):
            """Recursively add valid child elements based on DTD structure."""
            if element_name in self.elements:
                sub_elements = self.extract_element_names(self.elements[element_name])

                for sub_elem in sub_elements:
                    if sub_elem:
                        child = etree.SubElement(parent, sub_elem)
                        child.text = "PLACEHOLDER"
                        add_elements(child, sub_elem)

        add_elements(root, root_name)

        # Save XML
        output_file = self.schema_path.replace(".dtd", ".xml")
        xml_tree = etree.ElementTree(root)
        xml_tree.write(output_file, pretty_print=True, xml_declaration=True, encoding="UTF-8")

        return output_file


# LangChain Tool Definition
def dtd_to_xml_tool(dtd_file_path):
    converter = DTDToXMLConverter(dtd_file_path)
    return converter.convert_schema()


convert_dtd_to_xml_tool = Tool(
    name="DTD to XML Converter",
    description="Converts a given DTD schema into a structured XML file.",
    func=dtd_to_xml_tool
)
