import unittest
from owrpc_app.detection import Word, detect


def word(text, x, y, w=.1, h=.025):
    return Word(text, x, y, w, h)


class DetectionTests(unittest.TestCase):
    def test_search_in_gallery_does_not_set_playing_hero(self):
        result = detect([word('SEARCHING', .46, .055), word('MERCY', .85, .25)], ['Mercy'], [])
        self.assertEqual(result.phase, 'queue')
        self.assertIsNone(result.hero)

    def test_search_on_practice_range_takes_priority_over_hud(self):
        result = detect([word('STADIUM COMPETITIVE', .04, .02), word('5:28', .2, .02),
                         word('ITZHAMMY', .1, .9), word('275', .1, .82)], [], [])
        self.assertEqual((result.phase, result.mode), ('queue', 'Stadium'))

    def test_history_victories_and_maps_are_not_current_match(self):
        result = detect([word('HISTORY', .29, .04), word('GAME REPORTS', .02, .4),
                         word('HAVANA', .25, .4), word('VICTORY!', .85, .4)], [], ['Havana'])
        self.assertEqual(result.phase, 'menus')
        self.assertIsNone(result.map_name)

    def test_waiting_for_roles_is_not_search(self):
        result = detect([word('WAITING FOR GROUP MEMBERS', .76, .11),
                         word('TO SELECT ROLE', .76, .14)], [], [])
        self.assertEqual(result.phase, 'menus')

    def test_scoreboard_extracts_own_row_without_team_colors(self):
        words = [word('CONTROL | NEPAL', .82, .04), word('TIME:4:17', .94, .04),
                 word('E', .37, .15, .01), word('A', .39, .15, .01), word('D', .42, .15, .01),
                 word('BASTION', .6, .35), word('CASH', .25, .19),
                 word('10', .37, .19, .015), word('1', .39, .19, .015), word('1', .42, .19, .015),
                 word('ROUND 1 COMPLETE', .4, .10)]
        result = detect(words, ['Bastion'], ['Nepal'], 'CASH')
        self.assertEqual((result.phase, result.hero, result.map_name), ('match', 'Bastion', 'Nepal'))
        self.assertEqual(result.kda, (10, 1, 1))
        self.assertEqual(result.elapsed, 257)

    def test_no_guessing_own_stats_when_nickname_unknown(self):
        result = detect([word('E', .38, .15), word('A', .41, .15), word('D', .44, .15),
                         word('MOIRA', .65, .34), word('29 36 8', .37, .38)], ['Moira'], [])
        self.assertEqual(result.hero, 'Moira')
        self.assertIsNone(result.kda)

    def test_scoreboard_timer_accepts_ocr_zero_letters_only_in_timer_region(self):
        result = detect([word('E', .38, .15), word('A', .41, .15), word('D', .44, .15),
                         word('q.o:oo', .96, .04, .025)], [], [])
        self.assertEqual(result.elapsed, 0)

    def test_result_screen_takes_priority_over_scoreboard(self):
        result = detect([word('VICTORY', .02, .03), word('HAVANA', .15, .03),
                         word('LEAVING GAME IN', .73, .04)], [], ['Havana'])
        self.assertEqual(result.phase, 'results')

    def test_unrecognized_frame_does_not_force_menu(self):
        self.assertIsNone(detect([], [], []).phase)

    def test_two_rows_with_same_name_are_ambiguous(self):
        words = [word('E', .38, .15), word('A', .41, .15), word('D', .44, .15),
                 word('CASH', .25, .2), word('CASH', .25, .3), word('10', .38, .2)]
        self.assertIsNone(detect(words, [], [], 'CASH').kda)


class ConservativeDetectionTests(unittest.TestCase):
    def test_russian_search_timer_can_have_an_ocr_error(self):
        result = detect([word('ИГРА ПО РОЛЯМ: БЫСТРАЯ ИГРА', .8, .105), word('п:13', .96, .105, .02)], [], [])
        self.assertEqual((result.phase, result.mode), ('queue', 'Quick Play'))

    def test_short_hero_name_from_scoreboard_can_be_corrected(self):
        words = [word('E', .38, .15, .01), word('A', .41, .15, .01), word('D', .44, .15, .01), word('D.VRO', .6, .34)]
        self.assertEqual(detect(words, ['D.Va', 'Moira'], []).hero, 'D.Va')

    def test_hud_requires_both_health_and_ammunition(self):
        words = [word('250', .1, .82), word('250', .16, .82), word('PLAYER', .12, .9)]
        self.assertIsNone(detect(words, [], []).phase)
        words += [word('15', .92, .89, .02), word('15', .95, .89, .02)]
        result = detect(words, [], [])
        self.assertEqual((result.phase, result.nickname), ('match', 'PLAYER'))

    def test_ambiguous_nickname_never_selects_stats(self):
        from owrpc_app.detection import own_row
        self.assertIsNone(own_row([word('FREYA', .22, .2), word('FREYA', .22, .3)], 'FREYA'))
        self.assertIsNotNone(own_row([word('FREYR', .22, .2)], 'FREYA'))


class QueueModeTests(unittest.TestCase):
    def test_tabs_do_not_override_actual_queue_mode(self):
        words = [word('ИДЕТ ПОИСК', .46, .056), word('0:42', .55, .01, .025),
                 word('СТАДИОН', .45, .11), word('АРКАДА', .62, .11),
                 word('ПОИСК (СОРЕВНОВАТЕЛЬНАЯ ИГРА: ИГРА ПО РОЛЯМ)', .07, .25, .35)]
        self.assertEqual(detect(words, [], []).mode, 'Competitive')


class AdditionalSceneTests(unittest.TestCase):
    def test_russian_hybrid_scoreboard_resolves_bundled_paraiso(self):
        from owrpc_app.catalog import load_catalog
        catalog = load_catalog()
        words = [word('УБ', .38, .15, .01), word('СОД', .41, .15, .01),
                 word('С', .44, .15, .01), word('ГИБРИДНЫЙ РЕЖИМ', .82, .035, .07),
                 word('ПАРАИСО', .90, .035, .03)]
        result = detect(words, catalog['heroes'], catalog['maps'])
        self.assertEqual((result.map_name, result.mode), ('Paraíso', 'Hybrid'))

    def test_map_vote_does_not_pick_a_candidate_map(self):
        words = [word('ЧЕМ БОЛЬШЕ ГОЛОСОВ У ПОЛЯ БОЯ', .36, .215, .30),
                 word('BLIZZARD WORLD', .31, .54), word('ИЛИОС', .49, .54),
                 word('ПАРАИСО', .65, .54)]
        result = detect(words, [], ['Blizzard World', 'Илиос', 'Параисо'])
        self.assertEqual((result.phase, result.scene), ('map_vote', 'map_vote'))
        self.assertIsNone(result.map_name)

    def test_cyrillic_condensed_title_and_control_mode(self):
        words = [word('УБ', .38, .15, .01), word('СОД', .41, .15, .01),
                 word('С', .44, .15, .01), word('РЯМЯТТРЯ', .6, .34),
                 word('КОНТРОЛЬ', .87, .03)]
        heroes = [{'name': 'Ramattra', 'localized_names': {'ru': 'Раматтра'}},
                  {'name': 'Reaper', 'localized_names': {'ru': 'Жнец'}}]
        result = detect(words, heroes, [])
        self.assertEqual((result.hero, result.mode), ('Ramattra', 'Control'))

    def test_practice_scoreboard_with_lower_headers(self):
        words = [word('Учебный полигон', .86, .03, .07),
                 word('УБ', .414, .295, .008), word('СОД', .429, .295, .014),
                 word('С', .455, .295, .004), word('ЭШ', .627, .344, .02),
                 word('OLMAEUWU', .296, .334, .036),
                 word('0', .414, .337, .008), word('0', .435, .337, .008),
                 word('0', .456, .337, .008)]
        result = detect(words, [{'name': 'Ashe', 'localized_names': {'ru': 'Эш'}}],
                        [{'name': 'Practice Range', 'localized_names': {'ru': 'Учебный полигон'}}],
                        'OlmaeUwU')
        self.assertEqual((result.scene, result.hero, result.map_name, result.mode, result.kda),
                         ('scoreboard', 'Ashe', 'Practice Range', 'Practice', (0, 0, 0)))

    def test_lower_headers_without_practice_context_are_not_a_scoreboard(self):
        words = [word('E', .414, .295, .008), word('A', .435, .295, .008),
                 word('D', .456, .295, .008)]
        self.assertEqual(detect(words, [], []).scene, 'unknown')

    def test_german_result_is_not_active_match(self):
        result = detect([word('SIEG', .03, .04), word('SPIEL WIRD GESCHLOSSEN IN:', .5, .05),
                         word('SAMOA', .1, .04)], [], ['Samoa'])
        self.assertEqual(result.phase, 'results')
        self.assertIsNone(result.map_name)

    def test_spanish_team_report_is_not_current_scoreboard(self):
        result = detect([word('RESUMEN EQUIPOS PERSONAL', .05, .03),
                         word('E', .38, .15), word('A', .41, .15), word('D', .44, .15)], [], [])
        self.assertEqual(result.phase, 'results')
        self.assertIsNone(result.kda)

    def test_portuguese_assembly_identifies_own_hero(self):
        result = detect([word('JOGO CASUAL', .02, .06), word('BLIZZARD WORLD', .08, .18),
                         word('REÜNA SUA EQUIPE:', .03, .24), word('JUNO', .9, .06),
                         word('SELECIONAR VISUAL', .85, .24)], ['Juno'], ['Blizzard World'])
        self.assertEqual((result.phase, result.hero, result.map_name, result.mode),
                         ('match', 'Juno', 'Blizzard World', 'Quick Play'))
