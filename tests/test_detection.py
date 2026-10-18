import unittest
from owrpc_app.detection import Word, detect


def word(text, x, y, w=.1, h=.025):
    return Word(text, x, y, w, h)


class DetectionTests(unittest.TestCase):
    def test_back_alone_never_proves_match_exit(self):
        self.assertIsNone(detect([word('НАЗАД', .02, .03)], [], []).phase)
        self.assertIsNone(detect([word('BACK', .02, .03)], [], []).phase)

    def test_escape_main_menu_needs_settings_profile_and_exit_game(self):
        controls = [word('НАСТРОЙКИ', .48, .54), word('ПРОФИЛЬ', .48, .48),
                    word('ВЫЙТИ', .48, .74, .03), word('ИЗ', .51, .74, .01), word('ИГРЫ', .525, .74, .03)]
        self.assertEqual(detect(controls, [], []).phase, 'menus')
        self.assertIsNone(detect(controls[:2], [], []).phase)
        # A discarded alphabet pass can leave interleaved OCR noise.
        noisy = controls + [word('BblVITV4', .48, .74, .03), word('V13', .51, .74, .01)]
        self.assertEqual(detect(noisy, [], []).phase, 'menus')

    def test_leave_match_button_keeps_phase_unknown_even_with_menu_navigation(self):
        for label in ('ПОКИНУТЬ МАТЧ', 'LEAVE GAME', 'LEAVE MATCH'):
            with self.subTest(label=label):
                result = detect([word('ГЕРОИ', .03, .03), word(label, .48, .74)], [], [])
                self.assertIsNone(result.phase)
                self.assertEqual(result.scene, 'pause_menu')

    def test_menu_language_is_based_on_bounded_fixed_controls(self):
        from owrpc_app.ocr import interface_language
        labels = [word('МЕНЮ', .47, .28), word('ПРОФИЛЬ', .48, .48), word('НАСТРОЙКИ', .48, .54)]
        self.assertEqual(interface_language(labels), 'rus')
        self.assertIsNone(interface_language(labels[:1]))
        self.assertIsNone(interface_language([word('МЕНЮ ПРОФИЛЬ НАСТРОЙКИ', .03, .65)]))

    def test_vote_language_uses_fixed_hint_without_player_names(self):
        from owrpc_app.ocr import interface_language
        hint = word('ЧЕМ БОЛЬШЕ ГОЛОСОВ У ПОЛЯ БОЯ ТЕМ ВЫШЕ ВЕРОЯТНОСТЬ ЧТО ОНО БУДЕТ ВЫБРАНО',
                    .36, .21, .28)
        self.assertEqual(interface_language([hint]), 'rus')
        self.assertIsNone(interface_language([word('БОЛЬШЕ ГОЛОСОВ', .36, .21, .2)]))
        self.assertIsNone(interface_language([word(hint.text, .1, .6, .28)]))

    def test_role_choice_before_queue_is_a_menu(self):
        result = detect([word('SELECT A ROLE', .08, .25)], [], [])
        self.assertEqual((result.phase, result.scene), ('menus', 'menus'))

    def test_challenges_navigation_and_system_clock_are_not_queue_evidence(self):
        words = [word('DAILY WEEKLY EVENT LIFETIME HERO STADIUM COMPETITIVE', .02, .035, .33),
                 word('8:46 PM', .94, .08, .04)]
        result = detect(words, [], [])
        self.assertEqual((result.phase, result.scene), ('menus', 'menus'))
        self.assertIsNone(result.mode)

    def test_russian_runasapi_assembly_without_visible_mode_label(self):
        from owrpc_app.catalog import load_catalog
        catalog = load_catalog()
        words = [word('СБОР КОМАНДЫ:', .03, .24), word('СМЕНИТЬ ГЕРОЯ', .46, .90),
                 word('РАМАТТРА', .84, .06), word('РУНАСАПИ', .064, .178)]
        result = detect(words, catalog['heroes'], catalog['maps'])
        self.assertEqual((result.phase, result.scene, result.hero, result.map_name),
                         ('match', 'hero_select', 'Ramattra', 'Runasapi'))
        self.assertIsNone(result.mode)

    def test_russian_assembly_button_tolerates_duplicate_ocr_spelling(self):
        words = [word('СБОР КОМАНДЫ', .03, .24), word('СМЕНИТЬ', .47, .907, .03),
                 word('ТЕРОЯ', .507, .907, .03), word('ГЕРОЯ', .507, .907, .03)]
        self.assertEqual(detect(words, [], []).scene, 'hero_select')
        self.assertIsNone(detect(words[1:], [], []).phase)

    def test_russian_practice_selection_reads_far_right_grid_name(self):
        from owrpc_app.catalog import load_catalog
        catalog = load_catalog()
        words = [word('УЧЕБНЫЙ ПОЛИГОН', .06, .18), word('В МАТЧЕ', .03, .24),
                 word('ПРОДОЛЖИТЬ', .47, .90), word('КИРИКО', .815, .78, .03)]
        result = detect(words, catalog['heroes'], catalog['maps'])
        self.assertEqual((result.phase, result.scene, result.hero, result.map_name),
                         ('match', 'hero_select', 'Kiriko', 'Practice Range'))

    def test_practice_continue_selection_without_title(self):
        words = [word('PRACTICE RANGE', .03, .08), word('IN MATCH', .03, .24),
                 word('CONTINUE', .48, .90)]
        result = detect(words, ['Echo'], ['Practice Range'])
        self.assertEqual((result.phase, result.scene, result.map_name),
                         ('match', 'hero_select', 'Practice Range'))
        self.assertIsNone(result.hero)

    def test_ready_assembly_reads_selected_label_and_map(self):
        words = [word('ASSEMBLE YOUR TEAM', .04, .24), word('READY', .48, .90),
                 word('KIRIKO', .53, .77, .025), word('JUNKERTOWN', .06, .18)]
        result = detect(words, ['Kiriko'], ['Junkertown'])
        self.assertEqual((result.scene, result.hero, result.map_name),
                         ('hero_select', 'Kiriko', 'Junkertown'))
        self.assertIsNone(detect([word('READY', .48, .90)], [], []).phase)

    def test_shifted_own_row_requires_stat_header_and_remains_before_counters(self):
        from owrpc_app.detection import own_row
        owner = word('OWNNAME', .416, .19, .035, .019)
        self.assertIsNone(own_row([owner], 'OWNNAME'))
        header = word('E', .480, .15, .008)
        self.assertEqual(own_row([owner, header], 'OWNNAME'), owner)
        self.assertIsNone(own_row([word('OWNNAME', .49, .19), header], 'OWNNAME'))
        self.assertIsNone(own_row([owner, header, word('OWNNAME', .416, .25)], 'OWNNAME'))

    def test_side_queue_requires_playlist_and_timer(self):
        words = [word('ROLE QUEUE: QUICK PLAY', .85, .10, .10),
                 word('1:39', .97, .10, .02)]
        result = detect(words, [], [])
        self.assertEqual((result.phase, result.mode), ('queue', 'Quick Play'))
        self.assertIsNone(detect(words[:1], [], []).phase)

    def test_stay_as_team_is_only_a_results_footer(self):
        self.assertEqual(detect([word('STAY AS TEAM?', .87, .935, .06, .02)], [], []).phase,
                         'results')
        self.assertIsNone(detect([word('STAY AS TEAM?', .05, .70)], [], []).phase)

    def test_counter_ocr_fallback_rejects_ambiguous_or_non_numeric_tokens(self):
        from PIL import Image
        from unittest.mock import patch
        from owrpc_app.ocr import read_counter_crop
        crop = Image.new('RGB', (76, 40))
        with patch('owrpc_app.digits.read_digits', return_value=None), \
                patch('owrpc_app.native_ocr._engine.words') as native:
            native.return_value = [word('11', .2, .2)]
            self.assertEqual(read_counter_crop(crop), 11)
            for tokens in [[], ['1', '1'], ['I1'], ['-1'], ['1.1'], ['1234']]:
                native.return_value = [word(t, .2, .2) for t in tokens]
                self.assertIsNone(read_counter_crop(crop), tokens)

    def test_post_match_footer_excludes_chat_mentions(self):
        footer = [Word('ENDORSE', .46, .96, .04, .02), Word('PLAYERS', .50, .96, .04, .02)]
        self.assertEqual(detect(footer, [], []).phase, 'results')
        chat = [Word('ENDORSE', .46, .86, .04, .02), Word('PLAYERS', .50, .86, .04, .02)]
        self.assertNotEqual(detect(chat, [], []).phase, 'results')

    def test_assembly_hud_is_not_hero_gallery_navigation(self):
        result = detect([word('ASSEMBLE YOUR HEROES', .43, .045)], [], [])
        self.assertIsNone(result.phase)
        self.assertEqual(detect([word('HEROES', .06, .025)], [], []).phase, 'menus')
        self.assertEqual(detect([word('SHOP', .45, .025)], [], []).phase, 'menus')

    def test_unranked_summary_rewards_ends_match(self):
        result = detect([word('SUMMARY', .035, .04), word('REWARDS', .15, .04)], [], [])
        self.assertEqual((result.phase, result.scene), ('results', 'results'))

    def test_partial_ocr_counters_combine_with_independent_digit_shapes(self):
        from pathlib import Path
        from PIL import Image
        from owrpc_app.ocr import analyze_image
        image = Image.new('RGB', (3440, 1440))
        with Image.open(Path(__file__).parent / 'fixtures' / 'kda-samoa-21-3-6.png') as crop:
            image.paste(crop, (1300, 270))
        words = [word('E', .390, .15, .008), word('A', .411, .15, .008),
                 word('D', .432, .15, .008), word('DMG', .456, .15, .018),
                 word('MIT', .523, .15, .015),
                 word('OWNNAME', .3247, .1891, .0334, .0187),
                 word('21', .3909, .195, .0065, .0188)]
        result = analyze_image(image, words, {'heroes': [], 'maps': []}, 'OWNNAME')
        self.assertEqual(result.kda, (21, 3, 6))

    def test_english_assembly_requires_button_and_ignores_countdown(self):
        words = [word('ASSEMBLE YOUR TEAM', .04, .24),
                 word('MIDTOWN', .09, .18), word('0:12', .04, .27)]
        self.assertIsNone(detect(words, [], ['Midtown']).phase)
        words.append(word('CHANGE HERO', .46, .91))
        result = detect(words, [], ['Midtown'])
        self.assertEqual((result.phase, result.scene, result.map_name),
                         ('match', 'hero_select', 'Midtown'))
        self.assertIsNone(result.elapsed)
        self.assertIsNone(result.party_size)

    def test_short_grimsvotn_header_with_partial_diacritics(self):
        from owrpc_app.catalog import load_catalog
        from owrpc_app.detection import catalog_name
        maps = load_catalog()['maps']
        for spelling in ('GRÍMSVÖTN','GRIMSVÖTN','GRIMSVOTN','ГРИМСВОТН'):
            self.assertEqual(catalog_name('ESCORT | '+spelling+' TIME:0:00', maps),
                             'Watchpoint: Grimsvotn')
        self.assertIsNone(catalog_name('GRIM FPS 120', maps))

    def test_long_mystery_playlist_takes_priority_over_map_type(self):
        from owrpc_app.detection import mode_from, catalog_name
        self.assertEqual(mode_from('КОНТРОЛЬ – ЗАГАДОЧНОЕ БЕЗУМИЕ | НЕПАЛ'), 'Mystery Madness')
        self.assertEqual(mode_from('НАТИСК | НЬЮ-КВИН-СТРИТ'), 'Push')
        maps = [{'name': 'New Queen Street', 'localized_names': {'ru': 'Нью-Квин-стрит'}},
                {'name': 'Nepal', 'localized_names': {'ru': 'Непал'}}]
        self.assertEqual(catalog_name('НЬЮ-КВИЊСТРИТ', maps, fuzzy=True), 'New Queen Street')
        self.assertIsNone(catalog_name('0:00 FPS', maps, fuzzy=True))

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
    def test_interface_language_uses_header_labels_and_ignores_nicknames(self):
        from owrpc_app.ocr import interface_language, nickname_language
        self.assertEqual(interface_language([word('ГЕРОИ', .03, .02),
                                             word('СОБЫТИЯ', .09, .02)]), 'rus')
        self.assertEqual(interface_language([word('HEROES', .03, .02),
                                             word('EVENTS', .09, .02)]), 'eng')
        self.assertEqual(interface_language([word('HERO INFO', .03, .02),
                                             word('SCOREBOARD', .12, .02)]), 'eng')
        self.assertIsNone(interface_language([word('ГЕРОИ', .03, .02)]))
        self.assertIsNone(interface_language([word('ГЕРОИ СОБЫТИЯ', .2, .3)]))
        self.assertEqual(nickname_language('OlmaeUwU'), 'eng')
        self.assertEqual(nickname_language('Игрок'), 'rus')
        self.assertEqual(nickname_language('Player_Игрок'), 'rus')
        assembly = [word('SSEMBLE YOUR TEAM', .04, .24), word('SELEGVSKIN', .88, .23)]
        self.assertEqual(interface_language(assembly), 'eng')
        self.assertIsNone(interface_language(assembly[:1]))
        self.assertEqual(interface_language([word('СБОР КОМАНДЫ', .03, .24),
                                             word('ВЫБОР ОБЛИКА', .86, .24)]), 'rus')

    def test_collapsed_competitive_search_reads_detail_instead_of_all_tabs(self):
        words = [word('SEARCHING', .46, .055), word('HEROES', .03, .025),
                 word('COMPETITIVE', .33, .11), word('STADIUM', .45, .11),
                 word('ARCADE', .62, .11),
                 word('SEARCHING: COMPETITIVE: ROLE QUEUE', .05, .255, .28)]
        self.assertEqual(detect(words, [], []).mode, 'Competitive')
        self.assertIsNone(detect(words[:-1], [], []).mode)

    def test_expanded_playlist_excludes_tabs_on_other_lines(self):
        words = [word('SEARCHING', .46, .055), word('HEROES', .03, .025),
                 word('STADIUM', .45, .18), word('ARCADE', .62, .18),
                 word('COMPETITIVE:', .40, .12, .10), word('ROLE', .51, .12, .04),
                 word('QUEUE', .56, .12, .05)]
        self.assertEqual(detect(words, [], []).mode, 'Competitive')

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

    def test_english_selecting_map_and_vote_countdown_do_not_pick_highlight(self):
        candidates = [word('PARAÍSO', .32, .54), word('BUSAN', .50, .54)]
        for title in ([word('SELECTING', .45, .14, .05), word('MAP', .52, .14, .03)],
                      [word('VOTE', .44, .14, .03), word('FOR', .48, .14, .02),
                       word('A', .51, .14, .01), word('MAP', .53, .14, .03)],
                      [word('VOTE', .44, .14, .03),
                       word('MAPS WITH MORE VO VOTES HAVE A HIGHER CHANCE TO BE PICKED', .40, .21, .22)]):
            result = detect(title+candidates, [], ['Paraíso', 'Busan'])
            self.assertEqual((result.phase, result.scene), ('map_vote', 'map_vote'))
            self.assertIsNone(result.map_name)
        self.assertIsNone(detect([word('SELECTING MAP', .05, .70)], [], []).phase)
        self.assertIsNone(detect([word('VOTE', .44, .14)], [], []).phase)

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
