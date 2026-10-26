"""Settings migration, validation and panel preservation checks (no live writes)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import appearance
import settings


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.config=self.root/'.config/cosmic/io.github.kerry.CosmicWindowList/v1'
        self.panel=self.root/'.config/cosmic/com.system76.CosmicPanel.Panel/v1'
        self.panel.mkdir(parents=True)
        (self.panel/'plugins_wings').write_text('Some((["custom.launcher"], ["custom.tray"]))\n')
        (self.panel/'plugins_center').write_text('Some(["custom.clock"])\n')
        self.patches=[patch.object(settings,'CONFIG',self.config),patch.object(settings,'PANEL',self.panel),
                      patch.object(settings,'SYSTEM_PANEL',self.root/'system'),patch.object(Path,'home',return_value=self.root)]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    def test_migration_keeps_existing_preferences(self):
        self.config.mkdir(parents=True)
        (self.config/'group_after').write_text('9\n')
        (self.config/'favorites').write_text('["my.app"]\n')
        settings.apply_defaults(panel_defaults=False)
        self.assertEqual(settings.read_values()['group_after'],9)
        self.assertEqual((self.config/'favorites').read_text(),'["my.app"]\n')
        self.assertFalse(settings.read_values()['custom_style'])

    def test_preset_roundtrip_preserves_layout_and_grouping(self):
        settings.save({'group_after':8})
        settings.save(appearance.MXWL)
        values=settings.read_values()
        self.assertEqual(values['group_after'],8)
        self.assertEqual(values['accent_color'],'#91bd7d')
        self.assertEqual(values['font_family'],'IBM Plex Mono')
        self.assertEqual(settings.panel_layout(),{'left':['custom.launcher'],'right':['custom.tray'],'center':['custom.clock']})

    def test_invalid_values_do_not_write(self):
        for values in ({'button_min_width':300,'button_max_width':100},{'accent_color':'bad'},
                       {'show_icons':False,'show_titles':False}):
            with self.assertRaises(ValueError): settings.save(values)
        self.assertFalse(self.config.exists())
        with self.assertRaises(ValueError): settings.save(appearance.MXWL,panel_style={**appearance.PANEL_MXWL,'opacity':101})
        self.assertFalse(self.config.exists())

    def test_panel_colors_roundtrip_and_backup(self):
        for key,text in appearance.panel_values({**appearance.PANEL_MXWL,'background':'#112233','opacity':85}).items():
            (self.panel/key).write_text(text)
        settings.save(appearance.MXWL,panel_style=appearance.PANEL_MXWL)
        self.assertEqual(settings.read_panel_style()['background'],'#1e1e1e')
        backups=list((self.root/'.local/state/cosmic-backups').glob('*/.config/cosmic/com.system76.CosmicPanel.Panel/v1/background'))
        self.assertEqual(len(backups),1)
        self.assertIn('0.06666667',backups[0].read_text())

    def test_malformed_stored_values_recover(self):
        self.config.mkdir(parents=True)
        (self.config/'group_after').write_text('broken')
        (self.config/'corner_radius').write_text('"oops"')
        self.assertEqual(settings.read_values()['group_after'],5)
        self.assertEqual(settings.read_values()['corner_radius'],4)


if __name__=='__main__': unittest.main()
