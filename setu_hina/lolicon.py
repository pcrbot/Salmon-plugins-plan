import io
import os
import random
import datetime
import aiohttp
import traceback
from PIL import Image
from traceback import format_exc
import salmon
from salmon import R
try:
    import ujson as json
except:
    import json


config_default = {
	"base": {
		"daily_max": 10,  # 每日上限次数
		"freq_limit": 30,  # 频率限制
		"max_pic_once_send": 1,  # 一次最大发送图片数量
		"enable_forward_msg": True  # 启用转发消息模式
	},
	"default": {
		"withdraw": 0,  # 撤回时间，单位秒
		"lolicon": True,  # 别动
		"lolicon_r18": False,  # lolicon_r18模块开关
	},
	"lolicon": {
		"mode": 2,  # 0禁用 1无缓存 2有缓存在线 3有缓存离线
		"r18": False,  # R18图开关
		"size_original": False,  # 原图开关
		"pixiv_direct": False,  # 是否直连pixiv
		"pixiv_proxy": "https://i.pixiv.cat",  # pixiv代理地址
		"lolicon_proxy": ""  # lolicon代理地址
	}
}

groupconfig_default = {}

# Check config if exist
pathcfg = os.path.join(os.path.dirname(__file__), 'config.json')
if not os.path.exists(pathcfg):
	try:
		with open(pathcfg, 'w') as cfgf:
			json.dump(config_default, cfgf, ensure_ascii=False, indent=2)
			salmon.logger.error('未找到配置文件，已根据默认配置模板创建，请打开插件目录内config.json查看和修改')
	except:
		salmon.logger.error('创建配置文件失败，请检查插件目录的读写权限及是否存在config.json')
		traceback.print_exc()


# check group config if exist
gpcfgpath = os.path.join(os.path.dirname(__file__), 'groupconfig.json')
if not os.path.exists(gpcfgpath):
	try:
		with open(gpcfgpath, 'w') as gpcfg:
			json.dump(groupconfig_default, gpcfg, ensure_ascii=False, indent=2)
			salmon.logger.error('未找到群设置文件，已创建')
	except:
		salmon.logger.error('创建群设置文件失败，请检查插件目录的读写权限')
		traceback.print_exc()


quota_limit_time = datetime.datetime.now()
cfgpath = os.path.join(os.path.dirname(__file__), 'config.json')
groupconfigpath = os.path.join(os.path.dirname(__file__), 'groupconfig.json')
group_config = {}
config = {}
config = json.load(open(cfgpath, 'r', encoding='utf8'))
group_config = json.load(open(groupconfigpath, 'r', encoding='utf8'))


def generate_image_struct():
	return {
		'id': 0,
		'url': '',
		'title': '',
		'author': '',
		'tags': [],
		'r18': False,
		'data': None,
		'native': False,
	}


native_info = {}
native_r18_info = {}


def get_config(key, sub_key):
	if key in config and sub_key in config[key]:
		return config[key][sub_key]
	return None


def get_group_config(group_id, key):
	group_id = str(group_id)
	if group_id not in group_config:
		return config['default'][key]
	if key in group_config[group_id]:
		return group_config[group_id][key]
	else:
		return None


def set_group_config(group_id, key, value):
	group_id = str(group_id)
	if group_id not in group_config:
		group_config[group_id] = {}
		for k, v in config['default'].items():
			group_config[group_id][k] = v
	group_config[group_id][key] = value
	try:
		with open(groupconfigpath, 'w', encoding='utf8') as f:
			json.dump(group_config, f, ensure_ascii=False, indent=2)
	except:
		traceback.print_exc()


async def get_group_info(group_ids=0, info_type='member_count'):
	"""
    1. 传入一个整型数字, 返回单个群指定信息, 格式为字典
    2. 传入一个list, 内含多个群号(int), 返回一个字典, 键为群号, 值为指定信息
    3. 不填入参数, 返回一个包含所有群号与指定信息的字典
    无论获取多少群信息, 均只有一次API的开销, 传入未加入的群时, 将自动忽略
    info_type支持group_id, group_name, max_member_count, member_count
    """
	group_info_all = await get_group_list_all()
	_gids = []
	_gnames = []
	# 获得的已加入群为列表形式, 处理为需要的字典形式
	for it in group_info_all:
		_gids.append(it['group_id'])
		_gnames.append(it[info_type])
	group_info_dir = dict(zip(_gids, _gnames))
	if group_ids == 0:
		return group_info_dir
	if type(group_ids) == int:
		# 转为列表
		group_ids = [group_ids]
		salmon.logger.error(group_ids)
	for key in list(group_info_dir.keys()):
		if key not in group_ids:
			del group_info_dir[key]
		else:
			# TODO: group not joined
			pass
	return group_info_dir


async def get_group_list_all():
	"""
    获取所有群, 返回为原始类型(列表)
    """
	for bot in salmon.get_bot_list():
		group_list = await bot.get_group_list()
	return group_list


def load_native_info(sub_dir):
	info = {}
	path = f'setu/' + sub_dir
	res = R.img(path)
	if not os.path.exists(res.path):
		return info
	fnlist = os.listdir(res.path)
	for fn in fnlist:
		s = fn.split('.')
		if len(s) != 2 or s[1] != 'json' or not s[0].isdigit():
			continue
		uid = int(s[0])
		try:
			with open(res.path + '/' + fn, encoding='utf8') as f:
				d = json.load(f)
				d['tags'].append(d['title'])
				d['tags'].append(d['author'])
				info[uid] = ','.join(d['tags'])
		except:
			pass
	salmon.logger.info(f'reading {len(info)} setu from {sub_dir}')
	return info


# 获取随机色图
async def query_setu(r18=0, keyword=None):
	global quota_limit_time
	image_list = []
	data = {}
	url = 'https://api.lolicon.app/setu/v2'
	params = {
		'r18': r18,
		'num': 1,
	}
	if keyword:
		params["tag"] = keyword
	if get_config('lolicon', 'size_original'):
		params['size'] = 'original'
	else:
		params['size'] = 'regular'
	size = params['size']
	if get_config('lolicon', 'pixiv_direct'):
		params['proxy'] = 'disable'
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params, proxy=get_config('lolicon', 'lolicon_proxy')) as resp:
				data = await resp.json(content_type='application/json')
	except Exception:
		traceback.print_exc()
		return
	if data['error']:
		salmon.logger.error(f'lolicon api error: {data["error"]}')
	for item in data['data']:
		image = generate_image_struct()
		image['id'] = item['pid']
		image['title'] = item['title']
		image['url'] = item['urls'][size]
		image['tags'] = item['tags']
		image['r18'] = item['r18']
		image['author'] = item['author']
		image_list.append(image)
	return image_list


async def download_image(url: str):
	salmon.logger.info(f'lolicon downloading image: {url}')
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get(url, proxy=get_config('lolicon', 'lolicon_proxy')) as resp:
				data = await resp.read()
				# 转jpg
				byte_stream = io.BytesIO(data)
				roiImg = Image.open(byte_stream)
				if roiImg.mode != 'RGB':
					roiImg = roiImg.convert('RGB')
				imgByteArr = io.BytesIO()
				roiImg.save(imgByteArr, format='JPEG')
				return imgByteArr.getvalue()
	except:
		salmon.logger.error('lolicon download image failed')
	# traceback.print_exc()
	return None


async def download_pixiv_image(url: str, id):
	salmon.logger.info('lolicon downloading pixiv image', url)
	headers = {
		'referer': f'https://www.pixiv.net/member_illust.php?mode=medium&illust_id={id}'
	}
	try:
		async with aiohttp.ClientSession(headers=headers) as session:
			async with session.get(url, proxy=get_config('lolicon', 'pixiv_proxy')) as resp:
				data = await resp.read()
				# 转jpg
				byte_stream = io.BytesIO(data)
				roiImg = Image.open(byte_stream)
				if roiImg.mode != 'RGB':
					roiImg = roiImg.convert('RGB')
				imgByteArr = io.BytesIO()
				roiImg.save(imgByteArr, format='JPEG')
				return imgByteArr.getvalue()
	except:
		salmon.logger.error('pixiv download image failed')
	# traceback.print_exc()
	return None


def save_image(image):
	path = f'setu/lolicon/{image["id"]}'
	if image['r18']:
		path = f'setu/lolicon_r18/{image["id"]}'
	res = R.img(path + '.jpg')
	with open(res.path, 'wb') as f:
		f.write(image['data'])
	res = R.img(path + '.json')
	info = {
		'title': image['title'],
		'author': image['author'],
		'url': image['url'],
		'tags': image['tags'],
	}
	with open(res.path, 'w', encoding='utf8') as f:
		json.dump(info, f, ensure_ascii=False, indent=2)


async def get_setu_online(num, r18=0, keyword=None):
	image_list = await query_setu(r18=r18, keyword=keyword)
	if image_list == None:
		return
	valid_list = []
	while len(image_list) > 0:
		image = image_list.pop(random.randint(0, len(image_list) - 1))
		# 检查本地是否存在该图片
		path = f'setu/lolicon/{image["id"]}.jpg'
		if image['r18']:
			path = f'setu/lolicon_r18/{image["id"]}.jpg'
		res = R.img(path)
		if os.path.exists(res.path):
			image['data'] = res.path
			image['native'] = True
		else:
			if get_config('lolicon', 'pixiv_direct'):
				image['data'] = await download_pixiv_image(image['url'], image['id'])
			else:
				image['data'] = await download_image(image['url'])
			image['native'] = False
			if image['data'] and get_config('lolicon', 'mode') == 2:
				save_image(image)
				image['data'] = res.path
		if image['data']:
			valid_list.append(image)
		if len(valid_list) >= num:
			break
	return valid_list


def get_setu_native(r18=0, uid=0):
	image = generate_image_struct()
	path = f'setu/lolicon'
	if r18 == 1:
		path = f'setu/lolicon_r18'
	elif r18 == 2:
		if random.randint(1, 100) > 50:
			path = f'setu/lolicon_r18'
	res = R.img(path)
	if not os.path.exists(res.path):
		return image
	if uid == 0:
		fn = random.choice(os.listdir(res.path))
		if fn.split('.')[0].isdigit():
			uid = int(fn.split('.')[0])
	if not uid:
		return image	
	image['id'] = int(uid)
	image['native'] = True
	path += f'/{uid}'
	res = R.img(path)
	try:
		image['data'] = res.path + '.jpg'
		with open(res.path + '.json', encoding='utf8') as f:
			d = json.load(f)
			if 'title' in d:
				image['title'] = d['title']
			if 'author' in d:
				image['author'] = d['author']
			if 'url' in d:
				image['url'] = d['url']
	except:
		pass	
	return image


def search_setu_native(keyword, r18, num):
	result_list = []
	if r18 == 0 or r18 == 2:
		for k, v in native_info.items():
			if v.find(keyword) >= 0:
				result_list.append({
					'uid': k,
					'r18': 0,
				})
	if r18 == 1 or r18 == 2:
		for k, v in native_r18_info.items():
			if v.find(keyword) >= 0:
				result_list.append({
					'uid': k,
					'r18': 1,
				})
	if len(result_list) > num:
		result_list = random.sample(result_list, num)
	image_list = []
	for result in result_list:
		image = get_setu_native(result['r18'], result['uid'])
		if image['data']:
			image_list.append(image)
	return image_list


# r18: 0 正常 1 r18 2 混合
async def lolicon_get_setu(r18):
	if get_config('lolicon', 'mode') >= 2:
		return get_setu_native(r18)
	elif get_config('lolicon', 'mode') == 1:
		image_list = await get_setu_online(1, r18)
		if len(image_list) > 0:
			return image_list[0]
		else:
			return None
	else:
		return None


# r18: 0 正常 1 r18 2 混合
async def lolicon_search_setu(keyword, r18, num):
	if get_config('lolicon', 'mode') == 1 or get_config('lolicon', 'mode') == 2:
		return await get_setu_online(num, r18, keyword)
	elif get_config('lolicon', 'mode') == 3:  # 离线模式
		return search_setu_native(keyword, r18, num)
	else:
		return None


async def lolicon_fetch_process():
	for _ in range(10):
		if get_config('lolicon', 'mode') == 2:
			salmon.logger.info('fetching lolicon setu')
			await get_setu_online(10, 0)
			if get_config('lolicon', 'r18'):
				salmon.logger.info('fetching lolicon r18 setu')
				await get_setu_online(10, 1)


def lolicon_init():
	global native_info
	global native_r18_info
	if get_config('lolicon', 'mode') == 3:
		native_info = load_native_info('lolicon')
		native_r18_info = load_native_info('lolicon_r18')


'''
class Lolicon:

    def __init__(self):
        pass

    async def get_setu(self):
        pass

    async def search_setu(self):
        pass

    async def get_ranking(self):
        pass

    async def get_ranking_setu(self):
        pass

    async def fetch_process(self):
        await lolicon_fetch_process()
'''