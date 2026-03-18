import asyncio

from agent import AgentOptions, Agent, AgentEvent
from ai.providers import KimiProvider


async def main():
  async def stream_fn(model, context, options):
    return provider.stream_simple(model, context, options)

  provider = KimiProvider()
  agent_options = AgentOptions(stream_fn=stream_fn)
  agent = Agent(agent_options)
  agent.set_model(provider.get_model())
  agent.set_system_prompt("你是一个有帮助的 AI 助手。")

  def on_event(event: AgentEvent):
    print(event)

  agent.subscribe(on_event)

  await agent.prompt("简单介绍一下 llm, 50个字内")
  await agent.wait_for_idle()


asyncio.run(main())
