from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import FriendAddNoticeEvent
from nonebot.plugin import on_request
from nonebot.adapters.cqhttp import FriendRequestEvent
import salmon
from salmon import Bot
from salmon.modules.authMS import util
from salmon.modules.authMS.constant import config


friend_request = on_request()

@friend_request.handle()
async def friend_approve(bot: Bot, event: FriendRequestEvent):
    if config.FRIEND_APPROVE:
        util.log(f'已自动接受来自{event.user_id}的好友请求','friend_add')
        salmon.logger.info(f'已自动接受来自{event.user_id}的好友请求')
        await bot.set_friend_add_request(flag=event.flag, approve=True)
    else:
        util.log(f'收到来自{event.user_id}的好友请求','friend_add')
        salmon.logger.info(f'收到来自{event.user_id}的好友请求')