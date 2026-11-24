import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'tools'))
from timer_fixtures import assemble, cases


class TimerFixtureTests(unittest.TestCase):
    def test_pinned_hardware_assertions_are_preserved(self):
        expected={
            'tim00':{'d':4,'e':5},'tim01':{'d':8,'e':9},
            'tim10':{'d':4,'e':5},'tim11':{'d':4,'e':5},
            'tim00_div_trigger':{'d':4,'e':5},'tim01_div_trigger':{'d':10,'e':11},
            'tim10_div_trigger':{'d':5,'e':6},'tim11_div_trigger':{'d':4,'e':5},
            'tima_reload':{'b':254,'c':254,'d':255,'e':0,'h':255,'l':0},
            'tima_write_reloading':{'c':254,'d':128,'e':127,'l':127},
            'tma_write_reloading':{'c':254,'d':127,'e':127,'l':254},
        }
        fixtures=cases()
        self.assertEqual({x['name']:x['expect'] for x in fixtures},expected)
        for item in fixtures:
            self.assertEqual(item['rom'][-4:],[0xAF,0xE0,7,0x76])
            self.assertLess(len(item['rom']),4096)

    def test_assembler_rejects_unknown_instructions(self):
        with self.assertRaisesRegex(ValueError,'Unrecognized'):
            assemble('\ntest:\n  call unknown\n  setup_assertions\n  assert_d $0A\n')


if __name__=='__main__':unittest.main()
