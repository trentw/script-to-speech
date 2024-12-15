import re
import json


def parse_screenplay(screenplay_text):
    lines = screenplay_text.split('\n')
    chunks = []
    current_speaker = None
    i = 0
    total_lines = len(lines)

    # Collect title page lines until the first scene heading
    while i < total_lines:
        line = lines[i].rstrip('\n')
        stripped_line = line.strip()
        # Skip initial empty lines
        if stripped_line == '':
            i += 1
            continue
        # Check if line is a scene heading
        if re.match(r'^(\s*\d+\s+)?(INT\.|EXT\.).*', stripped_line):
            break
        else:
            # For each non-blank line, create a title page chunk
            chunks.append({
                'type': 'title page',
                'speaker': 'none',
                'raw_text': line,
                'text': stripped_line
            })
            i += 1

    # Now proceed with parsing the rest of the screenplay
    while i < total_lines:
        line = lines[i].rstrip('\n')
        stripped_line = line.strip()
        leading_spaces = len(line) - len(line.lstrip(' '))

        # Skip empty lines
        if stripped_line == '':
            i += 1
            continue

        # Check for page number (e.g., "39.")
        if re.match(r'^\s*\d+\.?\s*$', stripped_line):
            chunks.append({
                'type': 'page number',
                'speaker': 'none',
                'raw_text': line,
                'text': stripped_line
            })
            current_speaker = None
            i += 1
            continue

        # Check for scene header (e.g., "INT. LOCATION - DAY")
        if re.match(r'^(\s*\d+\s+)?(INT\.|EXT\.).*', stripped_line):
            chunks.append({
                'type': 'scene header',
                'speaker': 'none',
                'raw_text': line,
                'text': stripped_line
            })
            current_speaker = None
            i += 1
            continue

        # Check for speaker attribution (indented 30 or more spaces)
        if stripped_line.isupper() and leading_spaces >= 30:
            # Remove parentheticals from speaker name
            speaker_name = re.sub(r'\(.*?\)', '', stripped_line).strip()
            current_speaker = speaker_name
            chunks.append({
                'type': 'speaker attribution',
                'speaker': 'none',
                'raw_text': line,
                'text': stripped_line
            })
            i += 1
            continue

        # Check for dialog modifier (lines starting with a parenthetical)
        if current_speaker and re.match(r'^\s{20,}\(.*\)', line):
            chunks.append({
                'type': 'dialog modifier',
                'speaker': current_speaker,
                'raw_text': line,
                'text': stripped_line
            })
            i += 1
            continue

        # Check for dialog lines (indented between 20 and 29 spaces)
        if current_speaker and 20 <= leading_spaces < 30:
            dialog_lines = []
            while i < total_lines:
                dialog_line = lines[i]
                dialog_stripped = dialog_line.strip()
                dialog_leading_spaces = len(
                    dialog_line) - len(dialog_line.lstrip(' '))

                # Stop collecting dialog if line is not indented as dialog
                if not (20 <= dialog_leading_spaces < 30):
                    break

                # Stop if line is empty
                if dialog_stripped == '':
                    i += 1
                    continue

                dialog_lines.append(dialog_stripped)
                i += 1

            if dialog_lines:
                dialog_text = ' '.join(dialog_lines)
                chunks.append({
                    'type': 'dialog',
                    'speaker': current_speaker,
                    'raw_text': '\n'.join(dialog_lines),
                    'text': dialog_text
                })
            current_speaker = None
            continue

        # Check for scene description (indented less than 20 spaces)
        if leading_spaces < 20:
            scene_description_lines = []
            while i < total_lines:
                sd_line = lines[i]
                sd_stripped = sd_line.strip()
                sd_leading_spaces = len(sd_line) - len(sd_line.lstrip(' '))

                # Stop collecting scene description if line is indented more (possible dialog or speaker attribution)
                if sd_leading_spaces >= 20:
                    break

                # Stop if line is empty
                if sd_stripped == '':
                    i += 1
                    continue

                scene_description_lines.append(sd_stripped)
                i += 1

            if scene_description_lines:
                scene_description_text = ' '.join(scene_description_lines)
                chunks.append({
                    'type': 'scene description',
                    'speaker': 'none',
                    'raw_text': '\n'.join(scene_description_lines),
                    'text': scene_description_text
                })
            current_speaker = None
            continue

        # If none of the above, skip the line
        i += 1

    return chunks


# Apply the parser to your provided screenplay snippet
# screenplay_text = ""


# parsed_chunks = parse_screenplay(screenplay_text)

# Print the parsed chunks in JSON format
# print(json.dumps(parsed_chunks, indent=2, ensure_ascii=False))
