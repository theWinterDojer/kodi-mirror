class BackupProgress:
    def __init__(self, dialog):
        self._dialog = dialog

    def start(self, heading):
        self._dialog.create(heading, "Starting backup.")

    def update(self, percent, message):
        self._dialog.update(percent, message)

    def close(self):
        self._dialog.close()
