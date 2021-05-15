# Salmon-plugins-plan


一个适用于 [Salmonbot](https://github.com/Watanabe-Asa/SalmonBot) 的插件新建及迁移企画。

欢迎大家参与本项目！

## 使用方法

将所需插件文件夹置于路径`salmon/modules`下，并按照对应要求安装依赖或编辑配置，然后在文件`salmon/configs/__bot__.py`的`MODULES_ON`中添加插件名并重启 bot .

<details>
  <summary>picfinder</summary>

### 搜图功能

原项目导航> [picfinder](https://github.com/pcrbot/picfinder_take)

请将文件`picfinder.template.py`移动至路径`salmon/configs`下并重命名为`picfinder.py`，并按注释编辑配置。

</details>

<details>
  <summary>check</summary>

### 搜图功能

原项目导航> [check](https://github.com/pcrbot/Hoshino-plugin-transplant/tree/master/check)

请将文件`check.template.py`移动至路径`salmon/configs`下并重命名为`check.py`，并按注释编辑配置。然后安装依赖。

```python
pip3.9 install psutil
```

</details>

## 关于开源

本项目以 GPL-3.0 协议开源。