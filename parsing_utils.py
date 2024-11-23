import pdfplumber
import json
import parsing3


def pdf_to_output(pdf_path, text_file, json_file):
    text = extract_text_preserving_whitespace(pdf_path, text_file)
    json = parsing3.parse_screenplay(text)
    dump_to_file(json, json_file)


def read_text(input):
    with open(input, 'r') as file:
        # Read the contents of the file
        content = file.read()

        return content


def dump_to_file(input, output):
    with open(output, 'w') as file:
        file.write(json.dumps(input, indent=2, ensure_ascii=False))


def extract_text_preserving_whitespace(pdf_path, output_file):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            # Use the layout parameter to preserve whitespace and indentation
            text += page.dedupe_chars().extract_text(x_tolerance=1,
                                                     y_tolerance=1, layout=True)

    # Writing the extracted text to the output file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(text)

    return text
