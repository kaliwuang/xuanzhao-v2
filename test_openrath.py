"""最简OpenRath + MiMo测试"""
import sys
sys.path.insert(0, ".")

from rath import flow
from rath.session import Session

# 配置MiMo Provider
provider = flow.Provider(
    model="mimo-v2.5-pro",
    api_key="tp-syfnd40eilysggo5yj75f1ud2ovq9f4jvd2ym6o8b42varvg",
    base_url="https://token-plan-sgp.xiaomimimo.com/v1",
)

# 创建最简单的Agent
agent = flow.Agent(
    "用一句话回答用户的问题。",
    provider,
)

# 创建Session
session = Session.from_user_message("你好，你是谁？").to("local", spec="./")

# 运行
print("测试OpenRath + MiMo...")
result = agent(session)
print("完成！")

# 输出结果
for row in result.chunk_table.rows:
    if row.kind.value == "assistant":
        print(f"回答：{row.payload.get('content', '')}")
