import os
from sqlitedict import SqliteDict
import salmon


try:
    config = salmon.configs.authMS.auth_config
except:
    # 保不准哪个憨憨又不读README呢
    salmon.logger.error('未发现authMS配置文件!请仔细阅读README')


if salmon.configs.authMS.auth_config.ENABLE_COM:
    path_first = salmon.configs.authMS.auth_config.DB_PATH
else:
    path_first = ''


group_dict = SqliteDict(os.path.join(path_first, 'group.sqlite'), autocommit=True)
trial_list = SqliteDict(os.path.join(path_first, 'trial.sqlite'), autocommit=True)  # 试用列表