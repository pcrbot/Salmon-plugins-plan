from salmon.modules.authMS.group import check_auth
import pytz
import datetime
from salmon import scheduler
from salmon.modules.authMS.constant import config
from salmon.modules.authMS.group import check_auth


tz = pytz.timezone('Asia/Shanghai')


@scheduler.scheduled_job('cron', id='授权检查', hour='*', minute='02')
async def check_auth_sdj():
    now = datetime.datetime.now(tz)
    hour_now = now.hour
    if hour_now % config.FREQUENCY != 0:
        return
    if not config.ENABLE_AUTH:
        return
    await check_auth()