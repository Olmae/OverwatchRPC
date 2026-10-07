"""Spatial game text parsing. Team colors and character models are never evidence."""
from dataclasses import dataclass
import re
from difflib import SequenceMatcher
from .model import normalize


@dataclass(frozen=True)
class Word:
    text: str
    x: float
    y: float
    width: float
    height: float

    @property
    def cy(self):
        return self.y + self.height / 2


@dataclass(frozen=True)
class Detection:
    phase: str | None = None
    hero: str | None = None
    map_name: str | None = None
    mode: str | None = None
    kda: tuple | None = None
    nickname: str | None = None
    scene: str = 'unknown'
    elapsed: int | None = None
    party_size: int | None = None


def text_in(words, box):
    x1, y1, x2, y2 = box
    selected = [w for w in words if x1 <= w.x + w.width / 2 <= x2 and y1 <= w.cy <= y2]
    # OCR bounds differ for ascenders/descenders on the same baseline.
    # Fixed y buckets can reverse words when a line crosses a bucket edge.
    lines = []
    for word in sorted(selected, key=lambda w: (w.cy, w.x)):
        if lines:
            line = lines[-1]
            center = sum(w.cy for w in line) / len(line)
            tolerance = .6 * max(word.height, max(w.height for w in line))
            if abs(word.cy - center) <= tolerance:
                line.append(word)
                continue
        lines.append([word])
    return ' '.join(w.text for line in lines for w in sorted(line, key=lambda w: w.x)).upper()


def catalog_name(text, catalog, fuzzy=False):
    # Whole phrases only: never fuzzy-match noisy menu text to a hero or map.
    haystack = ' ' + re.sub(r'[^\w]+', ' ', text.casefold()) + ' '
    matches = []
    for item in catalog:
        name = item if isinstance(item, str) else item['name']
        aliases = [name] if isinstance(item, str) else [name, *item.get('localized_names', {}).values()]
        if any(' ' + re.sub(r'[^\w]+', ' ', alias.casefold()) + ' ' in haystack for alias in aliases):
            matches.append(name)
    if len(matches) == 1:
        return matches[0]
    if fuzzy and not matches:
        if re.search(r'\bD[.]V', text, re.I):
            return next((h if isinstance(h, str) else h['name'] for h in catalog if normalize(h if isinstance(h, str) else h['name']) == 'dva'), None)
        candidates = []
        for item in catalog:
            name = item if isinstance(item, str) else item['name']
            aliases = [name] if isinstance(item, str) else [name, *item.get('localized_names', {}).values()]
            tokens = text.split()
            scores = []
            for alias in aliases:
                normalized = normalize(alias)
                # Very short names are too ambiguous for typo correction.
                if len(normalized) < 4:
                    continue
                size = len(alias.split())
                for start in range(len(tokens) - size + 1):
                    phrase = normalize(' '.join(tokens[start:start + size]))
                    scores.append(SequenceMatcher(None, normalized, phrase).ratio())
                    # The condensed Cyrillic A can be read as Я by Windows OCR.
                    # Keep the existing length, confidence and ambiguity gates.
                    if 'а' in normalized:
                        scores.append(SequenceMatcher(None, normalized, phrase.replace('я', 'а')).ratio())
            score = max(scores, default=0)
            candidates.append((score, name))
        candidates.sort(reverse=True)
        if candidates and candidates[0][0] >= .7 and (len(candidates) < 2 or candidates[0][0]-candidates[1][0] >= .12):
            return candidates[0][1]
    return None


def mode_from(text):
    for mode, aliases in [('Stadium', ('STADIUM', 'СТАДИОН')), ('Competitive', ('COMPETITIVE', 'СОРЕВНОВАТЕЛ')),
                          ('Quick Play', ('QUICK PLAY', 'БЫСТРАЯ ИГРА', 'НЕРЕЙТИНГОВАЯ ИГРА', 'JOGO CASUAL')), ('Practice', ('PRACTICE', 'ТРЕНИРОВОЧ', 'УЧЕБНЫЙ ПОЛИГОН')),
                          ('Arcade', ('ARCADE', 'АРКАДА')), ('Custom Game', ('CUSTOM GAME', 'СВОЯ ИГРА')),
                          ('Control', ('CONTROL', 'КОНТРОЛЬ')), ('Escort', ('ESCORT', 'СОПРОВОЖДЕНИЕ')),
                          ('Hybrid', ('HYBRID', 'ГИБРИДНЫЙ РЕЖИМ'))]:
        if any(alias in text for alias in aliases):
            return mode
    return None


def own_row(words, nickname):
    if not nickname:
        return None
    scored = []
    for w in words:
        if .12 < w.x < .36 and .16 < w.cy < .88:
            score = SequenceMatcher(None, normalize(w.text), normalize(nickname)).ratio()
            if score >= .8:
                scored.append((score, w))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored or (len(scored)>1 and scored[0][0]-scored[1][0]<.15):
        return None
    return scored[0][1]


def own_stats(words, headers, nickname):
    if not nickname:
        return None
    row = own_row(words, nickname)
    if row is None:
        return None
    values = []
    for header in headers:
        candidates = [w for w in words if abs(w.cy - row.cy) < max(.014, row.height * .7)
                      and abs(w.x + w.width / 2 - (header.x + header.width / 2)) < .019
                      and min(headers, key=lambda h: abs(w.x + w.width / 2 - h.x - h.width / 2)) == header
                      and re.fullmatch(r'\d{1,3}', w.text)]
        if len(candidates) != 1:
            return None
        values.append(int(candidates[0].text))
    return tuple(values)


def detect(words, heroes, maps, nickname=''):
    top = text_in(words, (0, 0, 1, .15))
    result = any(t in top for t in ('VICTORY', 'DEFEAT', 'VICTORIA', 'DERROTA', 'ПОБЕДА', 'ПОРАЖЕНИЕ'))
    results_ui = any(t in top for t in ('LEAVING GAME', 'ABANDONANDO', 'SUMMARY', 'REWARDS', 'ВЫХОД', 'НАГРАДЫ', 'ДЛИТЕЛЬНОСТЬ МАТЧА', 'ПОКИНУТЬ МАТЧ'))
    # The final banner is large and centered; chat text and round notices are
    # insufficient evidence that the match ended.
    final_banner = any((w.text.upper() in ('VICTORY', 'DEFEAT', 'ПОБЕДА', 'ПОРАЖЕНИЕ')
                        or w.text.upper().endswith('ЖЕНИЕ')
                        and SequenceMatcher(None, w.text.upper(), 'ПОРАЖЕНИЕ').ratio() >= .65)
                       and .3 < w.x < .7 and .35 < w.cy < .65
                       and w.width > .20 and w.height > .065 for w in words)
    if result and results_ui or final_banner:
        return Detection(phase='results', scene='results')
    # Search is an independent state; it may coexist with gallery/practice HUD.
    group_banner = text_in(words, (.4, .08, .6, .2))
    waiting = (any(t in top for t in ('WAITING FOR GROUP MEMBERS', 'TO SELECT ROLE', 'ВЫБЕРУТ РОЛИ'))
               or all(t in group_banner for t in ('ГРУППЫ', 'ВЫБЕРУТ', 'РОЛИ')))
    search = any(t in top for t in ('SEARCHING', 'ПОИСК', 'ПОИСКА'))
    center_banner = text_in(words, (.4, 0, .6, .10))
    center_timer = text_in(words, (.52, 0, .59, .07))
    if re.search(r'\S{1,3}:\d{2}', center_timer):
        search = search or any(len(token)>=7 and SequenceMatcher(None, token, 'SEARCHING').ratio()>=.75
                               for token in center_banner.split())
    timed_banner = any(t in top for t in ('STADIUM COMPETITIVE', 'ИГРА ПО РОЛЯМ: БЫСТРАЯ ИГРА')) and bool(re.search(r'\S{1,3}:\d{2}', top))
    stadium_banner = text_in(words, (0, 0, .26, .09))
    timed_banner = timed_banner or ('STADIUM' in stadium_banner and bool(re.search(r'\S{1,3}:\d{2}', stadium_banner)))
    if not waiting and (search or timed_banner):
        detail = text_in(words, (0, .235, .57, .30))
        detail_mode = mode_from(detail) if any(t in detail for t in ('SEARCH', 'ПОИСК')) else None
        banner_mode = mode_from(stadium_banner) or mode_from(text_in(words, (.73, .07, 1, .15)))
        return Detection(phase='queue', mode=detail_mode or banner_mode, scene='search')
    vote_hint = text_in(words, (.32, .19, .75, .25))
    vote_result = text_in(words, (.32, .14, .75, .27))
    if 'РЕЗУЛЬТАТЫ ГОЛОСОВАНИ' in vote_result.replace('Я', 'А') or 'VOTING RESULTS' in vote_result:
        selected_map = catalog_name(top, maps)
        if selected_map is None:
            # The small italic winner label can be split into individual words.
            compact = normalize(text_in(words, (.94, .025, 1, .08)))
            names = {item['name'] for item in maps if isinstance(item, dict)
                     and any(normalize(alias) == compact for alias in
                             (item['name'], *item.get('localized_names', {}).values()))}
            selected_map = next(iter(names)) if len(names) == 1 else None
        return Detection(phase='map_loading', scene='map_loading',
                         map_name=selected_map, mode=mode_from(top))
    if ('БОЛЬШЕ' in vote_hint and 'ГОЛОСОВ' in vote_hint) or 'VOTE FOR A' in top:
        return Detection(phase='map_vote', scene='map_vote')
    if ('SPIEL WIRD GESCHLOSSEN' in top and 'SIEG' in top) or all(t in top for t in ('RESUMEN', 'EQUIPOS', 'PERSONAL')):
        return Detection(phase='results', scene='results')
    result = any(t in top for t in ('VICTORY', 'DEFEAT', 'VICTORIA', 'DERROTA', 'ПОБЕДА', 'ПОРАЖЕНИЕ'))
    results_ui = any(t in top for t in ('LEAVING GAME', 'ABANDONANDO', 'SUMMARY', 'REWARDS', 'ВЫХОД', 'НАГРАДЫ'))
    if (result and results_ui) or ('COMPETITIVE' in top and 'SUMMARY' in top and 'REWARDS' in top):
        return Detection(phase='results', scene='results')
    if waiting:
        return Detection(phase='menus', scene='waiting_for_group')
    if any(t in top for t in ('HISTORY', 'ИСТОРИЯ')):
        return Detection(phase='menus', scene='menus')
    # Headers locate the numeric columns without relying on row highlight or team colors.
    practice = 'УЧЕБНЫЙ ПОЛИГОН' in top or 'PRACTICE RANGE' in top
    header_bottom = .4 if practice else .2
    headers = []
    for aliases in [('E', 'УБ'), ('A', 'СОД'), ('D', 'С')]:
        found = [w for w in words if .3 < w.x < .55 and .1 < w.cy < header_bottom and w.text.upper() in aliases]
        if len(found) != 1:
            break
        headers.append(found[0])
    if len(headers) != 3:
        dmg = [w for w in words if .35 < w.x < .6 and .12 < w.cy < header_bottom and w.text.upper() in ('DMG', 'УРОН')]
        mit = [w for w in words if .45 < w.x < .65 and .12 < w.cy < header_bottom and w.text.upper() in ('MIT', 'ПОГЛ')]
        if len(dmg) == 1 and not mit and sum(bool(re.fullmatch(r'\d+', w.text)) for w in words if .3 < w.x < .6 and .19 < w.cy < .88) >= 9:
            mit = [Word('MIT', dmg[0].x+dmg[0].width*5.3, dmg[0].y, dmg[0].width, dmg[0].height)]
        if len(dmg) == len(mit) == 1 and abs(dmg[0].cy-mit[0].cy) < .01:
            center = dmg[0].x + dmg[0].width/2
            spacing = mit[0].x + mit[0].width/2 - center
            headers = [Word(label, center-factor*spacing-.005, dmg[0].y, .01, dmg[0].height)
                       for label, factor in zip(('E', 'A', 'D'), (1, .72, .45))]
    scoreboard = len(headers) == 3 and headers[0].x < headers[1].x < headers[2].x
    if scoreboard:
        hero = catalog_name(text_in(words, (.58, .29, .86, .39)), heroes, fuzzy=True)
        map_name = catalog_name(text_in(words, (.65, 0, 1, .09)), maps)
        timer_text = text_in(words, (.91, .025, 1, .085)).replace('O', '0').replace('О', '0')
        timer = re.findall(r'(?<!\d)(\d{1,3}):([0-5]\d)(?!\d)', timer_text)
        elapsed = int(timer[0][0])*60+int(timer[0][1]) if len(timer)==1 else None
        return Detection(phase='match', hero=hero, map_name=map_name, mode=mode_from(top),
                         kda=own_stats(words, headers, nickname), scene='scoreboard', elapsed=elapsed)
    left = text_in(words, (0, .08, .48, .31))
    selected_label = text_in(words, (.42, .72, .57, .89))
    practice_selection = ('В МАТЧЕ' in left and 'УЧЕБНЫЙ ПОЛИГОН' in left
                          and 'ПРОДОЛЖИТЬ' in text_in(words, (.42, .84, .57, .96)))
    selection = any(t in left for t in ('SELECT YOUR HERO', 'SELECT HERO', 'ВЫБЕРИТЕ ГЕРОЯ', 'ВЫБОР ГЕРОЯ')) or ('SUA EQUIPE' in left and 'SELECIONAR VISUAL' in text_in(words, (.65, .08, 1, .28)))
    assembly = ('СБОР КОМАНДЫ' in left
                and any(t in text_in(words, (.42, .84, .57, .96)) for t in ('ВЫБРАТЬ', 'СМЕНИТЬ ГЕРОЯ')))
    if selection or practice_selection or assembly:
        hero = catalog_name(text_in(words, (.65, .02, 1, .26)), heroes, fuzzy=True)
        if hero is None and (practice_selection or assembly):
            hero = catalog_name(selected_label, heroes, fuzzy=True)
        return Detection(phase='match', hero=hero,
                         map_name=catalog_name(left, maps), mode=mode_from(top + ' ' + left), scene='hero_select')
    # A gallery has the same portrait grid as hero selection, but HOME/CUSTOMIZE controls.
    navigation = text_in(words, (0, 0, .8, .09))
    if any(t in navigation for t in ('HEROES', 'BATTLE PASS', 'SHOP', 'ГЕРОИ', 'МАГАЗИН', 'НАЗАД', 'HÉROES', 'EVENTOS', 'TIENDA', 'HISTORIA')):
        return Detection(phase='menus', scene='menus')
    hp = [n for w in words if .07 < w.x < .23 and .8 < w.cy < .87 for n in re.findall(r'\d{2,4}', w.text)]
    ammo = [n for w in words if .88 < w.x < 1 and .8 < w.cy < .96 for n in re.findall(r'\d{1,3}', w.text)]
    if len(hp) >= 2 and len(ammo) >= 2:
        names = [w for w in words if .08 < w.x < .23 and .89 < w.cy < .94 and len(normalize(w.text)) >= 3]
        return Detection(phase='match', scene='hud', nickname=names[0].text if len(names) == 1 else None)
    return Detection()
