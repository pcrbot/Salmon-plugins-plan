import salmon
from salmon import Bot, Service, priv, scheduler
from salmon.typing import CQEvent
from salmon.modules.check.check import Check


sv = Service('check', use_priv=priv.SUPERUSER, manage_priv=priv.SUPERUSER, visible=False)

MAX_PERFORMANCE_PERCENT = salmon.configs.check.MAX_PERFORMANCE_PERCENT
PROCESS_NAME_LIST = salmon.configs.check.PROCESS_NAME_LIST
check = Check(salmon.configs.check.PROCESS_NAME_LIST)

check_self = sv.on_fullmatch(('自检', '自檢', '自我检查', '自我檢查'), only_group=False)

@check_self.handle()
async def _(bot: Bot, event: CQEvent):
    check_report_admin = await check.get_check_info()
    if check_report_admin:
        await bot.send(event, check_report_admin)
    else:
        salmon.logger.error("Not found Check Report")
        await bot.send(event, "[ERROR]Not found Check Report")


@scheduler.scheduled_job('cron', id='自我检查', hour='*/3', minute='13')
async def check_task():
    weihu = salmon.configs.SUPERUSERS[0]
    result = await check.get_check_easy()
    for bot in salmon.get_bot_list():
        await bot.send_private_msg(user_id=weihu, message=result)