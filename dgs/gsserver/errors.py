class ResourceUnavailableError(Exception):
    pass


class ResourceNotFoundError(Exception):
    def __init__(self, resource_id):
        self.resource_id = resource_id


class ScriptParseError(Exception):
    def __init__(self, script_errors):
        self.script_errors = script_errors


class SearchRequestError(Exception):
    def __init__(self, errors):
        self.errors = errors
