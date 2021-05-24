# 注意, 此配置中的部分选项可能暂时不生效, 请以README中列举出的功能为准

class auth_config(object):

    # 授权系统自动检测总开关, 默认为关闭状态，此时不会自动检测/自动退群/停止响应无授权群聊
    # 设置此项目的是初次使用authMS时系统时的过渡选项, 正式使用应当配置为True
    ENABLE_AUTH = True

# -------------------事件过滤器---------------------
    # 事件过滤器配置文件的地址,例如/root/go-cqhttp/filter.json(必须填写)
    EVENT_FILTER = r'C:/bot/Go-cqhttp/filter.json'

# -------------------数据互通---------------------
    # 互通数据库的目录,例如group.sqlite位置/root/database/group.sqlite
    # 此时便填写/root/database/即可
    DB_PATH = ''

    # 是否启用互通
    ENABLE_COM = False

# --------------------群组管理相关---------------------

    # 授权到期后是否自动退群
    AUTO_LEAVE = True

    # 新群试用天数, 0天意味着机器人将不接受未授权群的入群邀请, 即便
    # 不允许重复试用, 如果群已经在试用列表且试用过期中仍然会被拒绝
    NEW_GROUP_DAYS = 0

    # 到期前的多少天开始提醒, 设置为0时将不会提醒
    REMIND_BRFORE_EXPIRED = 2

    # 到期后多少天退群, 仅当配置AUTO_LEAVE为True是此项有效, 设置为0则立即退群
    LEAVE_AFTER_DAYS = 0

    # 允许的最大群人数, 3000为不限制, 因为QQ群最大人数为3000
    # 进群后, 立刻检测一次人数（因为进群邀请不包含人数信息）
    MAX_GROUP_NUM = 200

    # 提醒/检查的时间间隔, 单位小时,
    # 值为1, 意为每小时检查一次, 注意实际每天的检查次数会向下取整
    FREQUENCY = 6

# ----------------------授权列表----------------------------

    # 私聊使用授权列表时, 每页显示的群的个数,不推荐超过10, 否则消息会非常长
    GROUPS_IN_PAGE = 5

#----------------------发言文本---------------------------

    # 加入新群时的发言, 同时适用于50人以上群和50人以下群
    NEW_GROUP_MSG = '''
    Bot已成功加入本群, 发送帮助以获得更多信息
    '''.strip()

    # 离开群之前的发言
    GROUP_LEAVE_MSG = '''
Bot即将退出本群
退群原因:
    '''.strip()

    # 提醒授权即将过期的发言, 在支持变量替换前不生效
    REMIND_MSG = '''
本群授权即将到期
    '''.strip()

    ADMIN_HELP='''
可用指令一览:
[授权列表] 检查所有已授权群
[授权状态] 查看Bot当前已加入群/已授权群的统计
[快速检查] 立刻检查群的授权
[刷新事件过滤器] 手动刷新事件过滤器
[变更授权 12345+1] 为一个群变更授权时间(+或-)
[转移授权 12345*54321] 转移已有群的授权
[清除授权 12345] 完全移除一个群的授权并退群(如果配置了的话)
[变更所有授权 3] 为所有已授权的群增加3天时间
[不检查人数/授权 12345] 群聊中发送则不必附加群号
[添加/移除白名单 12345] 群聊中发送则不必附加群号
[全部白名单] 查询全部白名单信息
    '''.strip()

# --------------------加好友相关-------------------------------
    # 自动接受加好友请求, 请把加我为好友的方式设置为“需要验证信息”
    FRIEND_APPROVE = True

# ------------------------日志-----------------------------
    # 日志, 记录群组加入, 群组退出, 群组过期, 好友添加
    LOG = True

    # 调试开关, 记录本系统所有信息
    DEBUG = False