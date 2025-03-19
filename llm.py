import json
import ollama
import openai

def query_deepseek_json(prompt):
    """Send prompt to DeepSeek and attempt to get JSON back"""

    config = {}
    with open('deepseek.json', 'r') as file:
        config = json.load(file)
    api_key = config.get('apiKey')
    
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a data extract tool. You always provide your response in valid JSON format."},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )

    return parse_json(response.choices[0].message.content)


def query_ollama_json(prompt, model="llama3"):
    """
    Send a prompt to Ollama using the official client and get JSON response
    
    Args:
        prompt: The prompt to send to the model
        model: The Ollama model to use (default: llama3)
    
    Returns:
        dict: The parsed JSON response
    """
    # Add instructions to return JSON
    json_prompt = f"""
    Please provide your response in valid JSON format.
    {prompt}
    Format your entire response as a JSON object with appropriate fields.
    """
    
    # Generate a response from the model
    response = ollama.generate(model=model, prompt=json_prompt)
    
    # Extract the text response
    text_response = response['response']

    return parse_json(text_response)

def parse_json(text_response):
    """Attempt to make the LLM text response into JSON"""

    # Try to parse the response as JSON
    try:
        # Find JSON content in the response
        json_start = text_response.find('{')
        json_end = text_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_string = text_response[json_start:json_end]
            return json.loads(json_string)
        else:
            # If we can't find valid JSON delimiters, try parsing the whole response
            return json.loads(text_response)
    except json.JSONDecodeError:
        # If JSON parsing fails, return the raw response
        return {"error": "Failed to parse JSON", "raw_response": text_response}