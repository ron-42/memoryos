from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.security import UserContext
from app.models.capture import CaptureTextRequest, CaptureUrlRequest, CaptureStreamEvent
from app.services.capture_pipeline import CapturePipelineService

router = APIRouter(prefix="/capture", tags=["capture"])


def _format_sse(event: CaptureStreamEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


async def _stream_events(events: AsyncGenerator[CaptureStreamEvent, None]) -> AsyncGenerator[str, None]:
    async for event in events:
        yield _format_sse(event)


@router.post("/url")
async def capture_url(
    payload: CaptureUrlRequest,
    user: UserContext = Depends(get_current_user),
) -> StreamingResponse:
    service = CapturePipelineService()
    return StreamingResponse(
        _stream_events(service.capture_url(str(payload.url), user)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/text")
async def capture_text(
    payload: CaptureTextRequest,
    user: UserContext = Depends(get_current_user),
) -> StreamingResponse:
    service = CapturePipelineService()
    return StreamingResponse(
        _stream_events(service.capture_text(payload.text, payload.title, user)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/pdf")
async def capture_pdf(
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
) -> StreamingResponse:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF uploads are supported")
    contents = await file.read()
    service = CapturePipelineService()
    return StreamingResponse(
        _stream_events(service.capture_pdf(file.filename, contents, user)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
