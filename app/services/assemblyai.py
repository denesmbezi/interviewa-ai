from fastapi import HTTPException
import httpx

from app.core.config import get_settings

settings = get_settings()


async def generate_assemblyai_token() -> str:
    if not settings.assemblyai_api_key:
        raise HTTPException(status_code=500, detail="AssemblyAI API key is not configured on the server")

    token_url = "https://agents.assemblyai.com/v1/token"
    try:
        response = httpx.get(
            token_url,
            headers={"Authorization": f"Bearer {settings.assemblyai_api_key}"},
            params={"expires_in_seconds": 600},
            timeout=15.0,
        )

        try:
            response_body = response.json()
        except ValueError:
            response_body = {"error": response.text}

        if response.status_code >= 400:
            detail = response_body.get("error") or response_body.get("message") or response.text or "Unknown AssemblyAI error"
            raise HTTPException(status_code=502, detail=f"AssemblyAI token request failed ({response.status_code}): {detail}")

        token = response_body.get("token")
        if not token:
            raise HTTPException(status_code=500, detail="AssemblyAI did not return a session token")
        return token
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AssemblyAI token request failed: {exc}") from exc
