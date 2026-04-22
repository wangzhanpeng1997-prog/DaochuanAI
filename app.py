import streamlit as st
import requests
import time
import base64
import io
from PIL import Image

# ===================== 1. 基础配置 =====================
st.set_page_config(page_title="Seedance 2.0 视频生成", page_icon="🎬", layout="wide")
st.title("🎬 Doubao-Seedance 2.0 视频生成工具")

# 从 Streamlit Secrets 获取配置
# 这里我们改用更简单的 API_KEY 方式
API_KEY = st.secrets.get("API_KEY", "")
PASSWORD = st.secrets.get("PASSWORD", "123456")

# 访问密码校验
if "access_granted" not in st.session_state:
    st.session_state.access_granted = False

if not st.session_state.access_granted:
    with st.container(border=True):
        pwd = st.text_input("请输入访问密钥", type="password")
        if st.button("进入系统", use_container_width=True):
            if pwd == PASSWORD:
                st.session_state.access_granted = True
                st.rerun()
            else:
                st.error("密码错误")
    st.stop()

if not API_KEY:
    st.error("❌ 未在 Secrets 中配置 API_KEY！请检查 Streamlit 设置。")
    st.stop()

# ===================== 2. 侧边栏参数 =====================
with st.sidebar:
    st.header("⚙️ 参数设置")
    mode = st.radio("生成模式", ["文生视频", "参考生成", "首帧锁定"])
    ratio = st.selectbox("视频比例", ["16:9", "9:16", "1:1", "3:4", "4:3", "21:9"], index=0)
    res = st.select_slider("分辨率", options=["480p", "720p", "1080p"], value="720p")
    
# ===================== 3. 主界面 =====================
col1, col2 = st.columns([2, 1])

with col1:
    prompt = st.text_area("📝 画面描述词", height=150, placeholder="例如：一个宇航员在火星上冲浪，赛博朋克风格...")
    
    img_b64 = None
    if mode in ["参考生成", "首帧锁定"]:
        uploaded_file = st.file_uploader(f"上传{mode}图片", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, caption="已上传图片", width=300)
            # 压缩并转 Base64
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=80)
            img_b64 = base64.b64encode(buffered.getvalue()).decode()

    btn = st.button("🚀 开始生成视频", type="primary", use_container_width=True)

# ===================== 4. 核心逻辑 =====================
# 根据你的图1，API地址如下
API_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

if btn:
    if not prompt:
        st.warning("请输入描述词")
    else:
        # 构造任务请求
        payload = {
            "model": "doubao-seedance-2-0-260128", # 对齐你的图1
            "content": [
                {"type": "text", "text": prompt}
            ],
            "params": {
                "aspect_ratio": ratio,
                "resolution": res
            }
        }
        
        # 如果有图片
        if img_b64:
            payload["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })

        try:
            with st.status("正在提交任务...", expanded=True) as status:
                # 1. 提交
                res_post = requests.post(API_URL, json=payload, headers=HEADERS)
                res_data = res_post.json()
                
                if res_post.status_code != 200:
                    st.error(f"提交失败: {res_data.get('error', {}).get('message', '未知错误')}")
                    st.stop()
                
                task_id = res_data.get("id")
                st.write(f"✅ 任务提交成功！ID: {task_id}")
                
                # 2. 轮询结果
                query_url = f"{API_URL}/{task_id}"
                while True:
                    res_get = requests.get(query_url, headers=HEADERS)
                    task_info = res_get.json()
                    status_str = task_info.get("status")
                    
                    if status_str == "succeeded":
                        status.update(label="🎉 生成成功！", state="complete")
                        # 展示视频
                        video_url = task_info.get("output", {}).get("video_url")
                        if video_url:
                            st.video(video_url)
                            st.success(f"[👉 点击此处直接下载视频]({video_url})")
                        break
                    elif status_str == "failed":
                        status.update(label="❌ 生成失败", state="error")
                        st.error(f"错误详情: {task_info.get('error')}")
                        break
                    else:
                        st.write("⏳ 视频努力生成中，请勿关闭页面...")
                        time.sleep(10) # 视频生成较慢，10秒查一次
                        
        except Exception as e:
            st.error(f"系统错误: {str(e)}")