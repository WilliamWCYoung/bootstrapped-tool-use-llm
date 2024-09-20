import json
import anthropic

client = anthropic.Anthropic()

system_prompt = """\
You're an assistant that will defer to tools when answering anything that requires processing, to avoid hallucinations.
If you can't answer with the given tools, then answer with a python block and the tool schema to create it.
Don't use any libraries that need importing in your python code block.
Don't hallucinate tools that don't exist and don't discuss the reasoning for the tools you're using.
Don't mention tool use in your final answer.

An example when you can't answer with the given tools:
<user>
What is the mean of the numbers 10, 20, 30, 40?
</user>
<assistant>
```python
def mean(numbers):
    return sum(numbers) / len(numbers)
```
```json
{
    "name": "mean",
    "description": "Get the mean of a list of numbers",
    "input_schema": {
        "type": "object",
        "properties": {
            "numbers": {
                "type": "array",
                "items": {
                    "type": "number"
                }
            }
        },
        "required": ["numbers"]
    }
}
```
</assistant>
"""

def clean_block(block):
    if block.type == "text":
        return {"type": "text", "text": block.text}
    elif block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}


def smart_prompt(question):
    tools = []
    messages= [{"role": "user", "content": system_prompt + question}]

    while True:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )
        messages.append({
            "role": "assistant",
            "content": [clean_block(block) for block in message.content]
        })


        # input("continue?")
        block_types = [block.type for block in message.content]

        if "tool_use" in block_types:
            result_content = []
            for block in message.content:
                if block.type == "tool_use":
                    result = eval(block.name)(**block.input)
                    result_content.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })
            messages.append(
                {"role": "user", "content": result_content}
            )
            continue
        
        tool_loaded = False
        for block in message.content:
            if block.type == "text":
                json_schema = None
                python_code = None
                for section in block.text.split("```"):
                    if section.startswith("json"):
                        json_schema = "\n".join(section.split("\n")[1:])
                    if section.startswith("python"):
                        python_code = "\n".join(section.split("\n")[1:])

                if json_schema and python_code:
                    print("Assistant's code:")
                    print(python_code)
                
                    tools.append(json.loads(json_schema))
                    exec(python_code)
                    messages.append({"role": "user", "content": "the tool has been loaded"})
                    tool_loaded = True
                    break

        if not tool_loaded:
            for block in message.content:
                if block.type == "text":
                    print("assistant:", block.text)
                    print()
            return
        
question = input("user: ") # How many r's are there in the word 'strawberry'?
print()
smart_prompt(question)
