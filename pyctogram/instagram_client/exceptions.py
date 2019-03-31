class InstagramException(BaseException):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return str(self.msg)

    def __str__(self):
        return self.__repr__()


class InstagramNoneResponse(InstagramException):
    pass


class InstagramNot2XX(InstagramException):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code

    def __repr__(self):
        return str(f'{self.msg} (status = {self.status_code}')


class InstagramWrongJsonStruct(InstagramException):
    def __init__(self):
        super().__init__('wrong json structure')


class InstagramEmptyBody(InstagramException):
    def __init__(self):
        super().__init__('empty body')


class InstagramNotJson(InstagramException):
    pass


class InstagramFailer(InstagramException):
    pass


class VideoTooShort(RuntimeError):
    pass
