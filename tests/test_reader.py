import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reader', ROOT / 'scripts/build_reader.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'examples/demo.json').read_text(encoding='utf-8'))
        self.base = ROOT / 'examples'
        self.words = list(enumerate(r.validate_glossary(self.data['glossary'])))

    def test_demo_preserves_shared_content(self):
        page, counts = r.build(self.data, self.base)
        self.assertEqual(counts, {'pair': 3, 'note': 1, 'equation': 1, 'figure': 1, 'table': 1})
        self.assertIn('data:image/png;base64,', page)
        self.assertIn('<td>6</td>', page)
        self.assertIn('<math display="block">', page)
        self.assertNotIn('<script src=', page)

    def test_longest_phrase_once_and_original_text(self):
        result = r.rich('A sample mean, a sample, then a sample mean.', self.words)
        self.assertEqual(result.count('class="vocab"'), 2)
        self.assertIn('>sample mean</button>', result)
        import re
        self.assertEqual(re.sub('<[^>]+>', '', result), 'A sample mean, a sample, then a sample mean.')

    def test_skip_math_citations_links_code_but_keep_tails(self):
        source = '<math><mi>sample</mi></math><cite>sample</cite><a href="https://example.org">sample</a><code>sample</code> sample'
        result = r.rich(source, self.words)
        self.assertEqual(result.count('class="vocab"'), 1)
        self.assertTrue(result.endswith('>sample</button>'))

    def test_annotation_cap_and_boundaries(self):
        self.assertNotIn('vocab', r.rich('resampled', self.words))
        self.assertNotIn('vocab', r.rich('sample mean', self.words, 0))
        self.assertEqual(r.rich('sample mean and bias', self.words, 1).count('class="vocab"'), 1)

    def test_context_specific_alias(self):
        duplicate = dict(self.data['glossary'][0], id='estimate-verb', meaning='估计', detail='这里是动词。')
        self.data['glossary'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            r.build(self.data, self.base)
        for section in self.data['sections']:
            for block in section['blocks']:
                block['glossary_ids'] = ['estimate-verb']
        page, _ = r.build(self.data, self.base)
        self.assertIn('data-word="8"', page)

    def test_reject_executable_markup(self):
        for value in ['<script>alert(1)</script>', '<span onclick="x">text</span>', '<a href="javascript:alert(1)">x</a>', '<iframe></iframe>', '<svg onload="x"></svg>', '<math href="https://example.org">x</math>']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                r.rich(value)

    def test_escape_embedded_glossary(self):
        self.data['glossary'][0]['detail'] = '</script><script>alert(1)</script>'
        page, _ = r.build(self.data, self.base)
        self.assertNotIn('</script><script>alert(1)', page)
        self.assertIn('\\u003c/script\\u003e', page)

    def test_missing_translation_and_duplicate_id(self):
        block = self.data['sections'][0]['blocks'][0]
        del block['zh']
        with self.assertRaises(KeyError):
            r.build(self.data, self.base)
        block['zh'] = '译文'
        block['id'] = self.data['sections'][0]['id']
        with self.assertRaisesRegex(ValueError, 'unique'):
            r.build(self.data, self.base)

    def test_invalid_table_shape(self):
        self.data['sections'][1]['blocks'][1]['rows'][0].append('unexpected')
        with self.assertRaisesRegex(ValueError, 'header count'):
            r.build(self.data, self.base)

    def test_asset_escape_and_svg_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            outside = root / 'secret.png'
            outside.write_bytes(b'\x89PNG\r\n\x1a\nsecret')
            inside = root / 'inside'
            inside.mkdir()
            with self.assertRaisesRegex(ValueError, 'inside'):
                r.image_data('../secret.png', inside)
            (inside / 'link.png').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'inside'):
                r.image_data('link.png', inside)
            (inside / 'image.svg').write_text('<svg></svg>')
            with self.assertRaisesRegex(ValueError, 'raster'):
                r.image_data('image.svg', inside)

    def test_malformed_markup_and_math_spacing(self):
        for value in ['<p>unclosed', '<p><em>bad</p></em>']:
            with self.assertRaises(ValueError):
                r.rich(value)
        self.assertEqual(r.rich('<math><mspace width="1em"/><mi>x</mi></math>'), '<math><mspace width="1em"></mspace><mi>x</mi></math>')

    def test_zero_annotation_limit(self):
        self.data['annotation_limit'] = 0
        page, _ = r.build(self.data, self.base)
        self.assertNotIn('class="vocab"', page)


if __name__ == '__main__':
    unittest.main()
