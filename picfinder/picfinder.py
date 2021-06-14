import re
import salmon
from salmon import Service, Bot
from salmon.configs import picfinder
from salmon.util import DailyNumberLimiter
from salmon.service import add_header
from salmon.typing import CQEvent, T_State, GroupMessageEvent, PrivateMessageEvent, Message
from salmon.configs.picfinder import threshold, SAUCENAO_KEY, CHAIN_REPLY, DAILY_LIMIT
from salmon.modules.picfinder.image import get_image_data_sauce, get_image_data_ascii


helptext='''
[搜图] 单张/多张搜图
'''.strip()

sv = Service('picfinder', help_=helptext)

lmtd = DailyNumberLimiter(DAILY_LIMIT)

picfind = sv.on_prefix('搜图', aliases={'识图', '查图', '找图'}, only_group=False)

@picfind.handle()
async def pic_rec(bot: Bot, event: CQEvent, state: T_State):
    uid = event.user_id
    if not lmtd.check(uid):
        await picfind.finish(f'您今天已经搜过{DAILY_LIMIT}次图了，休息一下明天再来吧~', call_header=True)
    args = str(event.message).strip()
    if args:
        state['pic'] = args
    message = await add_header(bot, event, msg='请发送需要搜索的图片~\n如果不需要搜图请发送“算了”或“不用了”:)')
    state['prompt'] = message

@picfind.got('pic', prompt='{prompt}')
async def pic_finder(bot: Bot, event: CQEvent, state: T_State):
    pic = state['pic']
    if pic in ('算了', '不用了'):
        await picfind.finish('我明白了~')
    ret = re.findall(r'url=(.*?)]', pic)
    if not ret:
        return
    await picfind.send('正在搜索，请稍候～', call_header=True)
    for url in ret:
        await picfinder(bot, event, url)


async def chain_reply(bot, event, chain, msg):
    if isinstance(event, PrivateMessageEvent):
        await bot.send(event, Message(msg))
        return chain
    elif not CHAIN_REPLY:
        await bot.send(event, msg)
        return chain
    else:
        data ={
                "type": "node",
                "data": {
                    "name": '小冰',
                    "uin": '2854196306',
                    "content": str(msg)
                        }
            }
        chain.append(data)
        return chain

    
async def picfinder(bot, event, image_data):
    uid = event.user_id
    chain=[]
    result = await get_image_data_sauce(image_data, SAUCENAO_KEY)
    image_data_report = result[0]
    simimax = result[1]
    if 'Index #' in image_data_report:
        await bot.send_private_msg(self_id=event.self_id, user_id=bot.config.SUPERUSERS[0], message='发生index解析错误')
        await bot.send_private_msg(self_id=event.self_id, user_id=bot.config.SUPERUSERS[0], message=image_data)
        await bot.send_private_msg(self_id=event.self_id, user_id=bot.config.SUPERUSERS[0], message=image_data_report)
    chain = await chain_reply(bot, event, chain, image_data_report)
    if float(simimax) > float(threshold):
        lmtd.increase(uid)
    else:
        if simimax != 0:
            chain = await chain_reply(bot, event, chain, "相似度过低，换用ascii2d检索中…")
        else:
            salmon.logger.error("SauceNao not found imageInfo")
            chain = await chain_reply(bot, event, chain, 'SauceNao检索失败,换用ascii2d检索中…')
        image_data_report = await get_image_data_ascii(image_data)
        if image_data_report[0]:
            chain = await chain_reply(bot, event, chain, image_data_report[0])
            lmtd.increase(uid)
        if image_data_report[1]:
            chain = await chain_reply(bot, event, chain, image_data_report[1])
        if not (image_data_report[0] or image_data_report[1]):
            salmon.logger.error("ascii2d not found imageInfo")
            chain = await chain_reply(bot, event, chain, 'ascii2d检索失败…')
    if isinstance(event, GroupMessageEvent):
        if CHAIN_REPLY:
            await bot.send_group_forward_msg(group_id=event.group_id, messages=chain)