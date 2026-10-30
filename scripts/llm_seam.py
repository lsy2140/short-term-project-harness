#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llm_seam.py — 업무 로직과 모델 호출 사이의 경계(seam). 표준 라이브러리만, Python 3.9+.

왜 필요한가: 모델 호출을 업무 로직에 섞으면 결정성·테스트 가능성·실패 격리가 동시에 깨진다.
업무 로직은 Provider 인터페이스(complete(key, prompt) -> str)만 안다. 기본은 StubProvider라서
네트워크·키 없이 테스트가 돈다. 실제 호출이 필요하면 환경에 맞는 Provider를 주입한다.

Provider 3종
  StubProvider      결정론적. {key: 응답} 사전. 테스트·오프라인 기본값.
  CodexCliProvider  시험장에서 제공된 Codex CLI를 subprocess로 호출(codex exec, read-only).
                    토큰 사용량이 기록되므로 호출 수를 최소화하고 캐시를 쓴다. 과제 안내가 금지하면 쓰지 않는다.
  HttpProvider      OPENAI_BASE_URL + OPENAI_API_KEY 가 환경변수로 주어진 경우(이전 대회는 주최측 프록시 제공)
                    urllib로 chat.completions 호출. SDK 불필요. 키는 환경변수에서만 읽고 로그에 남기지 않는다.

다섯 가지 방어: 스키마 검증(parse_json_or_none) / 재시도 1회 / 참조 무결성(check_ids) / 폴백 표시(meta) / 캐시(결정성).

사용 예
    sys.path.insert(0, 'scripts'); from llm_seam import Seam, StubProvider, CodexCliProvider  # (scripts 패키지명 충돌 회피)
    seam = Seam(StubProvider({"summary": '{"title": "..."}'}))
    text = seam.complete("summary", prompt)            # 실패 시 ModelUnavailable
    data = seam.complete_json("summary", prompt, required_keys=["title"])  # None 이면 폴백
    print(seam.meta)   # {"calls":1,"cache_hits":0,"failures":0,"retries":0,"elapsed_ms":3,"provider":"StubProvider"}
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass


class ModelUnavailable(RuntimeError):
    """호출 실패. 업무 로직은 이것을 잡아 결정론적 폴백으로 간다."""


class StubProvider(object):
    name = 'StubProvider'

    def __init__(self, responses=None, default=None):
        self.responses = dict(responses or {})
        self.default = default

    def complete(self, key, prompt):
        if key in self.responses:
            return self.responses[key]
        if self.default is not None:
            return self.default
        raise ModelUnavailable('stub has no response for key=%s' % key)


class CodexCliProvider(object):
    """제공된 Codex CLI를 비대화형으로 호출. 파일 수정 금지(read-only sandbox), 승인 없음."""
    name = 'CodexCliProvider'

    def __init__(self, model=None, timeout=120, cwd=None, extra_args=None):
        self.model = model
        self.timeout = timeout
        self.cwd = cwd
        self.extra_args = list(extra_args or [])

    def complete(self, key, prompt):
        exe = shutil.which('codex') or 'codex'  # Windows 에서는 codex.cmd 로 해석된다
        cmd = [exe, 'exec', '-s', 'read-only', '-c', 'approval_policy="never"', '--skip-git-repo-check']
        if self.model:
            cmd += ['-m', self.model]
        cmd += self.extra_args
        cmd.append(prompt)
        try:
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, cwd=self.cwd,
                                  stdin=subprocess.DEVNULL, encoding='utf-8', errors='replace')
        except (OSError, subprocess.SubprocessError) as e:
            raise ModelUnavailable('codex exec failed: %s' % e)
        if done.returncode != 0:
            raise ModelUnavailable('codex exec exit %d: %s' % (done.returncode, (done.stderr or '')[-300:]))
        out = (done.stdout or '').strip()
        if not out:
            raise ModelUnavailable('codex exec returned empty output')
        # codex exec는 마지막에 최종 응답을 그대로 출력한다. 중간 로그가 섞이면 마지막 비어있지 않은 블록을 쓴다.
        blocks = [b.strip() for b in out.split('\n\n') if b.strip()]
        return blocks[-1] if blocks else out


class HttpProvider(object):
    """OpenAI 호환 chat.completions 를 urllib 로 호출. 환경변수 OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL."""
    name = 'HttpProvider'

    def __init__(self, base_url=None, api_key=None, model=None, timeout=30):
        self.base_url = (base_url or os.environ.get('OPENAI_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY') or ''
        self.model = model or os.environ.get('OPENAI_MODEL') or 'gpt-4.1'
        self.timeout = timeout

    def complete(self, key, prompt):
        if not self.api_key:
            raise ModelUnavailable('OPENAI_API_KEY not set')
        body = json.dumps({'model': self.model, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0}).encode('utf-8')
        req = urllib.request.Request(self.base_url + '/chat/completions', data=body, headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.api_key, 'Accept-Encoding': 'identity'})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:  # noqa
            raise ModelUnavailable('http call failed: %s' % type(e).__name__)
        try:
            return data['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError):
            raise ModelUnavailable('unexpected response shape')


class Seam(object):
    """캐시 + 계측 + 재시도 1회. 업무 로직은 이 객체만 쓴다."""

    def __init__(self, provider, cache_path=None, retry_once=True):
        self.provider = provider
        self.cache_path = cache_path
        self.retry_once = retry_once
        self.cache = {}
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as fh:
                    self.cache = json.load(fh)
            except (OSError, ValueError):
                self.cache = {}
        self.meta = {'calls': 0, 'cache_hits': 0, 'failures': 0, 'retries': 0, 'elapsed_ms': 0,
                     'provider': getattr(provider, 'name', type(provider).__name__)}

    @staticmethod
    def _hash(key, prompt):
        return hashlib.sha256((key + '\x00' + prompt).encode('utf-8')).hexdigest()

    def _save(self):
        if not self.cache_path:
            return
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as fh:
                json.dump(self.cache, fh, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def complete(self, key, prompt):
        h = self._hash(key, prompt)
        if h in self.cache:
            self.meta['cache_hits'] += 1
            return self.cache[h]
        t0 = time.perf_counter()
        self.meta['calls'] += 1
        try:
            text = self.provider.complete(key, prompt)
        except ModelUnavailable:
            self.meta['failures'] += 1
            raise
        finally:
            self.meta['elapsed_ms'] += int((time.perf_counter() - t0) * 1000)
        self.cache[h] = text
        self._save()
        return text

    def complete_json(self, key, prompt, required_keys=()):
        """JSON 을 요구. 깨지면 'JSON만 반환' 으로 1회 재시도. 그래도 안 되면 None (호출자는 폴백)."""
        try:
            text = self.complete(key, prompt)
        except ModelUnavailable:
            return None
        data = parse_json_or_none(text, required_keys)
        if data is not None or not self.retry_once:
            return data
        self.meta['retries'] += 1
        try:
            text = self.complete(key + '#retry', prompt + '\n\n반드시 유효한 JSON 객체만 출력하라. 설명·코드펜스 금지.')
        except ModelUnavailable:
            return None
        return parse_json_or_none(text, required_keys)


def parse_json_or_none(text, required_keys=()):
    """모델 출력은 신뢰할 수 없는 입력이다. 코드펜스 제거 → json.loads → 필수 키 확인."""
    if not isinstance(text, str):
        return None
    s = text.strip()
    if s.startswith('```'):
        s = s.strip('`')
        if s.lower().startswith('json'):
            s = s[4:]
    start, end = s.find('{'), s.rfind('}')
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(s[start:end + 1])
    except ValueError:
        return None
    if not isinstance(data, dict) or any(k not in data for k in required_keys):
        return None
    return data


def check_ids(mentioned, known, label='id'):
    """참조 무결성: 모델이 언급한 ID 가 전부 원본 데이터에 있는가. 없는 것 목록을 돌려준다."""
    known = set(known)
    return [m for m in mentioned if m not in known]


if __name__ == '__main__':
    # 자가 점검: 스텁 → 캐시 → JSON 파싱 → 참조 무결성
    seam = Seam(StubProvider({'k': '```json\n{"title": "ok", "ids": ["A", "Z"]}\n```'}))
    d = seam.complete_json('k', 'p', required_keys=['title'])
    assert d and d['title'] == 'ok'
    seam.complete('k', 'p')
    assert seam.meta['cache_hits'] == 1 and seam.meta['calls'] == 1
    assert check_ids(d['ids'], ['A', 'B']) == ['Z']
    bad = Seam(StubProvider({}))
    assert bad.complete_json('x', 'p') is None and bad.meta['failures'] == 1
    print('llm_seam self-check OK', seam.meta)
    if '--codex' in sys.argv:
        s = Seam(CodexCliProvider())
        try:
            print(s.complete('ping', 'Reply with JSON only: {"pong": true}'))
        except ModelUnavailable as e:
            print('ModelUnavailable:', e)
        print(s.meta)
