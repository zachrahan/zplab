class LumencorException(Exception):
    def __init__(self, description):
        self.description = description
    def __str__(self):
        return repr(self.description)

