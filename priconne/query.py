from operator import add
import os
import numpy as np
import salmon
from salmon import Service, Bot, R, scheduler, aiohttpx, priv
from salmon.util import FreqLimiter
from salmon.service import add_header
from salmon.typing import CQEvent, T_State, Message
from salmon.modules.priconne.pcr_data import chara
try:
    import ujson as json
except:
    import json


lmt = FreqLimiter(5)

this_season = np.zeros(15001, dtype=int)
all_season = np.zeros(15001, dtype=int)

this_season[1:11] = 50
this_season[11:101] = 10
this_season[101:201] = 5
this_season[201:501] = 3
this_season[501:1001] = 2
this_season[1001:2001] = 2
this_season[2001:4000] = 1
this_season[4000:8000:100] = 50
this_season[8100:15001:100] = 15

all_season[1:11] = 500
all_season[11:101] = 50
all_season[101:201] = 30
all_season[201:501] = 10
all_season[501:1001] = 5
all_season[1001:2001] = 3
all_season[2001:4001] = 2
all_season[4001:7999] = 1
all_season[8100:15001:100] = 30


server_addr = "https://pcresource.coldthunder11.com/rank/"
resize_pic = False
config = None


YUKARI_SHEET = Message(f'''{R.img('priconne/quick/黄骑充电.jpg').cqcode}
※大圈是1动充电对象 PvP测试
※黄骑四号位例外较多
※对面羊驼或中后卫坦 有可能歪
※我方羊驼算一号位
※图片搬运自漪夢奈特''')


sv_help = '''
[日/台/陆rank] rank推荐表
[查看当前/全部rank更新源]
[设置rank更新源]
[更新rank表缓存]
[挖矿15001] 矿场余钻
[黄骑充电表] 黄骑1动规律
[谁是霸瞳] 角色别称查询
'''.strip()

sv = Service('pcr-query', help_=sv_help, bundle='pcr查询')

miner = sv.on_prefix('挖矿', aliases={'jjc钻石', '竞技场钻石', 'jjc钻石查询', '竞技场钻石查询'}, only_group=False)
rank = sv.on_rex(r'^(\*?([日台国陆b])服?([前中后]*)卫?)?rank(表|推荐|指南)?$', only_group=False)
current_source = sv.on_fullmatch('查看当前rank更新源', only_group=False)
all_source = sv.on_fullmatch('查看全部rank更新源', only_group=False)
set_source = sv.on_rex(r'^设置rank更新源 (.{0,5}) (.{0,10}) (.{0,20})$', only_group=False)
cache_update = sv.on_fullmatch('更新rank表缓存', only_group=False)
yukari = sv.on_fullmatch(('yukari-sheet', '黄骑充电', '酒鬼充电', '酒鬼充电表', '黄骑充电表'), only_group=False)
who_is = sv.on_prefix('谁是', only_group=False)


async def load_config():
    global config
    global server_addr
    config_path = os.path.join(os.path.dirname(__file__), "rank.json")
    with open(config_path, "r", encoding="utf8") as fp:
        config = json.load(fp)
        server_addr = config['upstream']
        resize_pic = config['resize_pic']
    if not os.path.exists(os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache")):
        os.mkdir(os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache"))
    if not os.path.exists(os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache", "pic")):
        os.mkdir(os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache", "pic"))
        await update_cache()


def save_config():
    config_path = os.path.join(os.path.dirname(__file__), "rank.json")
    with open(config_path, 'r+', encoding='utf8') as fp:
        fp.seek(0)
        fp.truncate()
        str = json.dumps(config, indent=4, ensure_ascii=False)
        fp.write(str)


async def download_rank_pic(url):
    salmon.logger.info(f"正在下载{url}")
    resp = await aiohttpx.head(url)
    content_length = int(resp.headers["Content-Length"])
    salmon.logger.info(f"块大小{str(content_length)}")
    #分割200kb下载
    block_size = 1024*200
    range_list = []
    current_start_bytes = 0
    while True:
        if current_start_bytes + block_size >= content_length:
            range_list.append(f"{str(current_start_bytes)}-{str(content_length)}")
            break
        range_list.append(f"{str(current_start_bytes)}-{str(current_start_bytes + block_size)}")
        current_start_bytes += block_size + 1
    pic_bytes_list = []
    for block in range_list:
        salmon.logger.info(f"正在下载块{block}")
        headers = {"Range": f"bytes={block}"}
        resp = await aiohttpx.get(url, headers=headers)
        res_content = resp.content
        pic_bytes_list.append(res_content)
    return b"".join(pic_bytes_list)


async def update_rank_pic_cache(force_update:bool):
    config_names = ["cn", "tw", "jp"]
    for conf_name in config_names:
        config_path = os.path.join(os.path.dirname(__file__), "cache", f"{conf_name}.json")
        with open(config_path, "r", encoding="utf8") as fp:
            rank_config = json.load(fp)
        for img_name in rank_config["files"]:
            if not force_update:
                if os.path.exists(os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache", "pic", f"{conf_name}_{img_name}")):
                    continue
            rank_img_url = f"{server_addr}{config['source'][conf_name]['channel']}/{config['source'][conf_name]['route']}/{img_name}"
            img_content = await download_rank_pic(rank_img_url)
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache", "pic", f"{conf_name}_{img_name}"), "ab") as fp:
                fp.seek(0)
                fp.truncate()
                fp.write(img_content)


async def update_cache(force_update:bool=False):
    salmon.logger.info("正在更新Rank表缓存")
    config_names = ["cn","tw","jp"]
    for conf_name in config_names:
        resp = await aiohttpx.get(f"{server_addr}{config['source'][conf_name]['channel']}/{config['source'][conf_name]['route']}/config.json")
        res = resp.text
        cache_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache", f"{conf_name}.json")
        with open(cache_path, "a", encoding="utf8") as fp:
            fp.seek(0)
            fp.truncate()
            fp.write(res)
    await update_rank_pic_cache(force_update)
    salmon.logger.info("Rank表缓存更新完毕")


@miner.handle()
async def miner_rec(bot: Bot, event: CQEvent, state: T_State):
    state['prompt'] = await add_header(bot, event, msg='请发送当前竞技场排名')
    try:
        args = int(event.message.extract_plain_text())
        if args:
            state['rank'] = args
    except:
        pass

@miner.got('rank', prompt='{prompt}')
async def arena_miner(bot: Bot, event: CQEvent, state: T_State):
    rank = int(state['rank'])
    rank = np.clip(rank, 1, 15001)
    s_all = all_season[1:rank].sum()
    s_this = this_season[1:rank].sum()
    if 1 <= rank <= 15001:
      lst=[str(rank)+"→"]
      for _ in range(40):
       if 70 < rank <= 15001:
         rank = 0.85 * rank
         rank = int(rank // 1)
         lst.append(str(rank)+"→")
       elif 10 < rank <= 70:
         rank = int(rank - 10)
         lst.append(str(rank)+'→')
       elif 0 < rank <= 10:
         lst.append(1)
         break
    else:
        msg3 = "请输入15001以内的正整数"
        await miner.finish(msg3, call_header=True)
    msg1 = f"最高排名奖励还剩{s_this}钻\n历届最高排名还剩{s_all}钻\n推荐挖矿路径:\n"
    msg2 = ''.join('%s' %id for id in lst)
    await miner.send(msg1 + msg2, call_header=True)


@rank.handle()
async def rank_sheet(bot: Bot, event: CQEvent, state: T_State):
    if config == None:
        await load_config()
    match = state['match']
    is_jp = match.group(2) == "日"
    is_tw = match.group(2) == "台"
    is_cn = match.group(2) and match.group(2) in "国陆b"
    if not is_jp and not is_tw and not is_cn:
        await rank.finish("请问您要查询哪个区服的rank表？\n*日rank表\n*台rank表\n*陆rank表", call_header=True)
    msg = []
    if is_jp:
        rank_config_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache", "jp.json")
        rank_config = None
        with open(rank_config_path, "r", encoding="utf8") as fp:
            rank_config = json.load(fp)
        rank_imgs = []
        for img_name in rank_config["files"]:
            rank_imgs.append(f'file:///{os.path.join(os.path.dirname(__file__), "cache", "pic", f"jp_{img_name}")}')
        msg.append(rank_config["notice"])
        pos = match.group(3)
        if not pos or "前" in pos:
            msg.append(f"[CQ:image,file={rank_imgs[0]}]")
        if not pos or "中" in pos:
            msg.append(f"[CQ:image,file={rank_imgs[1]}]")
        if not pos or "后" in pos:
            msg.append(f"[CQ:image,file={rank_imgs[2]}]")
        await rank.send(Message("".join(msg)), call_header=True)
    elif is_tw:
        rank_config_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache", "tw.json")
        rank_config = None
        with open(rank_config_path, "r", encoding="utf8") as fp:
            rank_config = json.load(fp)
        rank_imgs = []
        for img_name in rank_config["files"]:
            rank_imgs.append(f'file:///{os.path.join(os.path.dirname(__file__), "cache", "pic", f"tw_{img_name}")}')
        msg.append(rank_config["notice"])
        for rank_img in rank_imgs:
            msg.append(f"[CQ:image,file={rank_img}]")
        await rank.send(Message("".join(msg)), call_header=True)
    elif is_cn:
        rank_config_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),"cache","cn.json")
        rank_config = None
        with open(rank_config_path, "r", encoding="utf8") as fp:
            rank_config = json.load(fp)
        rank_imgs = []
        for img_name in rank_config["files"]:
            rank_imgs.append(f'file:///{os.path.join(os.path.dirname(__file__), "cache", "pic", f"cn_{img_name}")}')
        msg.append(rank_config["notice"])
        for rank_img in rank_imgs:
            msg.append(f"[CQ:image,file={rank_img}]")
        await rank.send(Message("".join(msg)), call_header=True)


@current_source.handle()
async def show_current_rank_source(bot: Bot, event: CQEvent):
    if config == None:
        await load_config()
    if not priv.check_priv(event, priv.SUPERUSER):
        await current_source.finish("Insufficient authority.")
    msg = []
    msg.append("国服:\n")
    msg.append(config["source"]["cn"]["name"])
    msg.append("   ")
    if config["source"]["cn"]["channel"] == "stable":
        msg.append("稳定源")
    elif config["source"]["cn"]["channel"] == "auto_update":
        msg.append("自动更新源")
    else:
        msg.append(config["source"]["cn"]["channel"])
    msg.append("\n台服:\n")
    msg.append(config["source"]["tw"]["name"])
    msg.append("   ")
    if config["source"]["tw"]["channel"] == "stable":
        msg.append("稳定源")
    elif config["source"]["tw"]["channel"] == "auto_update":
        msg.append("自动更新源")
    else:
        msg.append(config["source"]["tw"]["channel"])
    msg.append("\n日服:\n")
    msg.append(config["source"]["jp"]["name"])
    msg.append("   ")
    if config["source"]["jp"]["channel"] == "stable":
        msg.append("稳定源")
    elif config["source"]["jp"]["channel"] == "auto_update":
        msg.append("自动更新源")
    else:
        msg.append(config["source"]["jp"]["channel"])
    await current_source.send("".join(msg), call_header=True)


@all_source.handle()
async def show_all_rank_source(bot: Bot, event: CQEvent):
    if config == None:
        await load_config()
    if not priv.check_priv(event, priv.SUPERUSER):
        await all_source.finish("Insufficient authority.")
    resp = await aiohttpx.get(server_addr + "route.json")
    res = resp.json()
    msg = []
    msg.append("稳定源：\n国服:\n")
    for uo in res["ranks"]["channels"]["stable"]["cn"]:
        msg.append(uo["name"])
        msg.append("   ")
    msg.append("\n台服:\n") 
    for uo in res["ranks"]["channels"]["stable"]["tw"]:
        msg.append(uo["name"])
        msg.append("   ")
    msg.append("\n日服:\n") 
    for uo in res["ranks"]["channels"]["stable"]["jp"]:
        msg.append(uo["name"])
        msg.append("   ")
    msg.append("\n自动更新源：\n国服:\n")
    for uo in res["ranks"]["channels"]["auto_update"]["cn"]:
        msg.append(uo["name"])
        msg.append("   ")
    msg.append("\n台服:\n") 
    for uo in res["ranks"]["channels"]["auto_update"]["tw"]:
        msg.append(uo["name"])
        msg.append("   ")
    msg.append("\n日服:\n") 
    for uo in res["ranks"]["channels"]["auto_update"]["jp"]:
        msg.append(uo["name"])
        msg.append("   ")
    msg.append("\n※如需修改更新源，请使用以下命令\n[设置rank更新源 国/台/日 稳定/自动更新 源名称]") 
    await all_source.send("".join(msg), call_header=True)


@set_source.handle()
async def set_rank(bot: Bot, event: CQEvent, state: T_State):
    if config == None:
        await load_config()
    if not priv.check_priv(event, priv.SUPERUSER):
        await all_source.finish("Insufficient authority.")
    robj = state["match"]
    server = robj.group(1)
    channel = robj.group(2)
    name = robj.group(3)
    if server == "国":
        server = "cn"
    elif server == "台":
        server = "tw"
    elif server == "日":
        server = "jp"
    else :
        await set_source.finish('请选择正确的区服(国/台/日)', call_header=True)
    if channel == "稳定":
        channel = "stable"
    elif channel == "自动更新":
        channel = "auto_update"
    else :
        await set_source.finish('请选择正确的频道(稳定/自动更新)', call_header=True)
    resp = await aiohttpx.get(server_addr + 'route.json')
    res = resp.json()
    has_name = False
    source_jo = None
    for uo in res["ranks"]["channels"][channel][server]:
        if uo["name"].upper() == name.upper():
            has_name = True
            source_jo = uo
            break
    if not has_name:
        await set_source.finish('请输入正确的源名称', call_header=True)
    config['source'][server]['name'] = source_jo['name']
    config['source'][server]['channel'] = channel
    config['source'][server]['route'] = source_jo['route']
    save_config()
    await update_cache(True)
    await set_source.send('更新源设置成功', call_header=True)


@cache_update.handle()
async def update_rank_cache(bot: Bot, event: CQEvent):
    if config == None:
        await load_config()
    if not priv.check_priv(event, priv.SUPERUSER):
        await cache_update.finish("Insufficient authority.")
    await update_cache()
    await bot.send(event, "更新成功")


@yukari.handle()
async def yukari_sheet(bot: Bot, event: CQEvent):
    await yukari.send(YUKARI_SHEET, call_header=True)

    
@who_is.handle()
async def whois(bot: Bot, event: CQEvent):
    name = event.get_plaintext().strip()
    if not name:
        return
    id_ = chara.name2id(name)
    confi = 100
    guess = False
    if id_ == chara.UNKNOWN:
        id_, guess_name, confi = chara.guess_id(name)
        guess = True
    c = chara.fromid(id_)
    if confi < 60:
        return
    uid = event.user_id
    if not lmt.check(uid):
        await who_is.finish(f'兰德索尔花名册冷却中(剩余 {int(lmt.left_time(uid)) + 1}秒)', call_header=True)
    lmt.start_cd(uid, 120 if guess else 0)
    if guess:
        msg = f'兰德索尔似乎没有叫"{name}"的人...\n角色别称补全计划: github.com/Ice-Cirno/HoshinoBot/issues/5\n您有{confi}%的可能在找{guess_name} {c.icon.cqcode} {c.name}'
        await who_is.send(Message(msg), call_header=True)
    else:
        msg = f'{c.icon.cqcode} {c.name}'
        await who_is.finish(Message(msg), call_header=True)


@scheduler.scheduled_job('cron', id='Rank更新', hour='17', minute='45')
async def schedule_update_rank_cache():
    if config == None:
        await load_config()
    await update_cache()