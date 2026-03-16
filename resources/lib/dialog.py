def compose_dialog_text(*lines):
    return "[CR]".join(str(line) for line in lines if line not in (None, ""))
