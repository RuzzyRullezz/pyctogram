API_URL = 'https://i.instagram.com/api/v1'
FETCH_URL = f'{API_URL}/si/fetch_headers/?challenge_type=signup&guid='
LOGIN_URL = f'{API_URL}/accounts/login/'
LOGOUT_URL = f'{API_URL}/accounts/logout/'
SYNC_URL = f'{API_URL}/qe/sync/'
USER_LIST_URL = f'{API_URL}/friendships/autocomplete_user_list'
TIMELINE_URL = f'{API_URL}/feed/timeline/'
INBOX_URL = f'{API_URL}/news/inbox/'
USER_INFO_URL = f'{API_URL}/users/%d/info/'
FRIENDSHIPS_URL = f'{API_URL}/friendships/%s/%d/'
UPLOAD_IMG_URL = f'{API_URL}/upload/photo/'
EXPOSE_URL = f'{API_URL}/qe/expose/'
CONF_URL = f'{API_URL}/media/configure/'
UPLOAD_VIDEO_URL = f'{API_URL}/upload/video/'
DELETE_MEDIA_URL = f'{API_URL}/media/%s/delete/'
DIRECT_SHARE_URL = f'{API_URL}/direct_v2/threads/broadcast/media_share/'
DIRECT_MSG_URL = f'{API_URL}/direct_v2/threads/broadcast/text/'
CHANGE_PROF_PHOTO_URL = f'{API_URL}/accounts/change_profile_picture/'
EDIT_PROF_URL = f'{API_URL}/accounts/edit_profile/'
FOLLOWING_URL = f'{API_URL}/friendships/%d/following/'
FOLLOWERS_URL = f'{API_URL}/friendships/%d/followers/'
FRIENDSHIPS_INFO_URL = f'{API_URL}/friendships/show/%d/'
LIKE_URL = f'{API_URL}/media/%s/like/'
COMMENT_URL = f'{API_URL}/media/%s/comment/'
MAPS_URL = f'{API_URL}/maps/user/%d/'
TAGS_URL = f'{API_URL}/usertags/%d/feed/'
FEED_URL = f'{API_URL}/feed/user/%d/'
MEDIA_INFO_URL = f'{API_URL}/media/%s/info/'
MEFIA_COMMENTS_URL = f'{API_URL}/media/%s/comments/'
EDIT_MEDIA_URL = f'{API_URL}/media/%s/edit_media/'