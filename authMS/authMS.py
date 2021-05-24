from nonebot.plugin import on_command
import salmon
from salmon import Bot, priv
from salmon.service import parse_gid
from salmon.typing import CQEvent, T_State, PrivateMessageEvent, GroupMessageEvent
from salmon.modules.authMS import util
from salmon.modules.authMS.group import check_auth
from salmon.modules.authMS.constant import config


quick_check = on_command('快速检查')
admin_help = on_command('管理员帮助')
query_time = on_command('查询授权')


@quick_check.handle()
async def quick_check_chat(bot: Bot, event: CQEvent):
    '''
    立即执行一次检查, 内容与定时任务一样
    '''
    if event.user_id not in salmon.configs.SUPERUSERS:
        return
    await check_auth()
    await quick_check.finish('检查完成')


@admin_help.handle()
async def master_help_chat(bot: Bot, event: CQEvent):
    if isinstance(event, PrivateMessageEvent):
        if event.user_id not in salmon.configs.SUPERUSERS:
            await admin_help.finish('权限不足')
        await admin_help.finish(config.ADMIN_HELP)
    else:
        return


@query_time.handle()
async def auth_query_chat(bot: Bot, event: CQEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        if not priv.check_priv(event, priv.ADMIN):
            await query_time.finish('查询授权需要管理及以上的权限')
        gid = event.group_id
        state['gids'] = [event.group_id]  
    elif isinstance(event, PrivateMessageEvent):
        if event.user_id not in salmon.configs.SUPERUSERS:
            await query_time.finish('权限不足')
        gid = event.get_plaintext().split()
        if gid:
            state['gids'] = gid

@query_time.got('gids', prompt='请输入需要查询的群号', args_parser=parse_gid)
async def auth(bot: Bot, event: CQEvent, state: T_State):
    if not 'gids' in state:
        await query_time.finish('Invalid input.')
    for gid in state['gids']:
        result = util.check_group(gid)
        if not result:
            msg = '此群未获得授权'
        else:
            msg = await util.process_group_msg(gid, result, title='授权查询结果\n')
        await query_time.finish(msg)