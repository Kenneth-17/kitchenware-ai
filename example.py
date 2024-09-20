from openai import OpenAI
client = OpenAI(api_key='sk-Qx1xcQJlq6ZcIeJisyyzfuhSB8WFAkWt77PDjm9IbTT3BlbkFJbWQvNZHUP9VvA9Z1TAxo-R2b2gdUP1Jgwr8SKn5joA')
img_url = 'https://www.shutterstock.com/image-photo/raw-chicken-fillet-pieces-fresh-260nw-2044930682.jpg'

response = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What’s in this image, just the food name?"},
        {
          "type": "image_url",
          "image_url": {
            "url": img_url,
          },
        },
      ],
    }
  ],
  max_tokens=300,
)

print(response.choices[0].message.content)