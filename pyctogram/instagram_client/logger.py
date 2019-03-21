class RequestLog:
    def __init__(self):
        self.url = None
        self.request_headers = None
        self.request_body = None
        self.request_method = None
        self.request_timestamp = None
        self.status_code = None
        self.response_headers = None
        self.response_body = None
        self.response_timestamp = None
        self.error = None
