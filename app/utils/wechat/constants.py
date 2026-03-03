
import enum

class WeChatErrorCode(enum.Enum):
    """
    WeChat API Error Codes
    Reference: https://developers.weixin.qq.com/doc/oplatform/developers/errCode/
    """
    SUCCESS = 0
    SYSTEM_BUSY = -1
    INVALID_CREDENTIAL = 40001
    INVALID_GRANT_TYPE = 40002
    INVALID_OPENID = 40003
    INVALID_MEDIA_TYPE = 40004
    INVALID_FILE_TYPE = 40005
    INVALID_MEDIA_SIZE = 40006
    INVALID_MEDIA_ID = 40007
    INVALID_MESSAGE_TYPE = 40008
    INVALID_IMAGE_SIZE = 40009
    INVALID_VOICE_SIZE = 40010
    INVALID_VIDEO_SIZE = 40011
    INVALID_THUMB_SIZE = 40012
    INVALID_APPID = 40013
    ACCESS_TOKEN_MISSING = 41001
    ACCESS_TOKEN_EXPIRED = 42001
    REFRESH_TOKEN_EXPIRED = 42002
    OAUTH_CODE_EXPIRED = 42003
    USER_CHANGE_AUTH = 42007
    REQUIRE_HTTPS = 43001
    REQUIRE_POST = 43002
    REQUIRE_HTTPS_POST = 43003
    REQUIRE_SUBSCRIBE = 43004
    EMPTY_MEDIA_DATA = 44001
    POST_DATA_EMPTY = 44002
    IMG_SIZE_TOO_LARGE = 44003
    VOICE_SIZE_TOO_LARGE = 44004
    VIDEO_SIZE_TOO_LARGE = 44005
    MUSIC_SIZE_TOO_LARGE = 44006
    MSG_CONTENT_TOO_LONG = 45002
    MSG_TITLE_TOO_LONG = 45003
    MSG_DESC_TOO_LONG = 45004
    URL_TOO_LONG = 45005
    MEDIA_TOO_LARGE = 45006
    VOICE_TOO_LONG = 45007
    MSG_TOO_LONG = 45008
    API_QUOTA_LIMIT = 45009
    TEMPLATE_SIZE_LIMIT = 45010
    API_UNAUTHORIZED = 48001
    USER_LIMITED = 50002
    MENU_UNAUTHORIZED = 65400
    NO_QUOTA = 45011
    
    @classmethod
    def get_message(cls, code):
        messages = {
            0: "请求成功",
            -1: "系统繁忙，此时请开发者稍候再试",
            40001: "获取 access_token 时 AppSecret 错误，或者 access_token 无效",
            40002: "不合法的凭证类型",
            40003: "不合法的 OpenID",
            40004: "不合法的媒体文件类型",
            40005: "不合法的文件类型",
            40006: "不合法的文件大小",
            40007: "不合法的媒体文件 id",
            40008: "不合法的消息类型",
            40009: "不合法的图片文件大小",
            40010: "不合法的语音文件大小",
            40011: "不合法的视频文件大小",
            40012: "不合法的缩略图文件大小",
            40013: "不合法的 AppID",
            41001: "缺少 access_token 参数",
            42001: "access_token 超时",
            42002: "refresh_token 超时",
            42003: "oauth_code 超时",
            42007: "用户修改微信密码，accesstoken和refreshtoken失效，需要重新授权",
            43001: "需要 GET 请求",
            43002: "需要 POST 请求",
            43003: "需要 HTTPS 请求",
            43004: "需要接收者关注",
            44001: "多媒体文件为空",
            44002: "POST 的数据包为空",
            44003: "图文消息内容为空",
            44004: "文本消息内容为空",
            45002: "消息内容超过限制",
            45003: "标题字段超过限制",
            45004: "描述字段超过限制",
            45005: "链接字段超过限制",
            45006: "图片链接字段超过限制",
            45007: "语音播放时间超过限制",
            45008: "图文消息超过限制",
            45009: "接口调用超过限制",
            45010: "创建菜单个数超过限制",
            45011: "API 调用太频繁，请稍候再试",
            48001: "api 功能未授权，请确认公众号/服务号已获得该接口",
            50001: "用户未授权该 api",
            50002: "用户受限，可能是违规后接口被封禁",
            65400: "API不可用，即没有开通/升级到新版自定义菜单",
        }
        return messages.get(code, f"Unknown Error: {code}")
