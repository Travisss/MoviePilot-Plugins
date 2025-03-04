import time
from typing import Any, List, Dict, Tuple

from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType, NotificationType
from app.utils.http import RequestUtils


class WebHookMsg(_PluginBase):
    # 插件名称
    plugin_name = "自用webhook通知"
    # 插件描述
    plugin_desc = "支持使用webhook发送消息通知（自用版）"
    # 插件图标
    plugin_icon = "webhook.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "Travisss"
    # 作者主页
    author_url = "https://github.com/Travisss"
    # 插件配置项ID前缀
    plugin_config_prefix = "webhookmsg_"
    # 加载顺序
    plugin_order = 28
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _webhookurl = None
    _msgtypes = []

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._method = config.get('request_method')
            self._webhookurl = config.get("webhookurl")
            self._delay = config.get("delay") or 0
            self._msgtypes = config.get("msgtypes") or []

    def get_state(self) -> bool:
        return self._enabled and (True if self._webhookurl else False)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        # 编历 NotificationType 枚举，生成消息类型选项
        MsgTypeOptions = []
        for item in NotificationType:
            MsgTypeOptions.append({
                "title": item.value,
                "value": item.name
            })
        request_options = ["GET", "POST"]
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 2
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'request_method',
                                            'label': '请求方式',
                                            'items': request_options
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 10
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'webhookurl',
                                            'label': 'WebHook地址'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 2
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'delay',
                                            'label': '延迟时间（秒）',
                                            'placeholder': '0'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 10
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'multiple': True,
                                            'chips': True,
                                            'model': 'msgtypes',
                                            'label': '消息类型',
                                            'items': MsgTypeOptions
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                ]
            }
        ], {
            "enabled": False,
            "request_method": "GET",
            'webhookurl': '',
            "delay": 0,
            'msgtypes': []
        }

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(EventType.NoticeMessage)
    def send(self, event: Event):
        """
        消息发送事件
        """
        if not self.get_state():
            return

        if not event.event_data:
            return

        msg_body = event.event_data
        # 渠道
        channel = msg_body.get("channel")
        if channel:
            return
        # 类型
        msg_type: NotificationType = msg_body.get("type")
        # 标题
        title = msg_body.get("title")
        # 文本
        text = msg_body.get("text")
        # 图像
        image = msg_body.get("image")

        if not title and not text:
            logger.warn("标题和内容不能同时为空\n")
            return

        if (msg_type and self._msgtypes
                and msg_type.name not in self._msgtypes):
            logger.info(f"消息类型 {msg_type.value} 未开启消息发送\n")
            return

        # 延时发送通知
        if self._delay:
            logger.info(f"延迟 {self._delay} 秒后发送WebHook消息...")
            time.sleep(float(self._delay))

        payload = {
            "device": 'WebHookMsg',
            "title": title,
            "desp": text
        }
        try:
            logger.info(f"开始发送WebHook消息...")
            if self._method == 'POST':
                res = RequestUtils(content_type="application/json").post_res(self._webhookurl, json=payload)
            else:
                res = RequestUtils().get_res(self._webhookurl, params=payload)
            if res:
                logger.info(f"WebHook发送成功：request={self._method}, url={self._webhookurl}, title={title}, desp={text}\n")
            elif res is not None:
                logger.error(f"WebHook发送失败，状态码：{res.status_code}，返回信息：{res.text} {res.reason}\n")
            else:
                logger.error("WebHook发送失败，未获取到返回信息\n")
        except Exception as msg_e:
            logger.error(f"WebHook发送失败，{str(msg_e)}\n")

    def stop_service(self):
        """
        退出插件
        """
        pass
