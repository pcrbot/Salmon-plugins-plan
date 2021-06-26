import io
import os
import random
import base64
from PIL import Image, ImageDraw
from salmon import R
from salmon.modules.setu_hina.lolicon import *


def check_path():
	state = {}
	sub_dirs = ['lolicon', 'lolicon_r18']
	for item in sub_dirs:
		res = R.img('setu/' + item)
		if not os.path.exists(res.path):
			os.makedirs(res.path)
		state[item] = len(os.listdir(res.path)) // 2
	return state


check_path()


def get_spec_image(id):
	image = get_setu_native(0, id)
	if not image:
		return None
	else:
		image = format_setu_msg(image)
		return image


def format_setu_msg(image):
	try:
		if image["title"]:
			try:
				im = Image.open(io.BytesIO(image["data"]))
			except:
				im = Image.open(image["data"])
			width, height = im.size
			draw = ImageDraw.Draw(im)
			draw.point((random.randint(1, width), random.randint(1, height)), fill=(random.randint(0, 255),
			                                                                        random.randint(0, 255),
			                                                                        random.randint(0, 255)))
			image["data"] = io.BytesIO()
			im.save(image["data"], format='JPEG')
			image["data"] = image["data"].getvalue()
			base64_str = f"base64://{base64.b64encode(image['data']).decode()}"
			msg = f'「{image["title"]}」\nAuthor: {image["author"]}\nPID:{image["id"]}\n[CQ:image,file={base64_str}]'
			return msg
		else:
			return None
	except TypeError:
		return None


async def get_setu(group_id):
	source_list = []
	if get_group_config(group_id, 'lolicon'):
		source_list.append(1)
	if get_group_config(group_id, 'lolicon_r18'):
		source_list.append(2)
	source = 0
	if len(source_list) > 0:
		source = random.choice(source_list)
	image = None
	if source == 1:
		image = await lolicon_get_setu(0)
	elif source == 2:
		image = await lolicon_get_setu(1)
	else:
		return None
	if not image:
		return '获取失败'
	elif image['id'] != 0:
		return format_setu_msg(image)
	else:
		return image['title']


async def search_setu(group_id, keyword, num):
	source_list = []
	if get_group_config(group_id, 'lolicon') and get_group_config(group_id, 'lolicon_r18'):
		source_list.append(2)
	elif get_group_config(group_id, 'lolicon'):
		source_list.append(0)
	elif get_group_config(group_id, 'lolicon_r18'):
		source_list.append(1)
	if len(source_list) == 0:
		return []
	image_list = None
	msg_list = []
	while len(source_list) > 0 and len(msg_list) == 0:
		source = source_list.pop(random.randint(0, len(source_list) - 1))
		if source == 0:
			image_list = await lolicon_search_setu(keyword, 0, num)
		elif source == 1:
			image_list = await lolicon_search_setu(keyword, 1, num)
		elif source == 2:
			image_list = await lolicon_search_setu(keyword, 2, num)
		if image_list and len(image_list) > 0:
			for image in image_list:
				msg_list.append(format_setu_msg(image))
	return msg_list


lolicon_init()