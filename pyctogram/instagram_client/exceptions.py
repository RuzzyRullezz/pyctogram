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


class InstagramCheckpointRequired(InstagramNot2XX):
    checkpoint_required_message = 'checkpoint_required'

    def __init__(self, msg, status_code, checkpoint_url):
        super().__init__(msg, status_code)
        self.checkpoint_url = checkpoint_url


class InstagramChallengeRequired(InstagramNot2XX):
    challenge_required_message = 'challenge_required'

    def __init__(self, msg, status_code, challenge_url):
        super().__init__(msg, status_code)
        self.challenge_url = challenge_url


class InstagramLoginRequired(InstagramNot2XX):
    login_required_message = 'login_required'


class InstagramAccountHasBeenDisabled(InstagramNot2XX):
    inactive_user_message = 'Your account has been disabled for violating our terms. ' \
                            'Learn how you may be able to restore your account.'


class InstagramInvalidTargerUser(InstagramNot2XX):
    invalid_target_user_message = 'Invalid target user.'


class InstagramConsentRequired(InstagramNot2XX):
    consent_required_message = 'consent_required'


class InstagramNotAuthorizedToView(InstagramNot2XX):
    not_authorized_to_view_message = 'Not authorized to view user'


class InstagramCannotLikeMedia(InstagramNot2XX):
    cannot_like_media = 'Sorry, you cannot like this media'


class Instagram404(InstagramNot2XX):
    pass


class Instagram5XX(InstagramNot2XX):
    pass


class VideoTooShort(RuntimeError):
    pass
