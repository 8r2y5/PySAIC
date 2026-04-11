class RowCounter:
    def __init__(self):
        self.current_row = 0

    def __enter__(self):
        return self.current_row

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.current_row += 1
