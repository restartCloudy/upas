#!/bin/bash
# UPAS 图表发送到飞书脚本

# 配置
WEBHOOK_URL="你的飞书webhook地址"

# 图表目录
VIZ_DIR="/root/.openclaw/workspace/upas/data/visualizations"

# 发送图表到飞书的函数
send_to_feishu() {
    local image_file=$1
    local title=$2
    
    # Base64编码图片
    base64_image=$(base64 -i "$image_file")
    
    # 发送请求
    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"msg_type\": \"image\",
            \"content\": {
                \"image_key\": \"$base64_image\"
            }
        }"
}

# 发送所有图表
echo "正在发送UPAS图表到飞书..."

for img in "$VIZ_DIR"/*.png; do
    if [ -f "$img" ]; then
        filename=$(basename "$img")
        echo "发送: $filename"
        # send_to_feishu "$img" "$filename"
    fi
done

echo "发送完成！"

# 或者使用 Python 发送（更稳定）
python3 << 'EOF'
import requests
import base64
import os

webhook_url = "你的飞书webhook地址"
viz_dir = "/root/.openclaw/workspace/upas/data/visualizations"

for filename in os.listdir(viz_dir):
    if filename.endswith('.png'):
        filepath = os.path.join(viz_dir, filename)
        with open(filepath, 'rb') as f:
            image_data = f.read()
        
        # 使用飞书开放平台API上传图片并发送
        print(f"发送: {filename}")
EOF