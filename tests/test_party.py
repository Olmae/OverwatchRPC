from pathlib import Path
import unittest
from PIL import Image, ImageOps
from owrpc_app.party import party_size
from owrpc_app.model import Settings, Status, build_payload


class PartyTests(unittest.TestCase):
    def header(self, name):
        crop = Image.open(Path(__file__).parent/'fixtures'/f'party-{name}.png').convert('RGB')
        image = Image.new('RGB', (1920, 1080))
        image.paste(crop, (1920-crop.width, 0))
        return image

    def test_solo_duo_trio_do_not_count_social_number(self):
        for name, expected in [('solo', 1), ('solo-cat', 1), ('duo', 2), ('trio', 3), ('five-compact', 5)]:
            image = self.header(name)
            for variant in (image, ImageOps.invert(image), ImageOps.grayscale(image).convert('RGB')):
                with self.subTest(name=name):
                    self.assertEqual(party_size(variant), expected)

    def test_unknown_or_hidden_header_is_not_reported_as_solo(self):
        self.assertIsNone(party_size(Image.new('RGB', (1920, 1080), 'black')))

    def test_confirmed_menu_count_survives_opening_the_app(self):
        status = Status(party_size=2, party_read_at=100)
        payload = build_payload(Settings(language='ru', ocr_enabled=True), status, now=110)
        self.assertEqual(payload['state'], 'В группе: 2 игрока')
        self.assertIn('В группе: 2 игрока', build_payload(Settings(language='ru', ocr_enabled=True), status, now=200)['state'])
        status.phase = 'match'
        self.assertIn('В группе: 2 игрока', build_payload(Settings(language='ru', ocr_enabled=True), status, now=110)['state'])

    def test_solo_label_and_override(self):
        status = Status(party_size=1, party_read_at=100)
        self.assertEqual(build_payload(Settings(language='ru', ocr_enabled=True), status, now=101)['state'], 'Соло')
        self.assertEqual(build_payload(Settings(state_override='Custom', ocr_enabled=True), status, now=101)['state'], 'Custom')

    def test_party_is_remembered_through_queue_and_match_then_cleared(self):
        status = Status(party_size=2, party_read_at=100)
        status.transition('queue', now=110)
        self.assertEqual(status.party_size, 2)
        self.assertIn('В группе: 2 игрока', build_payload(Settings(language='ru'), status, now=150)['state'])
        status.transition('map_vote', now=160)
        payload = build_payload(Settings(language='ru'), status, now=170)
        self.assertEqual(payload['details'], 'Выбор карты')
        self.assertIn('В группе: 2 игрока', payload['state'])
        status.transition('match', now=200)
        payload = build_payload(Settings(language='ru'), status, now=2000)
        self.assertIn('В группе: 2 игрока', payload['state'])
        status.transition('menus', now=2100)
        self.assertIsNone(status.party_size)
        self.assertIsNone(status.party_read_at)

    def test_disabled_recognition_hides_previously_detected_party(self):
        status = Status(party_size=2, party_read_at=100)
        self.assertEqual(build_payload(Settings(ocr_enabled=False), status, now=101)['state'], 'Overwatch')

    def test_portraits_anchor_to_right_edge_on_ultrawide_monitor(self):
        crop = Image.open(Path(__file__).parent/'fixtures'/'party-duo.png').convert('RGB')
        image = Image.new('RGB', (3440, 1440))
        crop = crop.resize((1024, 123))
        image.paste(crop, (image.width-crop.width, 0))
        self.assertEqual(party_size(image), 2)
