import logging
import re
import os
import sys


sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


from app.scripts.GroupManager.group_management import *


from app.api import *
from app.config import owner_id

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "GroupManager",
)


# 是否是群主
def is_group_owner(role):
    return role == "owner"


# 是否是管理员
def is_group_admin(role):
    return role == "admin"


# 是否是管理员或群主或root管理员
def is_authorized(role, user_id):
    is_admin = is_group_admin(role)
    is_owner = is_group_owner(role)
    return (is_admin or is_owner) or (user_id in owner_id)


# 群管系统菜单
async def GroupManager(websocket, group_id, message_id):
    message = (
        f"[CQ:reply,id={message_id}]\n"
        + """
GroupManager 群管理系统

ban@ 时间 禁言x秒，默认60秒
unban@ 解除禁言
banme 随机禁言自己随机秒
banmerank 查看当日禁言排行
banrandom 随机禁言一个群友随机秒
banall 全员禁言
unbanall 全员解禁
t@ 踢出指定用户
del 撤回消息(需要回复要撤回的消息)
vc-on 开启视频监控
vc-off 关闭视频监控
wf-on 开启欢迎欢送
wf-off 关闭欢迎欢送
wf-set 设置欢迎词
"""
    )
    await send_group_msg(websocket, group_id, message)


async def handle_GroupManager_group_message(websocket, msg):
    try:
        user_id = str(msg["user_id"])
        group_id = str(msg["group_id"])
        raw_message = msg["raw_message"]
        # role = msg["sender"]["role"]
        role = str(msg.get("sender", {}).get("role", ""))
        message_id = str(msg["message_id"])
        self_id = str(msg.get("self_id", ""))  # 机器人QQ，转为字符串方便操作

        is_admin = is_group_admin(role)  # 是否是群管理员
        is_owner = is_group_owner(role)  # 是否是群主
        is_authorized = (is_admin or is_owner) or (
            user_id in owner_id
        )  # 是否是群主或管理员或root管理员

        if raw_message == "groupmanager" or raw_message == "群管":
            await GroupManager(websocket, group_id, message_id)
        if is_authorized and (raw_message == "测试" or raw_message == "test"):
            logging.info("收到管理员的测试消息。")
            if raw_message == "测试":
                await send_group_msg(
                    websocket, group_id, f"[CQ:reply,id={message_id}]测试成功"
                )
            elif raw_message == "test":
                await send_group_msg(
                    websocket, group_id, f"[CQ:reply,id={message_id}]Test successful"
                )

        if raw_message == "banall" and is_authorized:
            await set_group_whole_ban(websocket, group_id, True)
            return
        if raw_message == "unbanall" and is_authorized:
            await set_group_whole_ban(websocket, group_id, False)
            return

        if is_authorized and re.match(r"t.*", raw_message):
            kick_qq = None
            kick_qq = next(
                (item["data"]["qq"] for item in msg["message"] if item["type"] == "at"),
                None,
            )

            if kick_qq == self_id:
                await send_group_msg(
                    websocket, group_id, f"[CQ:reply,id={message_id}]踢我干什么！"
                )
                return

            if kick_qq:
                await set_group_kick(websocket, group_id, kick_qq)
                await send_group_msg(
                    websocket, group_id, f"[CQ:reply,id={message_id}]已踢出 {kick_qq}"
                )
        if re.match(r"ban.*", raw_message):

            # 指定禁言一个人
            if re.match(r"banyou.*", raw_message):

                await ban_somebody(
                    websocket, user_id, group_id, msg["message"], self_id
                )
                return

            # 禁言自己
            if raw_message == "banme" or raw_message == "禁言我":
                await banme_random_time(websocket, group_id, user_id, message_id)
                return

            # 查看禁言排行
            if raw_message == "banmerank":
                await banme_rank(websocket, group_id, message_id)
                return

            # 随机禁言
            if (
                raw_message == "banrandom" or raw_message == "随机禁言"
            ) and is_authorized:
                await ban_random_user(websocket, group_id, msg["message"])
                return

            # 禁言指定用户
            if (
                re.match(r"ban.*", raw_message) or re.match(r"禁言.*", raw_message)
            ) and is_authorized:

                await ban_user(websocket, group_id, msg["message"], self_id, user_id)

        # 解禁
        if (
            re.match(r"unban.*", raw_message) or re.match(r"解禁.*", raw_message)
        ) and is_authorized:
            await unban_user(websocket, group_id, msg["message"])

        # 撤回消息
        if "del" in raw_message and is_authorized:
            message_id = int(msg["message"][0]["data"]["id"])
            await delete_msg(websocket, message_id)

    except Exception as e:
        logging.error(f"处理群管理群消息时出错: {e}")
