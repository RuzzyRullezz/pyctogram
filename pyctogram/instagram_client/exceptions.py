class InstagramException(BaseException):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return str(self.msg)

    def __str__(self):
        return self.__repr__()


class InstagramNoneResponse(InstagramException):
    pass


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


class InstagramNot2XX(InstagramException):
    error_message = None
    special_exception_cls_list = []

    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code

    def __repr__(self):
        return str(f'{self.msg} (status = {self.status_code}')

    @classmethod
    def register(cls, exception_class):
        if not hasattr(exception_class, 'error_message') or getattr(exception_class, 'error_message') is None:
            raise Exception("Define 'error_message' field in special exception class.")
        cls.special_exception_cls_list.append(exception_class)
        return exception_class

    @classmethod
    def get_special_exception(cls, message):
        for se in cls.special_exception_cls_list:
            if se.error_message in message:
                return se
        return None


@InstagramNot2XX.register
class InstagramUserRestricred(InstagramNot2XX):
    error_message = 'user restricted'


@InstagramNot2XX.register
class InstagramSpamDetected(InstagramNot2XX):
    error_message = 'feedback_required'


@InstagramNot2XX.register
class InstagramCheckpointRequired(InstagramNot2XX):
    error_message = 'checkpoint_required'


@InstagramNot2XX.register
class InstagramChallengeRequired(InstagramNot2XX):
    error_message = 'challenge_required'


@InstagramNot2XX.register
class InstagramLoginRequired(InstagramNot2XX):
    error_message = 'login_required'


@InstagramNot2XX.register
class InstagramAccountHasBeenDisabled(InstagramNot2XX):
    error_message = 'Your account has been disabled for violating our terms. ' \
                    'Learn how you may be able to restore your account.'


@InstagramNot2XX.register
class InstagramInvalidTargerUser(InstagramNot2XX):
    error_message = 'Invalid target user.'


@InstagramNot2XX.register
class InstagramConsentRequired(InstagramNot2XX):
    error_message = 'consent_required'


@InstagramNot2XX.register
class InstagramNotAuthorizedToView(InstagramNot2XX):
    error_message = 'Not authorized to view user'


@InstagramNot2XX.register
class InstagramCannotLikeMedia(InstagramNot2XX):
    error_message = 'Sorry, you cannot like this media'


class InstagramRequestTimeout(InstagramNot2XX):
    pass


class Instagram404(InstagramNot2XX):
    pass


class Instagram5XX(InstagramNot2XX):
    pass


class VideoTooShort(RuntimeError):
    pass
