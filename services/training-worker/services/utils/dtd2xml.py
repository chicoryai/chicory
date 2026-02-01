import os
import re
from lxml import etree


def parse_dtd_manual(dtd_path):
    """
    Reads the DTD file as text and extracts element declarations.
    Returns a dictionary mapping each element name to its child elements.
    """
    with open(dtd_path, "r", encoding="utf-8") as f:
        dtd_text = f.read()

    # Regex to match DTD element declarations:
    pattern = re.compile(r'<!ELEMENT\s+(\w+)\s+\(([^)]*)\)([*+?]?)>')

    elements = {}
    for match in pattern.finditer(dtd_text):
        elem_name = match.group(1)
        content_model = match.group(2).strip()
        occurrence_modifier = match.group(3)  # Captures * or + or ?

        if content_model == "#PCDATA":
            elements[elem_name] = {"children": [], "modifier": occurrence_modifier}
        else:
            children = [alt.strip() for alt in re.split(r'\s*\|\s*', content_model) if alt.strip()]
            elements[elem_name] = {"children": children, "modifier": occurrence_modifier}

        print(f"Element '{elem_name}' children: {elements[elem_name]['children']} Modifier: {occurrence_modifier}")

    return elements


def generate_sample_xml(elements, root_name):
    """
    Recursively generates a sample XML tree from the DTD structure.
    Ensures correct hierarchical relationships and prevents duplicate root elements.
    """
    root = etree.Element(root_name)

    def add_child(parent, elem_name):
        # Prevent re-adding the root element inside itself
        if elem_name not in elements or (elem_name == root_name and parent is not root):
            return  # Stop if element is not defined in the DTD or is the root being nested

        element_info = elements[elem_name]
        children = element_info["children"]
        modifier = element_info["modifier"]

        # Apply the modifier logic (*, +, ?)
        repeat_count = 1 if modifier in ("*", "+") else 0 if modifier == "?" else 1

        for _ in range(repeat_count):
            if parent.tag == elem_name:
                parent_element = parent
            else:
                parent_element = etree.SubElement(parent, elem_name)
            for child in children:
                add_child(parent_element, child)  # Recursively add child elements

    add_child(root, root_name)
    return root


def parse_dtd_to_xml(dtd_path, output_xml="generated_output.xml"):
    """
    Parses the given DTD, generates sample XML that conforms to the DTD,
    writes the XML to a file, and then validates it against the DTD.
    """
    elements = parse_dtd_manual(dtd_path)
    if not elements:
        print("No element declarations found in the DTD. Please check the file.")
        return

    # Assume 'Header' is the root element, otherwise use the first declared element
    root_name = "Header" if "Header" in elements else list(elements.keys())[0]
    print(f"\nAssuming '{root_name}' is the root element...\n")

    # Generate the sample XML tree
    sample_xml_tree = generate_sample_xml(elements, root_name)
    xml_str = etree.tostring(sample_xml_tree, pretty_print=True, xml_declaration=True, with_comments=True, encoding="UTF-8")

    # Write the XML to a file
    with open(output_xml, "wb") as f:
        f.write(xml_str)
    print(f"XML file '{output_xml}' has been created successfully.\n")

    # Validate the generated XML against the DTD
    try:
        xml_doc = etree.parse(output_xml)
        with open(dtd_path, "r", encoding="utf-8") as f:
            dtd = etree.DTD(f)
        if dtd.validate(xml_doc):
            print("Validation successful: XML is valid according to the DTD.\n")
            print("Generated XML:")
            print(xml_str.decode("utf-8"))
        else:
            print("Validation failed: XML does not conform to the DTD.")
            print(dtd.error_log.filter_from_errors())
    except Exception as e:
        print(f"Error during XML validation: {e}")


if __name__ == "__main__":
    dtd_path = "/Users/sarkarsaurabh.27/Documents/Projects/brewsearch/data/pace_labs_sedd/raw/data/sedd_5-2_general_2a_2.dtd"  # Path to your DTD file
    output_xml = "/Users/sarkarsaurabh.27/Documents/Projects/brewsearch/data/pace_labs_sedd/raw/data/dummy.xml"  # Desired output XML filename

    # Convert DTD to XML and validate
    parse_dtd_to_xml(dtd_path, output_xml)

    # If you have a real sample XML file, validate it as well
    # sample_xml = "/Users/sarkarsaurabh.27/Documents/Projects/brewsearch/data/pace_labs_sedd/raw/data/sample.xml"  # Desired output XML filename
    # if os.path.exists(sample_xml):
    #     validate_xml(sample_xml, dtd_path)
