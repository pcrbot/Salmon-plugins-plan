import pytz
import asyncio
from datetime import datetime
from nonebot.plugin import on_notice, on_request
from nonebot.adapters.cqhttp import GroupRequestEvent, GroupIncreaseNoticeEvent
import salmon
from salmon import Bot, configs
from salmon.modules.authMS import util
from salmon.modules.authMS.constant import config, group_dict, trial_list


tz = pytz.timezone('Asia/Shanghai')

group_more_request = on_request()
group_50_notice = on_notice()

@group_more_request.handle()
async def handle_group_invite(bot: Bot, event: GroupRequestEvent):
    '''
    自动处理入群邀请
    适用于50人以上的邀请的情况, 50人以下请参见下一条函数
    '''
    if not config.ENABLE_AUTH:
        # 配置ENABLE_AUTH为0, 则授权系统不起作用, 不会自动通过加群邀请
        return
    if event.sub_type == 'invite':
        gid = event.group_id
        new_group_auth = await util.new_group_check(gid)
        if event.user_id not in configs.SUPERUSERS:
            if new_group_auth == 'expired' or new_group_auth == 'no trial':
                await bot.set_group_add_request(flag=event.flag,
                                                    sub_type=event.sub_type,
                                                    approve=False,
                                                    reason='邀请进入无授权群请联系维护组')
                util.log(f'接受到加群邀请, 群号{gid}授权状态{new_group_auth}, 拒绝加入', 'group_add')
            elif new_group_auth == 'authed' or new_group_auth == 'trial':
                await bot.set_group_add_request(flag=event.flag,
                                                    sub_type=event.sub_type,
                                                    approve=True)
                util.log(f'接受到加群邀请, 群号{gid}授权状态{new_group_auth}, 同意加入', 'group_add')
        else:
            await bot.set_group_add_request(flag=event.flag,
                                                sub_type=event.sub_type,
                                                approve=True)
            util.log(f'维护邀请入群, 群号{gid}授权状态{new_group_auth}, 同意加入', 'group_add')
    elif event.sub_type == 'add':
        cfg = configs.groupmaster.join_approve
        gid = event.group_id
        if gid not in cfg:
            return
        for k in cfg[gid].get('keywords', []):
            if k in event.comment:
                await bot.set_group_add_request(flag=event.flag,
                                                sub_type=event.sub_type,
                                                approve=True)
                return
        if cfg[gid].get('reject_when_not_match', False):
            await bot.set_group_add_request(flag=event.flag,
                                                sub_type=event.sub_type,
                                                approve=False)
            return


@group_50_notice.handle()
async def approve_group_invite_auto(bot: Bot, event: GroupIncreaseNoticeEvent):
    '''
    被邀请加入50人以下群时会自动接受, 此时获得的事件类型为通知而非邀请.
    无法处理拒绝入群的邀请, 应当使用退群(如果开启了自动退群的话)
    '''
    if not event.is_tome():
        return
    gid = event.group_id
    rt = await check_number(gid)
    if rt == 'overflow':
        # 人数超标不自动试用, 考虑到风控, 也不会立刻退群, 而是在下一次自动检查时退群
        new_group_auth = 'no trial'
    else:
        new_group_auth = await util.new_group_check(gid)
    if new_group_auth == 'expired' or new_group_auth == 'no trial':
        await util.notify_group(group_id=gid, txt='本群无授权或授权或已过期, 请联系维护')
        util.log(f'成功加入群{gid}中,该群授权状态{new_group_auth}, 将在下次计划任务时自动退出', 'group_leave')
        salmon.logger.info(f'成功加入群{gid}中,该群授权状态{new_group_auth}, 将在下次计划任务时自动退出')
    elif new_group_auth == 'authed' or new_group_auth == 'trial':
        await asyncio.sleep(5)  # 别发太快了
        # 避免重复try
        await util.notify_group(group_id=gid, txt=config.NEW_GROUP_MSG)
    util.log(f'成功加入群{gid}中, 该群授权状态{new_group_auth}', 'group_add')
    salmon.logger.info(f'成功加入群{gid}中, 该群授权状态{new_group_auth}')


async def check_auth():
    '''
    检查所有已加入群的授权状态和人数
    '''
    await check_number()      # 独立地检查一次所有群的人数是否超标
    group_info_all = await util.get_group_list_all()
    for group in group_info_all:
        gid = group['group_id']
        if gid in group_dict:
            util.log(f'正在检查群{gid}的授权......')
            # 此群已有授权或曾有授权, 检查是否过期
            time_left = group_dict[gid] - datetime.now()
            days_left = time_left.days
            rt_code = util.allowlist(gid)
            if rt_code == 'no_check' or rt_code == 'no_auth_check':
                # 在白名单, 并不会影响过期事件
                continue
            if time_left.total_seconds() <= 0:
                # 已过期, 检查是否在白名单中
                if config.AUTO_LEAVE and time_left.total_seconds() < -config.LEAVE_AFTER_DAYS * 86400:
                    # 自动退群且已过期超过LEAVE_AFTER_DAYS天, 如果设置LEAVE_AFTER_DAYS为0则立刻退群
                    await util.gun_group(group_id=gid, reason='授权过期')
                    util.log(f'群{gid}授权过期,已自动退群', 'group_leave')
                else:
                    # 不自动退群, 只发消息提醒
                    t_sp = '【提醒】本群授权已过期\n'
                    e_sp = '若需要继续使用请联系bot维护'
                    gname_sp = group['group_name']
                    msg_expired = await util.process_group_msg(gid=gid, expiration=group_dict[gid], title=t_sp,
                                                               end=e_sp, group_name_sp=gname_sp)
                    try:
                        for bot in salmon.get_bot_list():
                            await bot.send_group_msg(group_id=gid, message=msg_expired)
                    except Exception as e:
                        util.log(f'向群{gid}发送过期提醒时发生错误{type(e)}')
                group_dict.pop(gid)
                await util.flush_group()
            if days_left < config.REMIND_BRFORE_EXPIRED and days_left >= 0:
                # 将要过期
                msg_remind = await util.process_group_msg(
                    gid=gid,
                    expiration=group_dict[gid],
                    title=f'【提醒】本群的授权已不足{days_left + 1}天\n',
                    end='\n若需要继续使用请联系bot维护',
                    group_name_sp=group['group_name'])
                try:
                    await bot.send_group_msg(group_id=gid,
                                             message=msg_remind)
                except Exception as e:
                    salmon.logger.error(f'向群{gid}发生到期提醒消息时发生错误{type(e)}')
            util.log(f'群{gid}的授权不足{days_left + 1}天')
        elif gid not in trial_list:
            # 正常情况下, 无论是50人以上群还是50人以下群, 都需要经过机器人同意或检查
            # 但是！如果机器人掉线期间被拉进群试用, 将无法处理试用, 因此有了这部分憨批代码
            if not config.NEW_GROUP_DAYS and config.AUTO_LEAVE:
                # 无新群试用机制,直接退群
                await util.gun_group(group_id=gid, reason='无授权')
                util.log(f'发现无记录而被拉入的新群{gid}, 已退出此群', 'group_leave')
            else:
                await util.new_group_check(gid)
                util.log(f'发现无记录而被拉入的新群{gid}, 已开始试用', 'group_add')


async def check_number(group_id=0):
    '''
    检查所有群的成员数量是否符合要求, 当传入group_id时则检查传入的群
    '''
    if group_id == 0:
        gnums = await util.get_group_info(info_type='member_count')
    else:
        __gid = group_id
        gnums = await util.get_group_info(group_ids=__gid, info_type='member_count')
    for gid in gnums:
        if gnums[gid] > config.MAX_GROUP_NUM:
            # 人数超过, 检测是否在白名单 
            rt_code = util.allowlist(gid)
            if rt_code == 'not in' or rt_code == 'no_check_auth':
                util.log(f'群{gid}人数超过设定值, 当前人数{gnums[gid]}, 白名单状态{rt_code}', 'number_check')
                if group_id == 0:
                    # 检查全部群的情况, 可以自动退出
                    if config.AUTO_LEAVE:
                        await util.gun_group(group_id=gid, reason='群人数超过管理员设定的最大值')
                    else:
                        await util.notify_group(group_id=gid, txt='群人数超过管理员设定的最大值, 请联系管理员')
                else:
                    # 检查单个群的情况, 只通知而不自动退出, 等到下次计划任务时再退出
                    await util.notify_group(group_id=gid, txt='群人数超过管理员设定的最大值, 请联系管理员')
                    return 'overflow'
    return None