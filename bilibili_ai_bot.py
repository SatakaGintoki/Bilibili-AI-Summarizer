import os
import re
import asyncio
import httpx
from openai import AsyncOpenAI
from bilibili_api import Credential, session, video
from bilibili_api.comment import CommentResourceType, send_comment 

# ================= 1. 配置区 =================
# ⚠️ 警告：请不要将真实的密钥上传到公开网络！
SESSDATA = "请在这里填写你的 SESSDATA"
BILI_JCT = "请在这里填写你的 BILI_JCT"
UID = 123456789  # 请在这里填写你的真实数字 UID

credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)

AI_API_KEY = "请在这里填写你的大模型 API_KEY"
AI_BASE_URL = "https://ark.cn-beijing.volces.com/api/coding/v3" 
# =============================================
ai_client = AsyncOpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
# =============================================

# 🚀 武器 1：高容错版的精华提取器
def extract_for_comment(full_text):
    try:
        # 1. 过滤掉深度思考模型可能生成的 <think> 过程
        text_clean = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL).strip()
        
        # 2. 使用极度宽容的正则：只要包含关键汉字，无视前面的 Emoji 和 Markdown 符号
        tldr_match = re.search(r'一句话总结.*?[:：]\s*(.*?)(?=\n.*?核心要点)', text_clean, re.DOTALL)
        points_match = re.search(r'核心要点.*?[:：]\s*(.*?)(?=\n.*?内容脉络)', text_clean, re.DOTALL)
        
        # 3. 如果提取到了，就去除首尾空格；如果没有，给出默认提示
        tldr_text = tldr_match.group(1).strip() if tldr_match else "格式解析偏移，请查看本地完整版"
        points_text = points_match.group(1).strip() if points_match else "格式解析偏移，请查看本地完整版"
        
        # 4. 给提取出来的纯文本“卸妆”，把碍眼的 Markdown 星号删掉，让评论区更清爽
        tldr_text = tldr_text.replace('**', '').replace('#', '')
        points_text = points_text.replace('**', '').replace('#', '')
        
        # 5. 拼装适合评论区的文案
        msg = f"深度解析已完成：\n\n【一句话总结】\n{tldr_text}\n\n【核心要点】\n{points_text}\n\n(完整万字研报已保存在本地)"
        return msg
        
    except Exception as e:
        print(f"⚠️ 提取器发生异常: {e}")
        # 兜底方案：如果真出错了，至少截取开头的几百字发出去
        return "视频解析已完成：\n\n" + full_text[:200] + "...\n(完整版已存入本地)"

# 🚀 武器 2：获取视频字幕与 AID
async def get_video_data(bvid, credential):
    try:
        v = video.Video(bvid=bvid, credential=credential)
        info = await v.get_info()
        cid = info['cid']
        aid = info['aid'] 
        
        sub_info = await v.get_subtitle(cid=cid)
        sub_list = sub_info.get('subtitles', [])
        
        if not sub_list:
            return aid, "⚠️ 抱歉，该视频暂无字幕，我无法进行总结。"
            
        sub_url = sub_list[0].get('subtitle_url')
        if sub_url.startswith('//'):
            sub_url = 'https:' + sub_url
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(sub_url)
            sub_data = resp.json()
            full_text = " ".join([item.get('content', '') for item in sub_data.get('body', [])])
            return aid, full_text
            
    except Exception as e:
        return None, f"获取字幕失败: {e}"

# 🚀 武器 3：呼叫顶级学者大脑进行深度思考
async def summarize_with_ai(text):
    print("🧠 正在呼叫顶级学者大脑进行深度思考...")
    truncated_text = text[:8000] 
    
    SYSTEM_PROMPT = """Role (角色)
你是一位顶级的知识转化专家、具有极强批判性思维的独立学者和战略分析师。你擅长从繁杂的信息中抽丝剥茧，不仅能精准提炼核心脉络，还能跳出文本本身，提供深刻的批判性见解和前瞻性的创新方向。

Task (任务)
请仔细阅读我提供的视频文本（字幕），并严格按照以下的结构，输出一份高质量的“深度解析与思考报告”。

Output Structure (输出结构)

模块一：核心解码 (The What & How)
* **📌 一句话总结 (TL;DR)：** 用一句极度精炼的话概括视频的绝对核心思想。
* **🎯 核心要点 (Key Takeaways)：** 提炼视频中最重要的 3-5 个核心观点或信息增量。
* **🗺️ 内容脉络 (Logical Flow)：** 梳理作者的讲述逻辑与结构（如：提出问题 -> 论证过程 -> 给出结论），请结构化呈现。
* **✨ 高光与细节 (Highlights)：** 提取视频中最有价值的关键数据、真实案例或令人深思的金句。

模块二：行动转化 (Actionable Next Steps)
* **🛠️ 实用建议：** 根据视频内容，总结出观众看后可以立刻应用到工作、学习或生活中的 1-3 个具体行动步骤。

模块三：AI 深度思考与延展 (Deep Reflection & Critique) 
*(注：此部分需要你发挥强大的推理与分析能力，跳出文本限制进行独立思考)*
* **🤔 启发性思考点：** 看完这个视频后，最值得观众进一步追问、反思或探讨的 2-3 个深层问题是什么？
* **🛡️ 批判性分析 (Critical Thinking)：** * **局限性与盲区：** 作者的观点是否有以偏概全、幸存者偏差或逻辑跳跃的地方？是否有未提及的重要反面因素？
  * **底层假设拷问：** 作者得出结论的底层前提假设是什么？这个假设在所有情况下都成立吗？
* **🚀 创新与破局方向：** * 基于视频中的核心理念，结合当前的技术趋势或社会发展，可以衍生出哪些新的商业模式、研究方向或跨界应用？
  * 在哪些细分领域，视频中的方法论可以被改进或颠覆？

Formatting (格式要求)
* 请使用 Markdown 格式排版，确保层次清晰，适当使用加粗和列表。
* 语言风格要专业、客观、犀利，避免废话。"""

    try:
        response = await ai_client.chat.completions.create(
            model="ark-code-latest", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"请深度解析以下视频内容（字幕）：\n\n{truncated_text}"}
            ],
            max_tokens=4000 
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"我的 AI 大脑短路了：{e}"

# 🤖 主程序循环
async def main():
    print("🤖 机器人启动！耳朵、眼睛、大脑已全部就位...")
    last_at_time = 0
    
    try:
        init_data = await session.get_at(credential=credential)
        if init_data and 'items' in init_data and len(init_data['items']) > 0:
            last_at_time = init_data['items'][0].get('at_time', 0)
    except Exception as e:
        print(f"⚠️ 初始化提示: {e}")

    print("✅ 开始巡逻...")

    while True:
        try:
            at_data = await session.get_at(credential=credential)
            items = at_data.get('items', [])
            
            for item in reversed(items):
                current_time = item.get('at_time', 0)
                
                if current_time > last_at_time:
                    user_info = item.get('user', {})
                    uname = user_info.get('nickname', '未知用户')
                    
                    item_info = item.get('item', {})
                    uri = item_info.get('uri', '')
                    source_id = item_info.get('source_id', '') 
                    
                    bvid = "BV" + uri.split("BV")[1].split("?")[0] if "BV" in uri else ""
                    
                    print(f"\n🔔 收到【{uname}】的召唤！目标: {bvid}")
                    
                    if bvid:
                        aid, text = await get_video_data(bvid, credential)
                        
                        if text.startswith("⚠️ 抱歉") or text.startswith("获取字幕失败"):
                            reply_msg = text
                        else:
                            reply_msg = await summarize_with_ai(text)
                            
                        # ==========================================
                        # 步骤一：保存完整研报到本地桌面
                        # ==========================================
                        print("💾 准备将完整总结保存到本地桌面...")
                        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                        if not os.path.exists(desktop_path):
                            desktop_path = os.path.join(os.path.expanduser("~"), "桌面")
                            
                        file_name = f"B站视频总结_{bvid}.md"
                        file_path = os.path.join(desktop_path, file_name)
                        
                        try:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(f"# B站深度解析：{bvid}\n\n")
                                f.write(f"召唤者：{uname} (评论ID: {source_id})\n\n")
                                f.write("---\n\n")
                                f.write(reply_msg)
                            print(f"🎉 任务完成！已生成文件：【{file_name}】")
                        except Exception as e:
                            print(f"❌ 保存到桌面失败：{e}")

                        # ==========================================
                        # 步骤二：提取精华并在评论区艾特回复
                        # ==========================================
                        if aid and source_id:
                            print(f"💬 准备将精华版回复给 {uname} 的评论...")
                            
                            # 1. 提取短总结 (使用修复后的高容错提取器)
                            short_msg = extract_for_comment(reply_msg)
                            
                            # 2. 拼装最终发送的文案：加上 @用户名
                            final_comment = f"@{uname} {short_msg}"
                            
                            # 3. 截断保护：B站评论上限1000字，安全起见截断到900字
                            if len(final_comment) > 950:
                                final_comment = final_comment[:900] + "\n...(字数超限，完整内容已存入本地)"
                            
                            try:
                                # 4. 发送评论
                                await send_comment(
                                    text=final_comment,
                                    oid=aid,
                                    type_=CommentResourceType.VIDEO, 
                                    root=source_id,     # 将这作为原评论的子评论
                                    parent=source_id,   # 直接回复那条评论
                                    credential=credential
                                )
                                print("🎉 绝地反击成功！精华总结已成功回复在评论区！快去刷新看看吧！")
                            except Exception as e:
                                print(f"❌ 评论回复失败: {e}")
                    
                    last_at_time = current_time
                    
            await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ 巡逻时报错了: {e}")
            await asyncio.sleep(10)

if __name__ == '__main__':
    asyncio.run(main())