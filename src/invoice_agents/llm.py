"""Swappable LLM factory. Default backend is Groq (free tier); override with LLM_BACKEND."""
import os

from dotenv import load_dotenv

load_dotenv()

_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
    "xai": "grok-3",
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-5",
    "ollama": "fastcontext",
    "bedrock": "anthropic.claude-3-haiku-20240307-v1:0",
}


def get_llm(temperature: float = 0.0):
    backend = os.environ.get("LLM_BACKEND", "groq").lower()

    if backend == "groq":
        keys_raw = os.environ.get("GROQ_API_KEYS") or os.environ.get("GROQ_API_KEY", "")
        keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
        if len(keys) > 1:
            from src.invoice_agents.groq_rotation import RotatingChatGroq

            return RotatingChatGroq(api_keys=keys, model=_MODELS["groq"], temperature=temperature)

        from langchain_groq import ChatGroq

        return ChatGroq(model=_MODELS["groq"], temperature=temperature)

    if backend == "ollama":
        from langchain_ollama import ChatOllama

        model = os.environ.get("OLLAMA_MODEL", _MODELS["ollama"])
        return ChatOllama(model=model, temperature=temperature)

    if backend == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=_MODELS["gemini"], temperature=temperature)

    if backend == "xai":
        from langchain_xai import ChatXAI

        return ChatXAI(model=_MODELS["xai"], temperature=temperature)

    if backend == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=_MODELS["openai"], temperature=temperature)

    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=_MODELS["anthropic"], temperature=temperature)

    if backend == "bedrock":
        from langchain_aws import ChatBedrockConverse

        model = os.environ.get("BEDROCK_MODEL_ID", _MODELS["bedrock"])
        region = os.environ.get("AWS_REGION", "us-east-1")
        return ChatBedrockConverse(model=model, region_name=region, temperature=temperature)

    raise ValueError(f"Unknown LLM_BACKEND: {backend!r}. Expected one of {list(_MODELS)}.")
