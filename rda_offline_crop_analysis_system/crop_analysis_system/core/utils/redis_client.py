import threading
from typing import Dict, Optional

import redis
from django.conf import settings

from core.utils.log_files import append_log


_lock = threading.Lock()
_client: Optional[redis.Redis] = None
_fallback_store: Dict[str, Dict[str, str]] = {}


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def _fallback_set(key: str, mapping: Dict[str, str]) -> None:
    _fallback_store[key] = {**_fallback_store.get(key, {}), **mapping}


def _fallback_get(key: str) -> Dict[str, str]:
    return _fallback_store.get(key, {}).copy()


def _progress_key(job_id: int) -> str:
    return f"job:{job_id}:progress"


def _step_progress_key(job_id: int, step: str) -> str:
    return f"job:{job_id}:progress:{step}"


def set_progress(job_id: int, current: int, total: int, message: str = "") -> Dict[str, str]:
    percent = int((current / total) * 100) if total else 0
    payload = {
        "current": str(current),
        "total": str(total),
        "percent": str(percent),
        "message": message,
    }
    key = _progress_key(job_id)
    try:
        client = get_redis()
        client.hset(key, mapping=payload)
    except Exception:
        _fallback_set(key, payload)
    
    if message:
        append_log(job_id, message, percent=percent)
        
    return payload


def set_step_progress(job_id: int, step: str, current: int, total: int, message: str = "") -> Dict[str, str]:
    percent = int((current / total) * 100) if total else 0
    payload = {
        "current": str(current),
        "total": str(total),
        "percent": str(percent),
        "message": message,
    }
    key = _step_progress_key(job_id, step)
    try:
        client = get_redis()
        client.hset(key, mapping=payload)
    except Exception:
        _fallback_set(key, payload)
        
    if message:
        append_log(job_id, f"{step}: {message}", percent=percent)

    return payload


def add_step_total(job_id: int, step: str, amount: int) -> Dict[str, str]:
    key = _step_progress_key(job_id, step)
    try:
        client = get_redis()
        total_val = client.hincrby(key, "total", amount)
        current_val = int(client.hget(key, "current") or 0)
        percent = int((current_val / total_val) * 100) if total_val else 0
        client.hset(key, "percent", percent)
        return {
            "current": str(current_val),
            "total": str(total_val),
            "percent": str(percent),
            "message": str(client.hget(key, "message") or ""),
        }
    except Exception:
        store = _fallback_get(key)
        total_val = int(store.get("total", "0")) + amount
        current_val = int(store.get("current", "0"))
        percent = int((current_val / total_val) * 100) if total_val else 0
        payload = {
            "current": str(current_val),
            "total": str(total_val),
            "percent": str(percent),
            "message": store.get("message", ""),
        }
        _fallback_set(key, payload)
        return payload


def increment_progress(
    job_id: int, increment: int = 1, total: Optional[int] = None, message: str = ""
) -> Dict[str, str]:
    key = _progress_key(job_id)
    try:
        client = get_redis()
        pipe = client.pipeline()
        pipe.hincrby(key, "current", increment)
        if total is not None:
            pipe.hset(key, "total", total)
        if message:
            pipe.hset(key, "message", message)
        current = pipe.execute()[0]
        total_val = int(client.hget(key, "total") or 0)
        percent = int((int(current) / total_val) * 100) if total_val else 0
        client.hset(key, "percent", percent)
        
        if message:
            append_log(job_id, message, percent=percent)

        return {
            "current": str(current),
            "total": str(total_val),
            "percent": str(percent),
            "message": message,
        }
    except Exception:
        store = _fallback_get(key)
        current_val = int(store.get("current", "0")) + increment
        total_val = int(total) if total is not None else int(store.get("total", "0"))
        percent = int((current_val / total_val) * 100) if total_val else 0
        payload = {
            "current": str(current_val),
            "total": str(total_val),
            "percent": str(percent),
            "message": message or store.get("message", ""),
        }
        _fallback_set(key, payload)
        
        if message:
            append_log(job_id, payload["message"], percent=percent)
            
        return payload


def increment_step_progress(
    job_id: int, step: str, increment: int = 1, total: Optional[int] = None, message: str = ""
) -> Dict[str, str]:
    key = _step_progress_key(job_id, step)
    try:
        client = get_redis()
        pipe = client.pipeline()
        pipe.hincrby(key, "current", increment)
        if total is not None:
            pipe.hset(key, "total", total)
        if message:
            pipe.hset(key, "message", message)
        current = pipe.execute()[0]
        total_val = int(client.hget(key, "total") or 0)
        percent = int((int(current) / total_val) * 100) if total_val else 0
        client.hset(key, "percent", percent)
        
        if message:
            append_log(job_id, f"{step}: {message}", percent=percent)

        return {
            "current": str(current),
            "total": str(total_val),
            "percent": str(percent),
            "message": message,
        }
    except Exception:
        store = _fallback_get(key)
        current_val = int(store.get("current", "0")) + increment
        total_val = int(total) if total is not None else int(store.get("total", "0"))
        percent = int((current_val / total_val) * 100) if total_val else 0
        payload = {
            "current": str(current_val),
            "total": str(total_val),
            "percent": str(percent),
            "message": message or store.get("message", ""),
        }
        _fallback_set(key, payload)
        
        if message:
            append_log(job_id, f"{step}: {payload['message']}", percent=percent)
            
        return payload


def get_progress(job_id: int) -> Dict[str, str]:
    key = _progress_key(job_id)
    try:
        client = get_redis()
        data = client.hgetall(key)
        if not data:
            return {"current": "0", "total": "0", "percent": "0", "message": ""}
        return data
    except Exception:
        return _fallback_get(key)


def get_all_progress(job_id: int, steps: Optional[list] = None) -> Dict[str, Dict[str, str]]:
    if steps is None:
        steps = [
            "inference",
            "merge",
            "area",
            "thumbnail",
            "inference_windows",
            "merge_tiles",
            "merge_compute",
        ]
    data = {"overall": get_progress(job_id), "steps": {}}
    for step in steps:
        key = _step_progress_key(job_id, step)
        try:
            client = get_redis()
            step_data = client.hgetall(key)
            if not step_data:
                step_data = {"current": "0", "total": "0", "percent": "0", "message": ""}
        except Exception:
            step_data = _fallback_get(key)
        data["steps"][step] = step_data
    return data


def set_cancel(job_id: int, cancelled: bool = True) -> None:
    key = f"job:{job_id}:cancel"
    try:
        client = get_redis()
        if cancelled:
            client.set(key, "1")
        else:
            client.delete(key)
    except Exception:
        if cancelled:
            _fallback_set(key, {"cancel": "1"})
        else:
            _fallback_store.pop(key, None)


def is_cancelled(job_id: int) -> bool:
    key = f"job:{job_id}:cancel"
    try:
        client = get_redis()
        return client.get(key) == "1"
    except Exception:
        return _fallback_get(key).get("cancel") == "1"


def reset_progress(job_id: int) -> None:
    keys = [
        _progress_key(job_id),
        _step_progress_key(job_id, "inference"),
        _step_progress_key(job_id, "merge"),
        _step_progress_key(job_id, "area"),
        _step_progress_key(job_id, "inference_windows"),
        _step_progress_key(job_id, "merge_tiles"),
        _step_progress_key(job_id, "merge_compute"),
    ]
    try:
        client = get_redis()
        if keys:
            client.delete(*keys)
    except Exception:
        for key in keys:
            _fallback_store.pop(key, None)
