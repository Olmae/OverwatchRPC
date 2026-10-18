"""Bounded local failure evidence, enabled explicitly in user settings."""
from dataclasses import asdict
from datetime import datetime
import json
import logging
import time

from .storage import data_dir

log = logging.getLogger(__name__)


def diagnostic_text(snapshot, language='en'):
    """Render the latest frame separately from confirmed presence values."""
    from .i18n import tr
    def t(key, **values):
        return tr(key, language, **values)
    if snapshot is None:
        return t('Waiting for recognition')
    def stamp(value):
        return datetime.fromtimestamp(value).strftime('%H:%M:%S') if value else '—'
    status = snapshot['status']
    missing = snapshot['missing']
    fields = {'hero': 'Hero', 'map_name': 'Map', 'mode': 'Mode',
              'elapsed': 'Match time', 'party_size': 'Party size', 'kda': 'E/A/D', 'scene': 'Scene'}
    reason = (t('Waiting for confirmation') if snapshot['pending'] else
              t('Not read: {fields}', fields=', '.join(t(fields[key]) for key in missing)) if missing else
              t('Frame processed; confirmed values shown below'))
    return '\n'.join((
        t('Last frame: {read} · Confirmed: {confirmed}', read=stamp(snapshot['read_at']),
          confirmed=stamp(snapshot['confirmed_at'])),
        t('Scene: {scene} · Processing: {ms} ms', scene=snapshot['scene'], ms=round(snapshot['duration_ms'])),
        reason,
        f"{t('Hero')}: {status.hero or '—'} · {t('Map')}: {status.map_name or '—'}",
        f"{t('Mode')}: {status.mode or '—'} · E/A/D: " +
        ('/'.join(map(str, status.kda)) if status.kda is not None else '—'),
    ))


def missing_fields(scene, settings, tab_sample=False):
    if scene.scene == 'scoreboard':
        names = ['hero', 'map_name', 'mode', 'elapsed']
        if settings.kda_enabled and settings.player_name:
            names.append('kda')
        return [name for name in names if getattr(scene, name) is None]
    if scene.scene == 'hero_select':
        return [name for name in ('hero', 'map_name') if getattr(scene, name) is None]
    if scene.phase in ('menus', 'queue') and scene.party_size is None:
        return ['party_size']
    return ['scene'] if tab_sample and scene.scene == 'unknown' else []


def retention_priority(frame):
    """Evict routine captures before failures, and manual evidence last.

    Read legacy sidecars too; older app versions did not write a priority field.
    Missing/corrupt metadata is not sufficient evidence to protect a frame.
    """
    try:
        metadata = json.loads(frame.with_suffix('.json').read_text(encoding='utf-8'))
        if metadata.get('manual'):
            return 3
        if metadata.get('missing'):
            return 1 if metadata.get('detection', {}).get('scene') == 'unknown' else 2
    except (OSError, ValueError, AttributeError):
        pass
    return 0


class FailureRecorder:
    def __init__(self, folder=None, interval=60, max_frames=40, max_bytes=100_000_000):
        self.folder = folder if folder is not None else data_dir() / 'recognition-failures'
        self.interval, self.max_frames, self.max_bytes = interval, max_frames, max_bytes
        self.last_saved = {}
        self.last_periodic = float('-inf')

    def save(self, image, scene, settings, evidence, tab_sample=False, manual=False):
        if not settings.recognition_diagnostics and not manual:
            return
        missing = missing_fields(scene, settings, tab_sample)
        key = (scene.scene, tuple(missing))
        now = time.monotonic()
        periodic = settings.recognition_minute_snapshots and now-self.last_periodic >= 60
        failure = bool(missing) and now-self.last_saved.get(key, float('-inf')) >= self.interval
        if not periodic and not failure and not manual:
            return
        if periodic:
            self.last_periodic = now
        if failure:
            self.last_saved[key] = now
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            stem = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            path = self.folder / (stem + '.png')
            image.save(path)
            detection = asdict(scene)
            detection.pop('nickname', None)
            metadata = {'missing': missing, 'detection': detection, 'periodic': periodic,
                        'manual': manual,
                        'language': settings.ocr_language, 'tab_sample': tab_sample,
                        'interface_ocr_language': evidence.get('interface_ocr_language'),
                        'hero_source': evidence.get('hero_source'),
                        'image_size': list(image.size),
                        'timing_ms': {name: evidence.get(name) for name in ('text_ms', 'parse_ms')}}
            path.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2),
                                                encoding='utf-8')
            frames = sorted(self.folder.glob('*.png'), key=lambda frame: (retention_priority(frame), frame.name))
            total = sum(frame.stat().st_size + (frame.with_suffix('.json').stat().st_size
                        if frame.with_suffix('.json').exists() else 0) for frame in frames)
            while frames and (len(frames) > self.max_frames or total > self.max_bytes):
                oldest = frames.pop(0)
                for file in (oldest, oldest.with_suffix('.json')):
                    if file.exists():
                        total -= file.stat().st_size
                        file.unlink()
            if path.exists():
                log.info('Recognition evidence saved: missing=%s file=%s', ','.join(missing), path)
                return path
        except OSError:
            log.warning('Could not save recognition evidence', exc_info=True)


recorder = FailureRecorder()
