"""Unified LLM interface for md2pdf/pdf2md.
Provider priority: ANTHROPIC_API_KEY > OPENAI_API_KEY > OPENROUTER_API_KEY
"""
import os, base64, sys

def get_provider():
    if os.environ.get('ANTHROPIC_API_KEY'):
        return 'anthropic'
    elif os.environ.get('OPENAI_API_KEY'):
        return 'openai'
    elif os.environ.get('OPENROUTER_API_KEY'):
        return 'openrouter'
    return None

def text_complete(prompt, max_tokens=16384):
    provider = get_provider()
    if not provider:
        return None
    try:
        if provider == 'anthropic':
            import anthropic
            r = anthropic.Anthropic().messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}])
            return r.content[0].text
        else:
            import openai
            if provider == 'openai':
                client, model = openai.OpenAI(), "gpt-4o-mini"
            else:
                client = openai.OpenAI(base_url="https://openrouter.ai/api/v1",
                                       api_key=os.environ['OPENROUTER_API_KEY'])
                model = "openai/gpt-4o-mini"
            r = client.chat.completions.create(model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}])
            return r.choices[0].message.content
    except Exception as e:
        print(f"LLM error: {e}", file=sys.stderr)
        return None

def vision_complete(image_bytes, media_type, prompt, max_tokens=2048):
    provider = get_provider()
    if not provider:
        return None
    img_b64 = base64.b64encode(image_bytes).decode()
    try:
        if provider == 'anthropic':
            import anthropic
            r = anthropic.Anthropic().messages.create(
                model="claude-sonnet-4-6", max_tokens=max_tokens,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64",
                     "media_type": media_type, "data": img_b64}},
                    {"type": "text", "text": prompt}]}])
            return r.content[0].text
        else:
            import openai
            data_url = f"data:{media_type};base64,{img_b64}"
            if provider == 'openai':
                client, model = openai.OpenAI(), "gpt-4o"
            else:
                client = openai.OpenAI(base_url="https://openrouter.ai/api/v1",
                                       api_key=os.environ['OPENROUTER_API_KEY'])
                model = "openai/gpt-4o"
            r = client.chat.completions.create(model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt}]}])
            return r.choices[0].message.content
    except Exception as e:
        print(f"LLM vision error: {e}", file=sys.stderr)
        return None
