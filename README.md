# Salmon-plugins-plan


一个适用于 [Salmonbot](https://github.com/Watanabe-Asa/SalmonBot) 的插件新建及迁移企画。


## 使用方法

将所需插件文件夹置于路径`salmon/modules`下，并按照对应要求安装依赖或编辑配置，然后在文件`salmon/configs/__bot__.py`的`MODULES_ON`中添加插件名并重启 bot .

## 点击查看

<details>
  <summary> picfinder </summary>

### 搜图功能

原项目导航> [picfinder](https://github.com/pcrbot/picfinder_take)

请将文件`picfinder.template.py`移动至路径`salmon/configs`下并重命名为`picfinder.py`，并按注释编辑配置。

</details>

<details>
  <summary> check </summary>

### 自检

原项目导航> [check](https://github.com/pcrbot/Hoshino-plugin-transplant/tree/master/check)

1.请将文件`check.template.py`移动至路径`salmon/configs`下并重命名为`check.py`，并按注释编辑配置。

2.安装依赖 psutil

```python
pip3.9 install psutil
```

</details>

<details>
  <summary> gacha / rank </summary>

### PCR自动更新卡池

原项目导航> [gacha](https://github.com/pcrbot/gacha)

请将文件`update.py`放至路径`salmon/modules/priconne`下。

### PCR自动更新rank表

原项目导航> [pcr-rank](https://github.com/ColdThunder11/pcr-rank)

请将文件`rank.json`放至路径`salmon/modules/priconne`下，并替换同名文件`query.py`。

</details>

<details>
  <summary> authMS </summary>

### 授权功能

原项目导航> [authMS](https://github.com/pcrbot/authMS)

> 数据库与原授权插件数据互通，故支持双开或直接迁移。
> 
> 去除部分功能而保留了核心功能，部署完成后私聊发送`管理员帮助`可查看相关指令。

1.请将文件`filter.json`放至 go-cqhttp 运行目录下。

2.将文件`authMS.template.py`移动至路径`salmon/configs`下并重命名为`authMS.py`，并按注释编辑配置。

3.安装依赖 sqlitedict

```python
pip3.9 install sqlitedict
```

</details>

<details>
  <summary> setu_hina </summary>

### setu插件

原项目导航> [setu_renew](https://github.com/pcrbot/setu_renew)

> 初次使用请发送`setu fetch`指令缓存图片。

</details>

## 关于开源

本项目以 GPL-3.0 协议开源。