import asyncio
import traceback
import salmon
from salmon import Service, scheduler, Bot, util, priv
from salmon.service import add_header
from salmon.typing import CQEvent, PrivateMessageEvent, GroupMessageEvent, T_State, Message
from salmon.modules.setu_hina.base import get_spec_image, get_setu, search_setu, check_path
from salmon.modules.setu_hina.lolicon import get_config, get_group_config, set_group_config, lolicon_fetch_process


HELP_MSG = '''
来张 [keyword] 涩/色/瑟图 : 来张keyword的涩图(不指定关键字发送一张随机涩图)
提取图片pid ： 获取指定id的p站图片，没有时发送链接
'''
sv = Service('setu', bundle='娱乐', help_=HELP_MSG)

# 设置limiter
tlmt = util.DailyNumberLimiter(get_config('base', 'daily_max'))
flmt = util.FreqLimiter(get_config('base', 'freq_limit'))

set_conf = sv.on_prefix('setu', only_group=False)
setu = sv.on_rex(r'^[色涩瑟][图圖]$|^[来來发發给給]((?P<num>\d+)|(?:.*))[张張个個幅点點份丶](?P<keyword>.*?)[色涩瑟][图圖]$', only_group=False)
get_pic = sv.on_prefix('提取图片', only_group=False)

def check_lmt(uid, num):
	if uid in salmon.configs.SUPERUSERS:
		return 0, ''
	if not tlmt.check(uid):
		return 1, f"您今天已经冲过{get_config('base', 'daily_max')}次了,请明天再来~"
	if num > 1 and (get_config('base', 'daily_max') - tlmt.get_num(uid)) < num:
		return 1, f"您今天的剩余次数为{get_config('base', 'daily_max') - tlmt.get_num(uid)}次,已不足{num}次,请注意节制哦~"
	if not flmt.check(uid):
		return 1, f'您冲的太快了,{round(flmt.left_time(uid))}秒后再来吧~'
	# tlmt.increase(uid,num)
	flmt.start_cd(uid)
	return 0, ''


def render_forward_msg(msg_list: list, uid=2854196306, name='小冰'):
	forward_msg = []
	for msg in msg_list:
		forward_msg.append({
			"type": "node",
			"data": {
				"name": str(name),
				"uin": str(uid),
				"content": msg
			}
		})
	return forward_msg


async def send_msg(msg_list, bot, event):
	result_list = []
	if not get_config('base', 'enable_forward_msg') or isinstance(event, PrivateMessageEvent):
		for msg in msg_list:
			try:
				result_list.append(await bot.send(event, Message(msg)))
			except:
				salmon.logger.error('图片发送失败')
				await bot.send(event, '涩图太涩,发不出去力...')
			await asyncio.sleep(1)
		return result_list
	else:
		forward_msg = render_forward_msg(msg_list)
		try:
			await bot.send_group_forward_msg(group_id=event.group_id, messages=forward_msg)
		except:
			traceback.print_exc()
			salmon.logger.error('图片发送失败')
			await bot.send(event, '涩图太涩,发不出去力...')
		await asyncio.sleep(1)
		return list(range(len(msg_list)))


@set_conf.handle()
async def group_set(bot: Bot, event: CQEvent):
    if isinstance(event, GroupMessageEvent):
        gid = event.group_id
    is_su = priv.check_priv(event, priv.SUPERUSER)
    args = util.normalize_str(event.get_plaintext()).split()
    msg = ''
    if not is_su:
        msg = '权限不足'
    elif len(args) == 0:
        msg = '请后接参数(空格隔开)\n支持的指令如下：\n[setu set r18/withdraw on/off (group_id)]\n[setu status (group_id)]\n[setu fetch]\n[setu warehouse]'
    elif args[0] == 'set' and len(args) >= 3:
        if len(args) >= 4 and args[3].isdigit():
            gid = int(args[3])
        elif args[1] == 'r18':
            key = 'lolicon_r18'
        elif args[1] == 'withdraw':
            key = 'withdraw'
        else:
            key = None
        if args[2] == 'on' or args[2] == '启用':
            value = True
        elif args[2] == 'off' or args[2] == '禁用':
            value = False
        elif args[2].isdigit():
            value = int(args[2])
        else:
            value = None
        if key and (not value is None):
            set_group_config(gid, key, value)
            msg = '设置成功！当前设置值如下:\n'
            msg += f'群/{gid} : 设置项/{key} = 值/{value}'
        else:
            msg = '无效参数\n支持的指令如下：\n[setu set r18/withdraw on/off (group_id)]\n[setu status (group_id)]\n[setu fetch]\n[setu warehouse]'
    elif args[0] == 'status':
        if len(args) >= 2 and args[1].isdigit():
            gid = int(args[1])
        withdraw_status = "Off" if get_group_config(
            gid, "withdraw") == 0 else f'{get_group_config(gid, "withdraw")}s'
        lolicon_status = "R18" if get_group_config(
            gid, "lolicon_r18") else "Normal"
        msg = f'Group: {gid} :'
        msg += f'\nWithdraw: {withdraw_status}'
        msg += f'\nSetu: {lolicon_status}'
    elif args[0] == 'fetch':
        await bot.send(event, '开始缓存图片')
        await lolicon_fetch_process()
        msg = '缓存进程结束'
    elif args[0] == 'warehouse':
        msg = 'Warehouse:'
        state = check_path()
        for k, v in state.items():
            msg += f'\n{k} : {v}'
    else:
        msg = '无效参数\n支持的指令如下：\n[setu set r18/withdraw on/off (group_id)]\n[setu status (group_id)]\n[setu fetch]\n[setu warehouse]'
    await bot.send(event, msg)


@setu.handle()
async def send_search_setu(bot: Bot, event: CQEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        gid = event.group_id
    elif isinstance(event, PrivateMessageEvent):
        gid = int(1128254624)
    uid = event.user_id
    match = state['match']
    num = match.group('num')
    if num:
        try:
            num = int(num)
            max_num = int(get_config('base', 'max_pic_once_send'))
            if num > max_num:
                await bot.send(event, f'一次只能要{max_num}份setu哦~')
                num = max_num
            else:
                pass
        except:
            num = 1
    else:
        num = 1
    result, msg = check_lmt(uid, num)
    if result != 0:
        await setu.finish(msg, call_header=True)
    keyword = match.group('keyword')
    result_list = []
    msg_list = []
    if not keyword:
        for _ in range(num):
            msg = await get_setu(gid)
            if msg == None:
                await setu.finish('获取图片失败，可能有以下原因：\n网络不佳/配置有误\n初始化未使用[setu fetch]指令')
            msg_list.append(msg)
        result_list = await send_msg(msg_list, bot, event)
    else:
        keyword = keyword.strip()
        await bot.send(event, '搜索中...')
        msg_list = await search_setu(gid, keyword, num)
        if len(msg_list) == 0:
            await bot.send(event, '未找到指定TAG，将随机发送')
            for _ in range(num):
                msg = await get_setu(gid)
                if msg == None:
                    await bot.send(event, '获取图片失败，可能有以下原因：\n网络不佳/配置有误\n初始化未使用[setu fetch]指令')
                msg_list.append(msg)
            result_list = await send_msg(msg_list, bot, event)
        else:
            result_list = await send_msg(msg_list, bot, event)
    tlmt.increase(uid, len(result_list))
    second = get_group_config(gid, "withdraw")
    if second and second > 0:
        if not get_config('base', 'enable_forward_msg'):
            await asyncio.sleep(second)
            for result in result_list:
                try:
                    await bot.delete_msg(message_id=result['message_id'])
                except:
                    traceback.print_exc()
                    salmon.logger.error('setu撤回失败')
                await asyncio.sleep(1)


@get_pic.handle()
async def get_spec_setu(bot: Bot, event: CQEvent, state: T_State):
    args = event.get_plaintext().split()
    if args:
        state['pid'] = args
    message = await add_header(bot, event, msg='请发送需要提取的图片的pid')
    state['prompt'] = message

@get_pic.got('pid', prompt='{prompt}')
async def get_spec_setu_res(bot: Bot, event: CQEvent, state: T_State):
    pid = state['pid']
    args = str(pid)
    if len(args) == 8:
        msg = get_spec_image(args)
        if not msg:
            await get_pic.send(f'没有在本地找到这张图片/不支持r18图片的提取\n请尝试此原图链接:\nhttps://pixiv.lancercmd.cc/{args}', call_header=True)
        else:
            await get_pic.send(Message(msg), call_header=True)
    else:
        await get_pic.send('Pid应为8位数字id哦~', call_header=True)


@scheduler.scheduled_job('interval', minutes=40)
async def fetch_setu_process():
    await lolicon_fetch_process()