# 太累了，就没有对 nonebot2 连续对话特性进行更深的适配了，后续可能会回头优化(以及欢迎 PR)
import re
from math import ceil
from nonebot.plugin import on_command
import salmon
from salmon import Bot
from salmon.typing import CQEvent, GroupMessageEvent, PrivateMessageEvent, T_State
from salmon.modules.authMS import util
from salmon.modules.authMS.util import notify_group
from salmon.modules.authMS.constant import config


all_add = on_command('变更所有授权', aliases={'批量变更', '批量授权'})
auth_list = on_command('授权列表', aliases={'查看授权列表', '查看全部授权', '查询全部授权'})
change_auth = on_command('变更授权', aliases={'更改时间', '授权', '更改授权时间', '更新授权'})
trans_auth = on_command('转移授权')
auth_status = on_command('授权状态')
remove_auth = on_command('清除授权', aliases={'删除授权', '移除授权', '移除群授权', '删除群授权'})
no_number_check = on_command('不检查人数', aliases={'设置人数白名单'})
no_auth_check = on_command('不检查授权', aliases={'设置授权白名单'})
no_check = on_command('添加白名单')
remove_allowlist = on_command('移除白名单', aliases={'删除白名单'})
get_allowlist = on_command('全部白名单', aliases={'白名单列表', '所有白名单'})
reload_filter = on_command('刷新事件过滤器')


@all_add.handle()
async def add_time_all_rec(bot: Bot, event: CQEvent, state: T_State):
    if event.user_id not in salmon.configs.SUPERUSERS:
        util.log(f'{event.user_id}尝试批量授权, 已拒绝')
        await all_add.finish('权限不足')
    days = event.get_plaintext().split()
    if days:
        state['days'] = days

@all_add.got('days', prompt='请发送需要为所有群增加的天数')
async def add_time_all_chat(bot: Bot, event: CQEvent, state: T_State):
    try:
        days = int(state['days'])
        authed_group_list = await util.get_authed_group_list()
        for ginfo in authed_group_list:
            await util.change_authed_time(ginfo['gid'], days)
        util.log(f'已为所有群授权增加{days}天')
        await all_add.finish(f'已为所有群授权增加{days}天')
    except:
        await all_add.finish('Invalid input.')


@auth_list.handle()
async def group_list_chat(bot: Bot, event: CQEvent):
    '''
    此指令获得的是, 所有已经获得授权的群, 其中一些群可能Bot并没有加入
    分页显示, 请在authMS.py中配置
    '''
    if event.user_id not in salmon.configs.SUPERUSERS:
        util.log(f'{event.user_id}尝试查看授权列表, 已拒绝')
        await auth_list.finish('只有主人才能查看授权列表哦')
    if isinstance(event, GroupMessageEvent):
        # 群聊查看授权列表你也是个小天才
        await auth_list.finish('不支持群聊查看')
    elif isinstance(event, PrivateMessageEvent):
        if not event.get_plaintext().split():
            # 无其他参数默认第一页
            page = 1
        else:
            page = int(event.get_plaintext().split())
        msg = '======授权列表======\n'
        authed_group_list = await util.get_authed_group_list()
        length = len(authed_group_list)
        groups_in_page = config.GROUPS_IN_PAGE
        pages_all = ceil(length / groups_in_page)  # 向上取整
        if page > pages_all:
            await auth_list.finish(f'页码错误, 当前共有授权信息{length}条, 共{pages_all}页')
        if page <= 0:
            await auth_list.finish('请输入正确的页码')
        i = 0
        for item in authed_group_list:
            i = i + 1
            if i < (page - 1) * groups_in_page + 1 or i > page * groups_in_page:
                continue
            gid = int(item['gid'])
            g_time = util.check_group(gid)
            msg_new = await util.process_group_msg(gid,
                                                    g_time,
                                                    title=f'第{i}条信息\n',
                                                    end='\n\n',
                                                    group_name_sp=item['groupName'])
            msg += msg_new
        msg += f'第{page}页, 共{pages_all}页\n发送查询授权+页码以查询其他页'
        await auth_list.finish(msg)


@change_auth.handle()
async def add_time_chat(bot: Bot, event: CQEvent):
    origin = event.get_plaintext().strip()
    pattern = re.compile(r'^(\d{5,15})([+-]\d{1,5})$')
    m = pattern.match(origin)
    if m is None:
        await change_auth.finish('请发送“授权 群号±时长”来进行指定群的授权')
    gid = int(m.group(1))
    days = int(m.group(2))
    if event.user_id not in salmon.configs.SUPERUSERS:
        util.log(f'{event.user_id}尝试为群{gid}增加{days}天授权, 已拒绝')
        await change_auth.finish('权限不足')
    result = await util.change_authed_time(gid, days)
    msg = await util.process_group_msg(gid, result, title='变更成功, 变更后的群授权信息:\n')
    await notify_group(group_id=gid, txt=f'已为本群增加{days}天授权时长。\n可在群内发送【查询授权】来查看授权时间。')
    await change_auth.finish(msg)


@trans_auth.handle()
async def group_change_chat(bot: Bot, event: CQEvent):
    if not event.get_plaintext():
        await trans_auth.finish('请发送“转移授权 旧群群号*新群群号”来进行转移')
    origin = event.get_plaintext().strip()
    pattern = re.compile(r'^(\d{5,15})\*(\d{5,15})$')
    m = pattern.match(origin)
    if m is None:
        await trans_auth.finish('格式或群号错误\n请发送“转移授权 旧群群号*新群群号”来转移群授权时长\n如果新群已经授权，则会增加对应时长')
    old_gid = int(m.group(1))
    new_gid = int(m.group(2))
    if event.user_id not in salmon.configs.SUPERUSERS:
        util.log(f'{event.user_id}尝试转移授权{old_gid}到{new_gid}, 已拒绝')
        trans_auth.finish('权限不足')
    gtime_old = util.check_group(old_gid)
    if gtime_old == 0:
        await trans_auth.finish('旧群无授权, 不可进行转移')
    if old_gid == new_gid:
        await trans_auth.finish('宁搁这儿原地TP呢？')
    await util.transfer_group(old_gid, new_gid)
    gtime_new = util.check_group(new_gid)
    msg = await util.process_group_msg(new_gid, expiration=gtime_new, title=f'旧群{old_gid}授权已清空, 新群授权状态：\n')
    await notify_group(group_id=old_gid, txt=f'已转移本群授权时长至其他群。')
    await trans_auth.finish(msg)


@auth_status.handle()
async def auth_status_chat(bot: Bot, event: CQEvent):
    if event.user_id not in salmon.configs.SUPERUSERS:
        util.log(f'{event.user_id}尝试查看授权状态, 已拒绝')
        await auth_status.finish('权限不足')
    if isinstance(event, GroupMessageEvent):
        await auth_list.finish('不支持群聊查看')
    elif isinstance(event, PrivateMessageEvent):
        sid = event.self_id
        sgl = set(g['group_id']
                    for g in await bot.get_group_list(self_id=sid))
        frl = set(f['user_id']
                    for f in await bot.get_friend_list(self_id=sid))
        # 直接从service里抄了, 面向cv编程才是真
        gp_num = len(sgl)
        fr_num = len(frl)
        agp_num = len(await util.get_authed_group_list())
        msg = f'Bot账号：{sid}\n所在群数：{gp_num}\n好友数：{fr_num}\n授权群数：{agp_num}'
        await auth_status.finish(msg)


@remove_auth.handle()
async def remove_auth_rec(bot: Bot, event: CQEvent, state: T_State):
    '''
    完全移除一个群的授权，当然群聊发送也是需要确认群号的
    '''
    gid = event.get_plaintext().split()
    if gid:
        state['gid'] = gid

@remove_auth.got('gid', prompt='请发送需要清除授权的群号')
async def remove_auth_chat(bot: Bot, event: CQEvent, state: T_State):
    try:
        gid = int(state['gid'])
        if event.user_id not in salmon.configs.SUPERUSERS:
            util.log(f'{event.user_id}尝试为群{gid}清除授权, 已拒绝')
            await remove_auth.finish('权限不足')
        time_left = util.check_group(gid)
        if not time_left:
            await remove_auth.finish('此群未获得授权')
        msg = await util.process_group_msg(gid=gid, expiration=time_left, title='已移除授权,原授权信息如下\n')
        await util.change_authed_time(gid=gid, operate='clear')
        if config.AUTO_LEAVE:
            await util.gun_group(group_id=gid, reason='本群已被移除授权，具体事项请联系维护')
            msg += '\n已尝试退出该群聊'
        await remove_auth.finish(msg)
    except:
        await remove_auth.finish('Invalid input.')


@no_number_check.handle()
async def no_number_check_rec(bot: Bot, event: CQEvent, state: T_State):
    '''
    不检查一个群的人数是否超过人数限制, 在群聊中发送则为不检查本群
    '''
    if isinstance(event, GroupMessageEvent):
        gid = event.group_id
        state['gid'] = gid
    elif isinstance(event, PrivateMessageEvent):
        gid = event.get_plaintext().split()
        if gid:
            state['gid'] = gid

@no_number_check.got('gid', prompt='请发送需要设置人数白名单的群号')
async def no_number_check_chat(bot: Bot, event: CQEvent, state: T_State):
    try:
        gid = int(state['gid'])
        if event.user_id not in salmon.configs.SUPERUSERS:
            util.log(f'{event.user_id}尝试为群{gid}设置不检查人数, 已拒绝')
            await no_number_check.finish('权限不足')
        util.allowlist(group_id=gid, operator='add', nocheck='no_number_check')
        util.log(f'管理员{event.user_id}已将群{gid}添加至白名单, 类型为不检查人数')
        await notify_group(group_id=gid, txt='已添加本群为白名单，将不会检查本群人数上限')
        await no_number_check.finish(f'已将群{gid}添加至白名单, 类型为不检查人数')
    except:
        await no_number_check.finish('Invalid input.')


@no_auth_check.handle()
async def no_auth_check_rec(bot: Bot, event: CQEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        gid = event.group_id
        state['gid'] = gid
    elif isinstance(event, PrivateMessageEvent):
        gid = event.get_plaintext().split()
        if gid:
            state['gid'] = gid

@no_auth_check.got('gid', prompt='请发送需要设置授权白名单的群号')
async def no_auth_check_chat(bot: Bot, event: CQEvent, state: T_State):
    try:
        gid = int(state['gid'])
        if event.user_id not in salmon.configs.SUPERUSERS:
            util.log(f'{event.user_id}尝试为群{gid}设置不检查授权, 已拒绝')
            await no_auth_check.finish('权限不足')
        util.allowlist(group_id=gid, operator='add', nocheck='no_auth_check')
        util.log(f'管理员{event.user_id}已将群{gid}添加至白名单, 类型为不检查授权')
        await notify_group(group_id=gid, txt='已添加本群为白名单，将不会检查本群授权是否过期')
        await no_auth_check.finish(f'已将群{gid}添加至白名单, 类型为不检查授权')
    except:
        await no_auth_check.finish('Invalid input.')


@no_check.handle()
async def no_check_rec(bot: Bot, event: CQEvent, state: T_State):
    '''
    最高级别白名单, 授权与人数都不检查
    '''
    if isinstance(event, GroupMessageEvent):
        gid = event.group_id
        state['gid'] = gid
    elif isinstance(event, PrivateMessageEvent):
        gid = event.get_plaintext().split()
        if gid:
            state['gid'] = gid

@no_check.got('gid', prompt='请发送需要添加白名单的群号')
async def no_check_chat(bot: Bot, event: CQEvent, state: T_State):
    try:
        gid = int(state['gid'])
        if event.user_id not in salmon.configs.SUPERUSERS:
            util.log(f'{event.user_id}尝试为群{gid}添加白名单, 已拒绝')
            await no_check.finish('权限不足')
        util.allowlist(group_id=gid, operator='add', nocheck='no_check')
        util.log(f'管理员{event.user_id}已将群{gid}添加至白名单, 类型为全部不检查')
        await notify_group(group_id=gid, txt='已添加本群为白名单，将不会检查本群授权以及人数上限')
        await no_check.finish(f'已将群{gid}添加至白名单, 类型为全部不检查')
    except:
        await no_check.finish('Invalid input.')


@remove_allowlist.handle()
async def remove_allowlist_rec(bot: Bot, event: CQEvent, state: T_State):
    gid = event.get_plaintext().split()
    if gid:
        state['gid'] = gid

@remove_allowlist.got('gid', prompt='请发送需要移除白名单的群号')
async def remove_allowlist_chat(bot: Bot, event: CQEvent, state: T_State):
    try:
        gid = int(state['gid'])
        if event.user_id not in salmon.configs.SUPERUSERS:
            util.log(f'{event.user_id}尝试移除白名单{gid}, 已拒绝')
            await remove_allowlist.finish('权限不足')
        re_code = util.allowlist(group_id=gid, operator='remove')
        if re_code == 'not in':
            await remove_allowlist.finish(f'群{gid}不在白名单中')
        await notify_group(group_id=gid, txt='已移除本群的白名单')
        util.log(f'已将群{gid}移出白名单')
        await remove_allowlist.finish(f'已将群{gid}移出白名单')
    except:
        await remove_allowlist.finish('Invalid input.')


@get_allowlist.handle()
async def get_allowlist_chat(bot: Bot, event: CQEvent):
    if event.user_id not in salmon.configs.SUPERUSERS:
        util.log(f'{event.user_id}尝试查看白名单, 已拒绝')
        await get_allowlist.finish('权限不足')
    if isinstance(event, GroupMessageEvent):
        await get_allowlist.finish('不支持群聊查看')
    elif isinstance(event, PrivateMessageEvent):
        allow_list = util.get_list(list_type='allowlist')
        msg = '白名单信息\n'
        gids = list(allow_list.keys())
        gname_dir = await util.get_group_info(group_ids=gids, info_type='group_name')
        # 考虑到一般没有那么多白名单, 因此此处不做分页
        i = 1
        for gid in gname_dir:
            msg += f'第{i}条:   群号{gid}\n'
            gname = gname_dir[gid]
            gnocheck = allow_list[gid]
            msg += f'群名:{gname}\n类型:{gnocheck}\n\n'
            i = i+1
        await get_allowlist.finish(msg)


@reload_filter.handle()
async def reload_ef(bot: Bot, event: CQEvent):
    if event.user_id not in salmon.configs.SUPERUSERS:
        util.log(f'{event.user_id}尝试刷新事件过滤器, 已拒绝')
        await reload_filter.finish('只有主人才能刷新事件过滤器')
        return
    await util.flush_group()
    await reload_filter.finish('刷新成功!')