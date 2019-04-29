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


class InstagramDidntChangeTheStatus(InstagramException):
    pass


class InstagramUserRestricred(InstagramNot2XX):
    user_restricted_msg = 'user restricted'


class InstagramSpamDetected(InstagramNot2XX):
    feedback_required_message = 'feedback_required'


class InsragramCheckpointRequired(InstagramNot2XX):
    checkpoint_required_message = 'checkpoint_required'

    def __init__(self, msg, status_code, checkpoint_url):
        super().__init__(msg, status_code)
        self.checkpoint_required_message = checkpoint_url


class VideoTooShort(RuntimeError):
    pass
